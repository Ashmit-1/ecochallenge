# Deploying EcoChallenge

Production layout:

```
Browser ──► Cloudflare Pages (static SPA + /api proxy function)
                 │  /api/*  (same-origin, so cookies + CSRF just work)
                 ▼
            Cloud Run  (this repo's backend/Dockerfile)
                 ├──► Turso          hosted libSQL database (users, points, submissions)
                 ├──► Cloudflare R2  private photo bucket (evidence images)
                 └──► Google AI      Gemini/Gemma photo verification
```

Nothing lives on the container's disk: Cloud Run's filesystem is ephemeral, so the database and
photos are external. Deploy the **backend first** — the Pages function needs its URL.

Everything below assumes these shell variables. Replace the values:

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="asia-south1"                 # pick the region closest to your users
export SERVICE="ecochallenge-api"
export TURSO_DB="ecochallenge"
export R2_BUCKET="ecochallenge-photos"
export PAGES_PROJECT="ecochallenge"
export PAGES_DOMAIN="ecochallenge.pages.dev" # or your custom domain
```

## 0. Prerequisites

| Tool | Why | Check |
|---|---|---|
| `gcloud` + Cloud Build API | Build the image and deploy Cloud Run | `gcloud version` |
| `turso` CLI | Create the hosted database | `turso --version` |
| `bun` | Build the frontend | `bun --version` |
| Docker (optional) | Test the image locally | `docker --version` |

```bash
gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

turso auth login
bunx wrangler login        # Cloudflare account that will host Pages + R2
```

---

# Part 1 — Backend (Cloud Run)

## 1.1 Create the Turso database

```bash
turso db create "$TURSO_DB"
turso db show "$TURSO_DB" --url          # → libsql://ecochallenge-<org>.turso.io
turso db tokens create "$TURSO_DB"       # → the auth token (keep it secret)
```

```bash
export DATABASE_URL="libsql://ecochallenge-<org>.turso.io"   # from the command above
```

The app normalises `libsql://` to the SQLAlchemy libSQL dialect with TLS. You do **not** need to
create tables by hand — the container runs migrations on boot (step 1.4).

> Optional sanity check from your machine, before deploying:
> ```bash
> cd backend
> DATABASE_URL="$DATABASE_URL" TURSO_AUTH_TOKEN="<token>" uv run alembic upgrade head
> DATABASE_URL="$DATABASE_URL" TURSO_AUTH_TOKEN="<token>" uv run seed
> ```
> Skipping this is fine; the first container start does the same thing.

## 1.2 Create the R2 bucket

```bash
bunx wrangler r2 bucket create "$R2_BUCKET"
```

Then in the Cloudflare dashboard: **R2 → Manage R2 API Tokens → Create API Token**

- Permissions: **Object Read & Write**
- Scope: this bucket only
- Copy the **Access Key ID**, **Secret Access Key**, and your **Account ID** (top-right of R2).

```bash
export R2_ACCOUNT_ID="your-cloudflare-account-id"
```

Keep the bucket **private**. Photos are served only by the authenticated
`GET /api/v1/submissions/{id}/image` route, which checks ownership first.

## 1.3 Store secrets in Secret Manager

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))" > /tmp/ecochallenge-secret-key
gcloud secrets create ecochallenge-secret-key --data-file=/tmp/ecochallenge-secret-key
rm /tmp/ecochallenge-secret-key

# Paste each value when prompted, then Ctrl-D.
gcloud secrets create ecochallenge-turso-token  --data-file=-
gcloud secrets create ecochallenge-gemini-key   --data-file=-
gcloud secrets create ecochallenge-r2-key-id    --data-file=-
gcloud secrets create ecochallenge-r2-secret    --data-file=-
```

> `ecochallenge-gemini-key` is the `GEMINI_API_KEY` from
> <https://aistudio.google.com/apikey> — the same key already in `backend/.env`.

Let the Cloud Run service read them:

```bash
SA="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
for secret in ecochallenge-secret-key ecochallenge-turso-token ecochallenge-gemini-key \
              ecochallenge-r2-key-id ecochallenge-r2-secret; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor
done
```

If your project disables the default compute service account, create a dedicated service account,
grant it `roles/secretmanager.secretAccessor`, and pass it with `--service-account`.

## 1.4 Build and deploy the container

`gcloud run deploy --source .` uploads `backend/` and builds it with the checked-in
[Dockerfile](backend/Dockerfile) — no local Docker required. The entrypoint applies Alembic
migrations and the challenge seed, then starts uvicorn on Cloud Run's `$PORT`.

```bash
cd backend

# One instance while the first schema migration runs; scale up afterwards.
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --concurrency 20 \
  --timeout 120 \
  --min-instances 0 \
  --max-instances 1 \
  --set-env-vars "ENVIRONMENT=production,VISION_PROVIDER=gemini,GEMINI_MODEL=gemma-4-26b-a4b-it,STORAGE_BACKEND=r2,R2_ACCOUNT_ID=$R2_ACCOUNT_ID,R2_BUCKET=$R2_BUCKET,DATABASE_URL=$DATABASE_URL,CORS_ORIGINS=https://$PAGES_DOMAIN" \
  --set-secrets "SECRET_KEY=ecochallenge-secret-key:latest,TURSO_AUTH_TOKEN=ecochallenge-turso-token:latest,GEMINI_API_KEY=ecochallenge-gemini-key:latest,R2_ACCESS_KEY_ID=ecochallenge-r2-key-id:latest,R2_SECRET_ACCESS_KEY=ecochallenge-r2-secret:latest"
```

Notes on the flags:

- `--allow-unauthenticated` is required: the Pages Function calls the service without Google IAM
  credentials. The app's own JWT/cookie auth is what protects user data.
- `--max-instances 1` only for the first deploy, so two containers never migrate at the same time.
  `ENVIRONMENT=production` turns on `Secure` session cookies.
- `--concurrency 20` keeps each instance comfortably below Turso's connection limits while a
  request waits on the vision model.
- Multiple CORS origins would clash with the comma separator in `--set-env-vars`; use the
  alternate delimiter form `--set-env-vars "^@^A=1@B=2@CORS_ORIGINS=https://a,https://b"`.
- `backend/.gcloudignore` keeps `.env`, virtualenvs, the local database, and uploads out of the
  Cloud Build source upload; `backend/.dockerignore` repeats that for the image build. The built
  image was inspected and contains only `.venv`, `app`, `alembic`, `data`, `uploads`, the
  entrypoint, and `alembic.ini` — no `.env`.

After the first successful deploy, allow scaling:

```bash
gcloud run services update "$SERVICE" --region "$REGION" --max-instances 4
```

## 1.5 Verify the API

```bash
SERVICE_URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "$SERVICE_URL"

curl -s "$SERVICE_URL/api/v1/health"      # {"status":"ok","database":"ok",...}
curl -s "$SERVICE_URL/api/v1/meta"        # verification_provider: "gemma-4-26b-a4b-it"
curl -s "$SERVICE_URL/api/v1/challenges"  # 5 seeded challenges
```

The API docs are at `$SERVICE_URL/docs`.

If the deploy failed, read the build/start logs:

```bash
gcloud run services logs read "$SERVICE" --region "$REGION" --limit 50
```

## 1.6 Optional: run the same image locally

```bash
cd backend
docker build -t ecochallenge-backend .
docker run --rm -p 8080:8080 \
  -e SECRET_KEY="local-only-secret" \
  -e ENVIRONMENT=development \
  -e VISION_PROVIDER=mock \
  -e DATABASE_URL="sqlite:///./data/ecochallenge.db" \
  -e UPLOADS_DIR=./uploads \
  ecochallenge-backend
# http://127.0.0.1:8080/api/v1/health
```

---

# Part 2 — Frontend (Cloudflare Pages)

The SPA calls relative `/api/v1/...` paths, and Pages cannot proxy external domains from
`_redirects`. `frontend/functions/api/[[path]].ts` forwards
`/api/*` to Cloud Run, so the browser keeps treating the API as same-origin: session cookies stay
first-party and the CSRF double-submit cookie works without CORS.

## 2.1 Connect the repository (recommended)

In the Cloudflare dashboard: **Workers & Pages → Create → Pages → Connect to Git**

| Setting | Value |
|---|---|
| Repository | this repo |
| Production branch | `deployment` (or `main` once merged) |
| Root directory | `frontend` |
| Framework preset | Vite |
| Build command | `bun install --frozen-lockfile && bun run build` |
| Build output directory | `dist` |

Add the API origin as a variable for **both** Production and Preview:

**Settings → Variables and Secrets → Add**

```
API_ORIGIN = https://<your Cloud Run service URL from step 1.5>
```

Pages bundles `frontend/functions/` automatically when the root directory is `frontend`.

## 2.2 Or deploy from the CLI

```bash
cd frontend
bun install --frozen-lockfile
bun run build                      # tsc -b && vite build → dist/

bunx wrangler pages project create "$PAGES_PROJECT" --production-branch deployment
bunx wrangler pages deploy dist --project-name "$PAGES_PROJECT"
bunx wrangler pages secret put API_ORIGIN --project-name "$PAGES_PROJECT"
# paste the Cloud Run URL when prompted
```

Run the deploy from `frontend/` so Wrangler finds `functions/` next to `dist/`.

## 2.3 Point the backend at the Pages domain

If the Pages domain differs from the one used in step 1.4 (preview URLs, custom domain), update it:

```bash
gcloud run services update "$SERVICE" --region "$REGION" \
  --update-env-vars "CORS_ORIGINS=https://$PAGES_DOMAIN"
```

## 2.4 Verify end to end

```bash
# 1. The proxy reaches Cloud Run (this is the same path the browser uses)
curl -s "https://$PAGES_DOMAIN/api/v1/health"

# 2. The SPA shell loads
curl -sI "https://$PAGES_DOMAIN/" | head -3
```

Then in a browser, on the Pages URL:

1. Register a student → you stay signed in (cookies issued through the proxy).
2. Open a challenge and upload a real photo → verdict, points, and CO₂ update.
3. Reload the profile → the photo thumbnail still loads (it came from R2, not container disk).

---

# Part 3 — Operating it

## Redeploying

- **Backend:** re-run the `gcloud run deploy --source .` command (step 1.4). Set
  `--max-instances 1` for that revision if the release contains a new migration, then raise it
  again. The seed is idempotent and never re-activates a retired challenge.
- **Frontend:** push to the connected branch, or re-run `bunx wrangler pages deploy dist`.

## Rollback

```bash
gcloud run revisions list --service "$SERVICE" --region "$REGION"
gcloud run services update-traffic "$SERVICE" --region "$REGION" \
  --to-revisions "$SERVICE-00002-abc=100"
```

Frontend: **Pages → your project → Deployments → ⋯ → Rollback**. Database migrations are
forward-only; roll the code back only if the previous revision still matches the schema.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Container exits: `RuntimeError: TURSO_AUTH_TOKEN is required...` | `TURSO_AUTH_TOKEN` secret not mounted, or `DATABASE_URL` points at a host without a token |
| Uploads 500, log warns `R2 settings are incomplete` | One of `R2_ACCOUNT_ID`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` is missing or the token lacks Object Read & Write |
| Every write returns `403 CSRF validation failed` | The API is being called cross-site: `API_ORIGIN` is wrong/missing, or `CORS_ORIGINS` does not match the Pages domain |
| Signed in, but the next request is `401` | Cookies are `Secure` (`ENVIRONMENT=production`) and you are testing over plain HTTP |
| `PermissionDenied` on secrets at boot | Re-run the IAM bindings in step 1.3 for the service's actual service account |
| `alembic.util.exc.CommandError` / duplicate table | Two containers migrated at once; redeploy with `--max-instances 1` |
| First request after idle is slow | Cloud Run scaled to zero; set `--min-instances 1` for demos |
| Browser console 404 on `/api/...` | Pages project root is not `frontend`, so `functions/` was not bundled |

## Known deployment caveats

- **Migrations on boot** are convenient but not safe under concurrent scaling: deploy schema
  changes with `--max-instances 1`, then scale up.
- **Turso write concurrency:** the points/cooldown guarantee depends on SQLite's write
  serialisation (the award transaction re-checks the cooldown under the write lock). Turso
  serialises writes server-side, and the whole flow was verified on the same libSQL driver against
  a local file; re-run the concurrency checks against the provisioned database before opening the
  leaderboard to many students.
- **Login has no rate limiting** (known v1 limitation). Put a Cloudflare rate-limit rule on
  `/api/v1/auth/*` before publicising the URL.
- **Photos are capped at `MAX_UPLOAD_MB` (6 MB)** and Cloud Run accepts up to 32 MB per request;
  keep both in mind if you raise the cap.
- **`VISION_PROVIDER=mock`** approves without any AI review. Never set it in production.

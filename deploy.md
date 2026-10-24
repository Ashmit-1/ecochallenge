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
export TURSO_DB="ecochallenge-ashmit-1"
export DATABASE_URL="libsql://ecochallenge-ashmit-1.aws-ap-south-1.turso.io"
export R2_BUCKET="ecochallenge-photos"
export PAGES_PROJECT="ecochallenge"
export PAGES_DOMAIN="ecochallenge.pages.dev" # or your custom domain
```

> Status of this deployment: the **Turso database is provisioned, migrated, and seeded** (see
> [PROJECT_STATE.md](PROJECT_STATE.md)). Cloud Run and Pages still need to be created, and the R2
> API token still needs to be issued — those steps need dashboard access.

## 0. Prerequisites

| Tool | Why | Check |
|---|---|---|
| A GCP project with billing | Cloud Run + Cloud Build + Artifact Registry | console |
| `gcloud` (option B only) | Deploy without the console | `gcloud version` |
| `turso` CLI (optional) | Create/rotate database tokens | `turso --version` |
| `bun` | Build the frontend from the CLI | `bun --version` |
| Docker (optional) | Test the image locally | `docker --version` |

The console flow (Part 1, option A) enables Cloud Build, Artifact Registry, and the required
service-account roles as it goes. To pre-enable everything, or when using the CLI route:

```bash
gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

bunx wrangler login        # Cloudflare account that will host Pages + R2
```

---

# Part 1 — Backend (Cloud Run)

## 1.1 Turso database

Already provisioned:

| Setting | Value |
|---|---|
| Database | `ecochallenge-ashmit-1` |
| `DATABASE_URL` | `libsql://ecochallenge-ashmit-1.aws-ap-south-1.turso.io` |
| Group region | `aws-ap-south-1` (Mumbai) |
| Schema | migrated to `f3f9b1b53a8a` (initial schema) |
| Data | 5 challenges seeded, no users yet |

The URL only identifies the database; the **auth token** is the credential and it must never be
committed. Keep it in Secret Manager / the Cloud Run console (step 1.4).

To recreate everything from scratch:

```bash
turso db create "$TURSO_DB"
turso db show "$TURSO_DB" --url          # → libsql://…
turso db tokens create "$TURSO_DB"       # → the auth token (keep it secret)
```

The app normalises `libsql://` to the SQLAlchemy libSQL dialect with TLS. You do **not** need to
create tables by hand — the container runs migrations on boot (step 1.4).

> Sanity check from your machine, against the real hosted database:
> ```bash
> cd backend
> DATABASE_URL="$DATABASE_URL" TURSO_AUTH_TOKEN="<token>" uv run alembic upgrade head
> DATABASE_URL="$DATABASE_URL" TURSO_AUTH_TOKEN="<token>" uv run seed
> ```
> Both are idempotent: a second run migrates nothing and refreshes the same 5 challenges.

## 1.2 Create the R2 bucket

Dashboard: **R2 → Create bucket** → name it `ecochallenge-photos` (location: Automatic), or:

```bash
bunx wrangler r2 bucket create "$R2_BUCKET"   # ecochallenge-photos
```

If it already exists, skip — the command just reports that. Then:
**R2 → Manage R2 API Tokens → Create API Token**

- Permissions: **Object Read & Write**
- Scope: this bucket only
- Copy the **Access Key ID**, **Secret Access Key**, and your **Account ID**
  (R2 overview page, right-hand sidebar — the same ID that appears in the S3 endpoint
  `https://<account-id>.r2.cloudflarestorage.com`).

```bash
export R2_ACCOUNT_ID="your-cloudflare-account-id"
```

Keep the bucket **private** (no public access, no custom domain). Photos are served only by the
authenticated `GET /api/v1/submissions/{id}/image` route, which checks ownership first.

> These four R2 values are the one part of the setup that cannot be created for you: Cloudflare
> only issues R2 API tokens in the dashboard.

## 1.3 Secrets

Five values are secrets and must not be plain environment variables:

| Secret | Where it comes from |
|---|---|
| `SECRET_KEY` | generate: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `TURSO_AUTH_TOKEN` | `turso db tokens create ecochallenge-ashmit-1` |
| `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> — the key already in `backend/.env` |
| `R2_ACCESS_KEY_ID` | the R2 API token from step 1.2 |
| `R2_SECRET_ACCESS_KEY` | the R2 API token from step 1.2 |

**In the console (used by option A):** when you add an environment variable, choose
**Reference a secret** → **Create new secret**, paste the value, and pick the secret name. Cloud Run
creates the Secret Manager entry and grants the service account access — no `gcloud` needed.

**With the CLI (used by option B):**

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

Let the Cloud Run service read them (option B only — the console grants access itself):

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

## 1.4 Deploy the container

Two equivalent routes. **Option A** is the console + GitHub flow, which redeploys on every push.
**Option B** is a one-off deploy from your machine.

Both build the checked-in [Dockerfile](backend/Dockerfile); the entrypoint applies Alembic
migrations and the challenge seed on boot, then starts uvicorn on Cloud Run's `$PORT`.

### Option A — connect the GitHub repo (continuous deployment)

The Dockerfile is **not at the repo root**: it is `backend/Dockerfile`, and its `COPY app ./app`
paths are relative to `backend/`. Cloud Run's console has a field for exactly that.

1. Cloud Run → **Create service** → **Connect repository** → **Cloud Build** →
   **Set up with Cloud Build**. Authenticate the Cloud Build GitHub app if prompted and give it
   access to this repository.
2. In the **Build Configuration** step:

| Field | Value |
|---|---|
| Repository | this repo |
| Branch | `^deployment$` (the branch these artifacts are on) |
| Build type | **Dockerfile** |
| Source location | `backend/Dockerfile` |

`Source location` takes the Dockerfile path, and Cloud Run uses that file's directory (`backend/`)
as the Docker build context — which is what the Dockerfile expects. If the build fails with
`COPY failed: file not found` or `/app: not found`, the path was left at the repo root; set it to
`backend/Dockerfile`.

3. In **Configure**, set:

| Setting | Value |
|---|---|
| Service name | `ecochallenge-api` |
| Region | `asia-south1` (Mumbai, next to the Turso `aws-ap-south-1` database) |
| Authentication | **Allow unauthenticated invocations** |
| CPU allocation and pricing | CPU only allocated during request processing |
| Autoscaling | min `0`, max `1` (see the migration note) |
| Ingress | All |
| Container port | `8080` |
| Memory | `1 GiB` |
| CPU | `1` |
| Request timeout | `120` seconds |
| Maximum concurrent requests per instance | `20` |

4. **Variables & Secrets** → add these. Plain values as *environment variables*, the five secrets
   as *secret references* (step 1.3).

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` (turns on `Secure` cookies) |
| `DATABASE_URL` | `libsql://ecochallenge-ashmit-1.aws-ap-south-1.turso.io` |
| `VISION_PROVIDER` | `gemini` (never `mock` in production) |
| `GEMINI_MODEL` | `gemma-4-26b-a4b-it` |
| `STORAGE_BACKEND` | `r2` |
| `R2_BUCKET` | `ecochallenge-photos` |
| `R2_ACCOUNT_ID` | your Cloudflare account ID (or skip it and set `R2_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com`) |
| `MAX_UPLOAD_MB` | `6` (optional; this is the default) |
| `CORS_ORIGINS` | `https://<your Pages domain>` — add after Part 2, since the domain does not exist yet |

| Secret reference | Environment variable |
|---|---|
| `SECRET_KEY` | `SECRET_KEY` |
| Turso token | `TURSO_AUTH_TOKEN` |
| Gemini key | `GEMINI_API_KEY` |
| R2 access key ID | `R2_ACCESS_KEY_ID` |
| R2 secret access key | `R2_SECRET_ACCESS_KEY` |

5. **Create**. The first build takes a few minutes; the service URL appears when it is serving.
   Boot logs should read `Applying database migrations...` → `Seeding the challenge catalogue...` →
   `Starting API on 0.0.0.0:8080...`. Both steps are no-ops on this database (already at head,
   already seeded), so they finish in seconds.

Leave **max instances at 1**. The entrypoint migrates on boot, and two instances cold-starting at
the same moment could race on a schema change. Concurrency 20 on one instance is far more than this
app needs; to scale later, run `alembic upgrade head` yourself before pushing a revision, then raise
the limit.

### Option B — one-off deploy with gcloud

`gcloud run deploy --source .` uploads `backend/` and builds it with the same Dockerfile — no local
Docker required. It creates no trigger, so pushing to GitHub does not redeploy.

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
- `--max-instances 1` so two containers never migrate at the same time. Raise it only after you
  are running migrations yourself before each deploy.
  `ENVIRONMENT=production` turns on `Secure` session cookies.
- `--concurrency 20` keeps each instance comfortably below Turso's connection limits while a
  request waits on the vision model.
- Multiple CORS origins would clash with the comma separator in `--set-env-vars`; use the
  alternate delimiter form `--set-env-vars "^@^A=1@B=2@CORS_ORIGINS=https://a,https://b"`.
- `backend/.gcloudignore` keeps `.env`, virtualenvs, the local database, and uploads out of the
  Cloud Build source upload; `backend/.dockerignore` repeats that for the image build. The built
  image was inspected and contains only `.venv`, `app`, `alembic`, `data`, `uploads`, the
  entrypoint, and `alembic.ini` — no `.env`.

After the first successful deploy, scaling is a deliberate choice — see the migration note above:

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

- **Backend (GitHub trigger, option A):** push to `deployment`. The trigger rebuilds the image and
  rolls out a new revision; watch it under **Cloud Run → the service → Revisions**, or click the
  build log in the service header. Editing environment variables, secrets, or resources in the
  console does **not** need a rebuild.
- **Backend (gcloud, option B):** re-run the `gcloud run deploy --source .` command (step 1.4).
- **Frontend:** push to the connected branch, or re-run `bunx wrangler pages deploy dist`.

The seed is idempotent and never re-activates a retired challenge.

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
| Build fails: `COPY failed: file not found` / `/app: not found` | The build context was the repo root. In the trigger, set **Source location** to `backend/Dockerfile` |
| Build fails: `Cannot locate specified Dockerfile` | Same fix — the Dockerfile lives in `backend/`, not at the repo root |
| `alembic.util.exc.CommandError` / duplicate table | Two containers migrated at once; keep `--max-instances 1` |
| First request after idle is slow | Cloud Run scaled to zero; set `--min-instances 1` for demos |
| Browser console 404 on `/api/...` | Pages project root is not `frontend`, so `functions/` was not bundled |

## Known deployment caveats

- **Migrations on boot** are convenient but not safe under concurrent scaling: deploy schema
  changes with `--max-instances 1`, then scale up.
- **Turso write concurrency:** the points/cooldown guarantee depends on SQLite's write
  serialisation (the award transaction re-checks the cooldown under the write lock). Turso
  serialises writes server-side, and the whole flow was verified on the same libSQL driver; the
  two-simultaneous-approvals check has **not** been re-run against `ecochallenge-ashmit-1` yet. Do
  that (expect one 201 and one 429) before opening the leaderboard to many students.
- **The Turso token was shared in chat.** Treat it as exposed: once the service is running, create
  a fresh token (`turso db tokens create ecochallenge-ashmit-1`), update the Cloud Run secret, and
  revoke the old one (`turso db tokens invalidate`) so it does not outlive the setup.
- **Login has no rate limiting** (known v1 limitation). Put a Cloudflare rate-limit rule on
  `/api/v1/auth/*` before publicising the URL.
- **Photos are capped at `MAX_UPLOAD_MB` (6 MB)** and Cloud Run accepts up to 32 MB per request;
  keep both in mind if you raise the cap.
- **`VISION_PROVIDER=mock`** approves without any AI review. Never set it in production.

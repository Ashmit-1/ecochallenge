# functions/

Cloudflare Pages Functions — server-side handlers that sit in front of the static build. They are
compiled by Pages, not by Vite, so nothing here ships in `dist/`.

| Path | Purpose |
|---|---|
| [api/[[path]].ts](api/[[path]].ts) | Proxies `/api/*` to the Cloud Run backend so the SPA stays same-origin |

## Why the proxy exists

`src/lib/api.ts` calls `/api/v1/...` with relative paths and httpOnly cookies. Cloudflare Pages'
`_redirects` can only proxy **relative** URLs ("You cannot proxy external domains"), so a Pages
Function forwards the requests instead. Same-origin means:

- the session and CSRF cookies are first-party (`COOKIE_SAMESITE=lax` keeps working);
- no CORS configuration is needed;
- the browser sees no third-party API host.

## Configuration

| Setting | Where | Value |
|---|---|---|
| `API_ORIGIN` | Pages project → Settings → Variables and Secrets (production **and** preview) | The Cloud Run service URL, e.g. `https://ecochallenge-api-abc123-uc.a.run.app` |

For `wrangler pages dev`, put `API_ORIGIN=...` in `frontend/.dev.vars` (gitignored). Without it the
function returns `500 {"detail": "API_ORIGIN is not configured for this Pages project."}`.

## Rules

- Forward the request untouched (method, body stream, cookies, `X-CSRF-Token`); only the host changes.
- Never add caching here — `/api/*` must stay live, matching the service worker rule in the contract.
- Keep the handler dependency-free so Pages can bundle it without a build step.

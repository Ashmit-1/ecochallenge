/**
 * Cloudflare Pages Function: forward `/api/*` to the Cloud Run backend.
 *
 * Pages cannot proxy an external origin from `_redirects` ("Proxying will only support relative
 * URLs on your site"), and the SPA calls `/api/v1/...` with relative paths plus httpOnly cookies.
 * Routing those calls through this function keeps the API same-origin: cookies stay first-party,
 * `COOKIE_SAMESITE=lax` and the CSRF double-submit cookie keep working, and no CORS is involved.
 *
 * Configure `API_ORIGIN` (Pages project → Settings → Variables and Secrets), e.g.
 * `https://ecochallenge-api-abc123-uc.a.run.app`. Locally, put it in `frontend/.dev.vars`.
 */

interface Env {
  /** Base URL of the deployed API. Required. */
  API_ORIGIN?: string;
}

interface PagesContext {
  request: Request;
  env: Env;
  params: { path?: string | string[] };
}

export async function onRequest(context: PagesContext): Promise<Response> {
  const { request, env, params } = context;
  const origin = env.API_ORIGIN;

  if (!origin) {
    return new Response(
      JSON.stringify({ detail: "API_ORIGIN is not configured for this Pages project." }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }

  const incoming = new URL(request.url);
  const segments = Array.isArray(params.path) ? params.path.join("/") : (params.path ?? "");
  const target = new URL(`/api/${segments}`, origin);
  target.search = incoming.search;

  // Forward the request as-is (method, body stream, cookies, CSRF header). Only the host changes,
  // so Cloud Run routes on its own hostname.
  const headers = new Headers(request.headers);
  headers.delete("host");

  return fetch(target.toString(), {
    method: request.method,
    headers,
    body: request.body,
    redirect: "manual",
  });
}

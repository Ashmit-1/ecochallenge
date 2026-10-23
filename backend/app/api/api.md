# api/

The HTTP boundary. Routes parse input, call a service, and return a schema — nothing more.

| Path | Purpose |
|---|---|
| [deps.py](deps.py) | Shared dependencies: DB session, current user, vision provider |
| [v1/](v1/v1.md) | Version 1 of the API — every endpoint lives here |

## Rules for this layer

- **No business logic.** If a route contains a domain `if`, it belongs in `services/`.
- **Always declare `response_model`.** It documents the contract and strips accidental fields
  (such as `image_path` or `hashed_password`).
- **Use `CurrentUser` for protected routes**, `OptionalUser` where anonymous browsing is allowed.
  A supplied-but-invalid token is a `401`, not a silent downgrade to anonymous.
- **Raise `HTTPException` with a student-readable `detail`.** Messages are shown in the UI.

## deps.py

- `SessionDep` — one SQLAlchemy session per request, closed by the dependency.
- `CurrentUser` / `OptionalUser` — decodes the bearer JWT, loads the user, enforces `is_active`.
- `VisionDep` — the configured verification provider; tests override this dependency.

## Versioning

`app/api/v1/router.py` mounts the v1 routers with the `/api/v1` prefix. A breaking change means a
new `v2/` package, not changes in place; the frontend pins a version.

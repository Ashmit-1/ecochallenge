# routes/

One module per resource. Each file is thin: parse input → call a service → return a schema.

| File | Endpoints |
|---|---|
| [system.py](system.py) | `GET /health`, `GET /meta` |
| [auth.py](auth.py) | `POST /auth/register`, `POST /auth/login`, `GET\|PATCH /auth/me` |
| [challenges.py](challenges.py) | `GET /challenges`, `GET /challenges/{slug}` |
| [submissions.py](submissions.py) | `POST /challenges/{slug}/submissions`, `GET /submissions`, `GET /submissions/{id}`, `GET /submissions/{id}/image` |
| [profile.py](profile.py) | `GET /profile` |
| [leaderboard.py](leaderboard.py) | `GET /leaderboard` |

## Conventions

- One `APIRouter` per module, `tags=[...]` for docs grouping. Prefixes live in the module.
- Auth via `CurrentUser` / `OptionalUser` from [../deps.py](../deps.py); never decode tokens by hand.
- Uploads read at most `MAX_UPLOAD_MB + 1` bytes, so an oversized file is rejected without being
  loaded into memory in full.
- Images are streamed with `FileResponse` only after `submission_service.get_submission()` proves
  ownership; the uploads directory is never mounted statically.
- Every non-obvious status code is declared in `responses={...}` so the OpenAPI page is honest.
- Error `detail` strings are user-facing copy. Keep them plain and actionable.

## Adding a route

1. Add the function here with an explicit `response_model`.
2. Put the logic in a service; do not add queries to the route.
3. If it is a new module, include its router in [../router.py](../router.py).
4. Update [docs/api.md](../../../../../docs/api.md) and add a test.

# backend/

The FastAPI service: HTTP API, SQLite persistence, AI photo verification, and tests.
Run every command from this directory.

| Path | What it is |
|---|---|
| [app/](app/app.md) | The Python application package — **start here for code changes** |
| [alembic/](alembic/alembic.md) | Migration environment and versioned schema changes |
| [tests/](tests/tests.md) | Pytest suite: isolated DB per test, mocked vision |
| [alembic.ini](alembic.ini) | Alembic config; DB URL comes from `app.core.config` |
| [Dockerfile](Dockerfile) | Cloud Run image: two-stage uv build, non-root runtime, `$PORT` |
| [docker-entrypoint.sh](docker-entrypoint.sh) | Migrate → seed → uvicorn; runs on every container start |
| [.dockerignore](.dockerignore) | Keeps `.env`, local state, and tests out of the image |
| [.gcloudignore](.gcloudignore) | Keeps `.env` and local state out of `gcloud run deploy --source` uploads |
| [pyproject.toml](pyproject.toml) | Dependencies, `seed` script entry, pytest config |
| [uv.lock](uv.lock) | Locked dependency graph — commit it |
| [.env.example](.env.example) | All settings, safe to commit. Copy to `.env` |
| `.env` | Local secrets. **Gitignored, never commit** |
| `data/` | SQLite file lives here (gitignored) |
| `uploads/` | Submitted photos (gitignored; only `.gitkeep` is tracked) |
| [README.md](README.md) | Setup and run instructions |

## Commands

```bash
uv sync                       # install
uv run alembic upgrade head   # create/upgrade schema
uv run seed                   # idempotent starter challenges
uv run fastapi dev            # http://127.0.0.1:8000/docs
uv run pytest -q              # tests
```

If `uv` reports `Read-only file system` for its cache, prefix with
`UV_CACHE_DIR=/tmp/uv-cache`.

## Container / deployment

The container is built from [Dockerfile](Dockerfile) and started by
[docker-entrypoint.sh](docker-entrypoint.sh), which applies `alembic upgrade head`, runs the seed,
then starts uvicorn on Cloud Run's `$PORT` with proxy headers. Production configuration comes from
environment variables only:

- `DATABASE_URL=libsql://<db>-<org>.turso.io` + `TURSO_AUTH_TOKEN` → Turso instead of a local file;
- `STORAGE_BACKEND=r2` + the four `R2_*` settings → photos in Cloudflare R2 instead of `uploads/`.

Full steps (database, bucket, secrets, deploy, rollback): [../deploy.md](../deploy.md).

## Gotchas

- `app/` must stay importable as a package; Alembic and tests both import `app.models` to see
  metadata. A model that is not imported there will silently be missing from migrations.
- The SQLite URL is relative, so it resolves against **this** directory.
- Changing a model requires `uv run alembic revision --autogenerate -m "..."` then reviewing the
  generated file — never rely on `create_all`.

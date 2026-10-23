# backend/

The FastAPI service: HTTP API, SQLite persistence, AI photo verification, and tests.
Run every command from this directory.

| Path | What it is |
|---|---|
| [app/](app/app.md) | The Python application package — **start here for code changes** |
| [alembic/](alembic/alembic.md) | Migration environment and versioned schema changes |
| [tests/](tests/tests.md) | Pytest suite: isolated DB per test, mocked vision |
| [alembic.ini](alembic.ini) | Alembic config; DB URL comes from `app.core.config` |
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

## Gotchas

- `app/` must stay importable as a package; Alembic and tests both import `app.models` to see
  metadata. A model that is not imported there will silently be missing from migrations.
- The SQLite URL is relative, so it resolves against **this** directory.
- Changing a model requires `uv run alembic revision --autogenerate -m "..."` then reviewing the
  generated file — never rely on `create_all`.

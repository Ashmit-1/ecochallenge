# db/

Persistence plumbing and the starter challenge catalogue.

| File | Contains |
|---|---|
| [session.py](session.py) | SQLite engine, `SessionLocal`, `get_session()` FastAPI dependency, PRAGMA setup |
| [seed.py](seed.py) | `CHALLENGES` data + `apply_seed()` upsert + `main()` for `uv run seed` |
| [__init__.py](__init__.py) | Re-exports the engine/session helpers |

## session.py

- Sync SQLAlchemy engine (see [decisions](../../../docs/decisions.md#d1--sqlite-via-sqlmodel-sync-sessions)).
- Relative SQLite paths resolved by `settings.sqlalchemy_url`, so CWD cannot switch databases.
- `PRAGMA foreign_keys=ON` and `busy_timeout=5000` are applied to **every** connection,
  including test engines, via a listener on the `Engine` class.
- `get_session()` yields one session per request and closes it even on exception.

## seed.py

Seeds the five starter challenges, keyed by `slug`, so running it repeatedly is safe:

- **Unknown slug** → inserted.
- **Known slug** → content fields refreshed (title, points, cooldown, CO₂, …), but `is_active` is
  left alone so an admin can retire a challenge without the seed resurrecting it.

Run with `uv run seed`. Re-import after changing challenge copy; do not edit rows by hand.

```bash
uv run seed               # create/refresh
uv run python -m app.db.seed   # equivalent if the console script is unavailable
```

Seeding requires the schema to exist: `uv run alembic upgrade head` first.

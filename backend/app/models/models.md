# models/

SQLModel table definitions. **Tables only** — no business rules, no HTTP, no queries.

| File | Table | Purpose |
|---|---|---|
| [user.py](user.py) | `users` | Student account, hashed password, denormalised `points_total` |
| [challenge.py](challenge.py) | `challenges` | Challenge catalogue: points, cooldown, CO₂ estimate, category, icon |
| [submission.py](submission.py) | `submissions` | One photo attempt + verdict + snapshotted points/impact |
| [base.py](base.py) | — | `utcnow()` — every timestamp is **timezone-aware UTC** |
| [__init__.py](__init__.py) | — | Re-exports everything so Alembic's metadata is complete |

## Relationships

```
User 1 ──── * Submission * ──── 1 Challenge
```

`Submission.challenge` is the only ORM relationship. There is no `User.submissions` backref on
purpose: history is queried explicitly with pagination, never lazily loaded per user.

## Rules that live in the schema

- `users.email`, `users.display_name`, `challenges.slug`, `submissions.image_sha256` are **unique**.
- `submissions` has a composite index `(user_id, challenge_id, created_at)` for the cooldown check.
- `challenge_id` does **not** cascade: a challenge with history cannot be deleted, only deactivated
  (`is_active = false`). `user_id` cascades.
- `submissions.status` is stored as a plain string (`pending`/`approved`/`rejected`/`error`) to keep
  SQLite DDL simple; `SubmissionStatus` is the constant list.

## Changing the schema

1. Edit the model.
2. `uv run alembic revision --autogenerate -m "add x"`
3. **Read the generated migration** — autogenerate misses SQLite column type changes and data
   migrations, and it will happily drop indexes it does not understand.
4. `uv run alembic upgrade head`

`create_all()` is never used outside tests. See [../../alembic/alembic.md](../../alembic/alembic.md).

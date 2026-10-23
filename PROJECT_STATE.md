# Project state

> Living document. **Update this at every milestone**, not continuously. An agent with fresh
> context should be able to read this one file and know exactly where the project stands.
> Last updated: 2026-10-23

## Where we are

**Phase:** backend implementation. **Frontend: not started** (requires explicit user permission).

The repository was scaffolded today. No application code exists yet — only docs, config, and
pinned dependencies.

## Decisions locked

All product/stack decisions are settled and recorded in [docs/decisions.md](docs/decisions.md):
SQLite + SQLModel (sync), JWT access tokens only, Gemini vision behind a provider interface,
synchronous verification, local disk photo storage served auth-gated, no email in v1, Alembic
migrations, open registration, per-challenge CO₂ with documented assumptions, daily cooldown,
exact-duplicate rejection, rule-based badges, React + Vite (frontend, later).

## Works now

- `uv sync` installs FastAPI 0.161, SQLModel 0.48, Alembic 1.20, google-genai on Python 3.12.
- Import smoke test passes for the full dependency stack.
- Repo layout, `.gitignore`, `.env.example`, docs chain, and this state file exist.

## Not built yet

Everything user-facing: models, migrations, auth, challenges, submissions, verification, points,
badges, profile, leaderboard, seed data, tests, frontend.

## Next up

1. `app/core`, `app/db`, `app/models` — config, engine, user/challenge/submission tables.
2. Alembic initial migration.
3. Auth routes + service.
4. Submission pipeline with mock + Gemini providers.
5. Profile, badges, leaderboard.
6. Seed data and the pytest suite.
7. QA subagent audit, then ask permission to start the frontend.

## Known limitations (accepted for v1)

- AI verification can be fooled by a staged photo; treated as a deterrent, not proof.
- Exact-duplicate hashing does not catch re-cropped/re-compressed copies.
- No email verification or password reset; a forgotten password loses the account.
- Open registration means the leaderboard is only as honest as its users.
- SQLite on a single VPS; no horizontal scaling.

## How to verify the current state

```bash
cd backend
uv run python -c "import app"        # once app/ exists
uv run pytest -q
uv run alembic upgrade head
```

## Environment notes

- Python 3.12 is pinned via `.python-version`; the host's 3.14 is intentionally unused.
- `.env` exists locally with a random `SECRET_KEY`; `GEMINI_API_KEY` is still blank.
- Under a restrictive sandbox, uv needs `UV_CACHE_DIR=/tmp/uv-cache`.

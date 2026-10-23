# EcoChallenge — Agent Guide

A gamified sustainability app. Students pick an eco challenge, do it in the real world,
upload photo evidence, and an AI vision model verifies the photo before points are awarded.
Points feed a profile, badges, estimated CO₂ savings, and a leaderboard.

**Current state: backend complete and live-verified. Frontend not started; its contract is ready.**
Read [PROJECT_STATE.md](PROJECT_STATE.md) first.

## Read in this order

1. [PROJECT_STATE.md](PROJECT_STATE.md) — what works, what is stubbed, what is next.
2. This file — navigation map and hard rules.
3. The `<folder>.md` for the folder you are about to touch (see below).

## Navigation: hop, don't read everything

Every directory contains a `<dirname>.md` that lists **only its immediate children** and says
which one to open next. Follow the chain to your target file; do not bulk-read the repo.

```
AGENTS.md → backend/backend.md → app/app.md → services/services.md → submission_service.py
```

| You need to work on | Open this |
|---|---|
| Understand the product or current state | [PROJECT_STATE.md](PROJECT_STATE.md), [docs/docs.md](docs/docs.md) |
| API layer, routes, request/response shapes | [backend/app/api/api.md](backend/app/api/api.md) |
| Database models, schema, migrations | [backend/app/models/models.md](backend/app/models/models.md) → [backend/alembic/alembic.md](backend/alembic/alembic.md) |
| Business rules (points, cooldowns, verification) | [backend/app/services/services.md](backend/app/services/services.md) |
| AI photo verification | [backend/app/vision/vision.md](backend/app/vision/vision.md) |
| Configuration, secrets, JWT | [backend/app/core/core.md](backend/app/core/core.md) |
| Tests | [backend/tests/tests.md](backend/tests/tests.md) |
| Seed challenge data | [backend/app/db/db.md](backend/app/db/db.md) |
| Why a decision was made | [docs/decisions.md](docs/decisions.md) |
| Build the frontend (new session) | [frontend/frontend.md](frontend/frontend.md) → [contract](frontend/frontend-backend-contract.md) |
| Visual design, palette, type, motion | [frontend/design.md](frontend/design.md) |

## Commands

All backend commands run from `backend/`.

```bash
uv sync                      # install deps into .venv
uv run alembic upgrade head  # apply migrations
uv run seed                  # insert/refresh the 5 starter challenges
uv run fastapi dev           # dev server on http://127.0.0.1:8000
uv run pytest -q             # full test suite
```

If `uv` fails with `Read-only file system` on its cache, prefix commands with
`UV_CACHE_DIR=/tmp/uv-cache`. Do not escalate sandbox permissions for this.

## Hard rules

- **Never commit `.env`.** It is gitignored. Update `.env.example` when you add a setting.
- **Install Python packages with `uv add <pkg>`** (or `uv add --dev`) — never edit
  `pyproject.toml` by hand for dependencies.
- **Never invent secrets or fake an integration.** If a key is missing, ask the user to add it.
- **Ask before assuming.** Use the ask-user-question tool rather than guessing a product decision.
- **Keep it minimal.** No speculative abstraction, no unused dependencies.
- **Tests accompany code**, not after it. `uv run pytest -q` must pass before a commit.
- **Commit after each meaningful change** with a conventional, descriptive message.
- **Update docs with the code.** A new file means its folder's `.md` gets a line; a changed
  behavior means [PROJECT_STATE.md](PROJECT_STATE.md) gets updated at the milestone.

## Conventions

- Python 3.12, 4-space indent, type hints on public functions.
- Backend stack: FastAPI + SQLModel + SQLite + Alembic, sync sessions, `def` endpoints.
- API is versioned under `/api/v1`. Errors use FastAPI's `{"detail": ...}` shape.
- Timestamps are UTC. CO₂ values are grams stored as integers.
- Frontend (future): React + Vite + TypeScript + Tailwind + Bun, installable PWA.

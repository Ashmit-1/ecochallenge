# EcoChallenge backend

FastAPI + SQLModel + SQLite + Alembic, managed with [uv](https://docs.astral.sh/uv/).

## Setup

```bash
cp .env.example .env
# edit .env: set SECRET_KEY and GEMINI_API_KEY
uv sync
uv run alembic upgrade head
uv run seed
uv run fastapi dev
```

- API docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/v1/health>

To run without a Gemini key, set `VISION_PROVIDER=mock` in `.env` — submissions then return a
deterministic verdict, which is enough for frontend work and demos. `mock` never contacts the
network.

## Tests

```bash
uv run pytest -q          # fast, no network, mock vision
uv run pytest -q -k auth  # one area
```

Tests use a temporary SQLite file per test and a fresh app instance, so they never touch
`data/ecochallenge.db` or the real uploads folder.

## Layout

`app/` holds everything: `api/` (routes), `services/` (rules), `models/` (tables),
`schemas/` (DTOs), `vision/` (AI provider), `core/` (config/security), `db/` (session/seed).
Each folder has its own `.md` explaining it. Start at [backend.md](backend.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Read-only file system` from uv | prefix commands with `UV_CACHE_DIR=/tmp/uv-cache` |
| `GEMINI_API_KEY is not set` | add the key to `.env`, or set `VISION_PROVIDER=mock` |
| `no such table` | run `uv run alembic upgrade head` |
| Photos rejected unexpectedly | the AI is strict on ambiguous images; the rejection reason is shown and retry is allowed |

# EcoChallenge

**Small actions, made visible.**

EcoChallenge turns everyday sustainable habits into visible progress. Students browse
environmental challenges, complete them in the real world, submit a photo as evidence, and an
AI vision model checks the photo against the claimed activity before awarding points. Points
drive a profile, badges, estimated CO₂ savings, and a campus leaderboard.

## Why

Students already cycle to campus, recycle, and plant saplings — but those actions go unrecorded,
so there is little feedback or recognition. EcoChallenge adds the missing feedback loop, and
uses photo evidence plus AI verification so points are not simply self-reported.

> AI verification reduces obvious mismatches; it cannot prove an activity happened. Every
> impact figure in the app is an estimate.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLModel, SQLite, Alembic, uv |
| Verification | Google Gemini vision, behind a provider interface (mock for tests/offline) |
| Frontend | React + Vite + TypeScript + Tailwind v4, Bun, installable PWA |

## Repository

```
backend/    FastAPI API, database, AI verification, tests
frontend/   React PWA (screens, typed API client, TanStack Query, design system)
docs/       Architecture, decisions, API reference
AGENTS.md   Map for AI coding agents (read this if you are one)
PROJECT_STATE.md  What currently works
```

## Run it

Backend:

```bash
cd backend
cp .env.example .env          # then set GEMINI_API_KEY
uv sync
uv run alembic upgrade head
uv run seed
uv run fastapi dev            # http://127.0.0.1:8000/docs
```

Frontend (dev server proxies `/api` to the backend):

```bash
cd frontend
bun install
bun run dev                   # http://127.0.0.1:5173
bunx tsc -b && bunx vitest run && bunx vite build   # the verification gate
```

The API is also fully usable through the interactive docs at `/docs`; its complete interface
is specified in [frontend/frontend-backend-contract.md](frontend/frontend-backend-contract.md).

## Status

Backend complete, live-verified, and frozen except for defects. Frontend built (milestones 1–4)
and under review. See [PROJECT_STATE.md](PROJECT_STATE.md) for the exact, honest state of every
feature.

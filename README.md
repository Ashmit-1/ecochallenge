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
| Frontend (next) | React + Vite + TypeScript + Tailwind, Bun, installable PWA |

## Repository

```
backend/    FastAPI API, database, AI verification, tests
docs/       Architecture, decisions, API reference
AGENTS.md   Map for AI coding agents (read this if you are one)
PROJECT_STATE.md  What currently works
```

## Run it

```bash
cd backend
cp .env.example .env          # then set GEMINI_API_KEY
uv sync
uv run alembic upgrade head
uv run seed
uv run fastapi dev            # http://127.0.0.1:8000/docs
```

The frontend is not built yet; the API is fully usable through the interactive docs at `/docs`.

## Status

Backend under active construction. See [PROJECT_STATE.md](PROJECT_STATE.md) for the exact,
honest state of every feature.

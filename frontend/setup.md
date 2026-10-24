# Frontend setup

How to set up, run, and verify the EcoChallenge frontend from a clean checkout.
The authoritative API reference is [frontend-backend-contract.md](frontend-backend-contract.md);
this file is about getting the code on your machine and running.

> Shorter pointers already exist elsewhere: `frontend.md` → "Running" and
> "Verification gate", `PROJECT_STATE.md` → "How to verify the current state".
> This file is the complete, start-here version.

---

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| **Bun** ≥ 1.x | Package manager + dev server + test runner | `bun --version` |
| **Python 3.12** + **uv** | Runs the backend the frontend talks to | `uv --version` |
| **Node** | Not required — Bun handles everything frontend-side | — |

The frontend has **no secrets of its own**. All secrets live in `backend/.env`
(never commit `.env`; copy from `.env.example`).

---

## 2. One-time setup

From the repository root:

```bash
# 2a. Backend (the frontend's data source) — must be seeded and running
cd backend
cp .env.example .env          # then put a real GEMINI_API_KEY in .env
uv sync
uv run alembic upgrade head
uv run seed                   # inserts the 5 starter challenges

# 2b. Frontend dependencies
cd ../frontend
bun install
```

Sandbox note: if Bun or uv report `Read-only file system` on their cache, prefix
commands with `BUN_TMPDIR=/tmp/bun-tmp BUN_INSTALL=/tmp/bun-install` (frontend)
or `UV_CACHE_DIR=/tmp/uv-cache` (backend). Do not escalate permissions for this.

---

## 3. Run it

```bash
# Terminal 1 — backend on http://127.0.0.1:8000
cd backend
uv run fastapi dev            # /docs for the interactive API

# Terminal 2 — frontend on http://127.0.0.1:5173
cd frontend
bun run dev
```

- The Vite dev server proxies `/api` → `http://127.0.0.1:8000`
  (`vite.config.ts`), so the browser sees one origin and the httpOnly cookie
  auth works with no extra CORS setup.
- **Offline/demo AI:** set `VISION_PROVIDER=mock` in `backend/.env` — every
  photo is approved unless its bytes contain `MOCK-REJECT` (no network, no key).
  With a real `GEMINI_API_KEY`, photo verification hits Gemini live (2–6 s).
- Create an account at `http://127.0.0.1:5173/register`, then log in.

---

## 4. Verification gate (before committing or merging)

```bash
cd frontend
bun run typecheck   # tsc -b — the REAL type gate (see note below)
bun run test        # vitest — API client, auth guards, submission flow, theme regressions
bun run lint        # oxlint
bun run build       # tsc -b && vite build → dist/
bun run scripts/check-doodle.ts   # wallpaper embed ↔ generator sync + tile coverage
```

> **`tsc -b`, not bare `tsc --noEmit`:** the root `tsconfig.json` is a
> references-only stub, so `tsc --noEmit` checks nothing and always "passes".
> Always use `bun run typecheck` (or `bunx tsc -b`).

Backend suite (unchanged by frontend work): `cd backend && uv run pytest -q`.

---

## 5. Optional: regenerate generated assets

```bash
cd frontend
bun run scripts/generate-icons.ts      # PWA icons (192/512/maskable) → public/icons/
python3 scripts/gen-doodle.py          # wallpaper tile CSS → paste into src/styles/index.css
python3 scripts/gen-doodle.py --preview out.svg   # 3×2 visual check of the tile
bun run scripts/check-doodle.ts        # verify the CSS still matches the generator
```

Run these only when the PWA mark or the wallpaper artwork changes.

---

## 6. Related docs

| Need | Open |
|---|---|
| API contract, types, auth, PWA rules | [frontend-backend-contract.md](frontend-backend-contract.md) |
| Visual design (type, palette, wallpaper, motion) | [design.md](design.md) |
| Source tree navigation | [src/src.md](src/src.md) |
| What works / what's next | [../PROJECT_STATE.md](../PROJECT_STATE.md) |
| Agent rules + navigation chain | [../AGENTS.md](../AGENTS.md) |

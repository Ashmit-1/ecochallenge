# Project state

> Living document. **Update at every milestone**, not continuously. A fresh agent should read this
> one file and know exactly where the project stands.
> Last updated: 2026-10-23 (backend feature-complete, pre-frontend)

## Where we are

**Phase:** backend implemented and tested. **Frontend: not started** — requires the owner's
explicit permission before any frontend work begins.

The API is fully usable through Swagger at `/docs`. The one thing not yet exercised is a **live
Gemini call**: `backend/.env` still has an empty `GEMINI_API_KEY`. Everything else is verified by
70 passing tests and a manual end-to-end run against a temp database.

## Works now (verified)

- `uv sync`, `uv run alembic upgrade head`, `uv run seed` against SQLite.
- Registration, login (OAuth2 form), `GET/PATCH /auth/me`; Argon2 hashes, 7-day HS256 JWT.
- Challenge catalogue with per-student cooldown state (5 seeded challenges).
- Photo submission: magic-byte validation, 6 MB cap, 24 h/168 h/72 h cooldowns, SHA-256 duplicate
  rejection, private file storage, synchronous verification, points awarded only on approval.
- Provider abstraction: `MockVisionProvider` (tests/offline) and `GeminiVisionProvider` (live).
  Provider outages return `502`, store the attempt as `error`, and allow the same photo to be retried.
- Profile: points, attempts, approvals, distinct challenges, estimated CO₂, rank, badges.
- Rule-based badges (6 definitions), new-badge reporting on approval.
- Leaderboard with `RANK()`, shared ranks on ties, pagination, current-user flag.
- Uvicorn boot verified: `/api/v1/health` → `ok`, `/docs` → 200, `/openapi.json` → 200.

## Not built yet

- Entire frontend (React + Vite + TS + Tailwind + PWA) — intentionally blocked.
- Password reset / email verification (out of v1 scope).
- Admin/audit portal, reward redemption, photo metadata checks (future enhancements).
- Deployment artifacts (Docker/nginx/systemd) — waiting on the VPS decision.
- A live Gemini verification run — waiting on the API key.

## Next up

1. Owner adds `GEMINI_API_KEY` to `backend/.env`; run one real photo through the API and record the
   verdict in this file.
2. Ask the owner for permission, then scaffold the frontend per the same documentation rules.
3. Revisit deployment once the VPS is confirmed.

## Known limitations (accepted for v1)

- AI verification can be fooled by a staged photo; it is a deterrent, not proof.
- Only *exact* duplicate photos are detected; re-encoded copies pass.
- No email means no password reset; a forgotten password loses the account.
- Open registration means the leaderboard is only as honest as its users.
- SQLite + one VPS; no horizontal scaling.
- `points_total` is denormalized; if it ever drifts, rebuild with
  `SUM(points_awarded)` over that user's approved submissions.

## How to verify the current state

```bash
cd backend
uv run alembic upgrade head
uv run pytest -q                          # 70 passed
uv run fastapi dev                        # http://127.0.0.1:8000/docs
```

Sandbox note: if uv reports `Read-only file system`, prefix commands with
`UV_CACHE_DIR=/tmp/uv-cache-ecochallenge`.

## Environment notes

- Python 3.12 pinned via `.python-version`; the host's 3.14 is deliberately unused.
- `backend/.env` exists locally with a random `SECRET_KEY`; `GEMINI_API_KEY` is **empty**.
- `VISION_PROVIDER=mock` is a supported way to run the whole app without a key.
- Dev database: `backend/data/ecochallenge.db` (gitignored). Photos: `backend/uploads/` (gitignored).

## Git

- `8026c5a` scaffold: docs chain, config, pinned dependencies
- `58eb0ff` backend: API, models, migrations, services, tests

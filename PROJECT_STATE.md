# Project state

> Living document. **Update at every milestone**, not continuously. A fresh agent should read this
> one file and know exactly where the project stands.
> Last updated: 2026-10-23 (backend complete, cookie auth added, frontend contract ready)

## Where we are

**Phase:** backend complete, audited, hardened, live-verified, and now cookie-authenticated for a
browser SPA. **Frontend: not started** — the owner will open a new session for it.

The backend is frozen except for defects. The frontend's complete interface lives in
[frontend/frontend-backend-contract.md](frontend/frontend-backend-contract.md); that file, not the
backend source, is the frontend's point of contact.

Live verification passed end to end: a real campus bicycle photo was approved (confidence 0.95,
50 points), a laptop photo on another challenge was rejected (confidence 1.0, 0 points), the badge
unlocked once, the cooldown became active, and history recorded both attempts.

## Works now (verified)

- Registration, login, logout, `GET/PATCH /auth/me`. Argon2 hashes, 7-day HS256 JWT requiring
  `exp`/`sub`, plus an **httpOnly cookie session** with a double-submit CSRF cookie/header.
  Bearer tokens still work for Swagger and non-browser clients.
- Challenge catalogue with per-student cooldown state (5 seeded challenges).
- Photo submission pipeline:
  - full Pillow decode (JPEG/PNG/WebP, ≥200×200 px, 6 MB cap, 40 MP pixel cap);
  - cooldown measured from **approval time**, enforced again under SQLite's write lock;
  - SHA-256 duplicate rejection; errored/abandoned rows retryable on the same challenge only;
  - private local storage, synchronous verification, points only on approval.
- Live provider: `gemma-4-26b-a4b-it` via `GeminiVisionProvider`; `MockVisionProvider` offline.
- Profile: points, attempts, approvals, distinct challenges, estimated CO₂, rank, badges.
- Rule-based badges (6), new-badge reporting on approval.
- Leaderboard with `RANK()`, shared ranks on ties, pagination, current-user flag.
- Request-body limit and CSRF middleware.
- 97 pytest tests, no network; `alembic check` reports no drift.

## Evidence for the claims above

| Check | Result |
|---|---|
| `uv run pytest` | 97 passed |
| Live Gemini: campus bicycle photo | `approved`, confidence 0.95, +50 points, +1,000 g CO₂ |
| Live Gemini: laptop photo on "recycle waste" | `rejected`, confidence 1.0, 0 points, concrete reason |
| Live profile after both | 50 pts, 1 approved, 1 rejected, rank 1, cooldown active |
| Cookie flow over real HTTP | register 201 sets cookies, `/auth/me` 200, logout 403 without CSRF, 204 with it |
| Concurrent approvals, same challenge | one `201`, one `429`, `points_total == 50` |
| Cooldown-bypass regression (10-day-old errored retry) | retry `201`, immediate second `429`, 50 points |
| 5 concurrent approvals, different challenges | all `201`, 280 points, 12,150 g CO₂ |
| Bare 8-byte PNG signature upload | `415` (was `201 approved`) |
| Fresh DB upgrade + downgrade + re-upgrade | passes; `alembic check` → no drift |
| `uv run fastapi dev` | health ok, `/docs` 200, `/redoc` 404 |

## Frontend decisions locked (not built)

- React + Vite + TypeScript + Tailwind + Bun; installable PWA.
- TanStack Query + React Router.
- PWA: installable app shell, data always online (no offline cache or queue).
- Auth: httpOnly cookie + `X-CSRF-Token` — **backend side is done**.
- Visual direction: **Fresh botanical** — airy whites, leaf greens, soft rounded cards, friendly
  iconography; mobile and laptop equally first-class.
- Full contract: [frontend/frontend-backend-contract.md](frontend/frontend-backend-contract.md).

## Not built yet

- Entire frontend (next session; see [frontend/frontend.md](frontend/frontend.md)).
- Password reset / email verification (out of v1 scope).
- Admin/audit portal, reward redemption, photo-metadata anti-spoofing (future enhancements).
- Deployment artifacts (Docker/nginx/systemd) — waiting on the VPS decision.

## Next up

1. A new session scaffolds the frontend from [frontend/frontend.md](frontend/frontend.md) and the
   contract, building against the existing cookie auth.
2. Revisit deployment once the VPS is confirmed.

## Known limitations (accepted for v1)

- AI verification can be fooled by a staged photo; it is a deterrent, not proof.
- Only *exact* duplicate photos are detected; re-encoded copies pass.
- `VISION_PROVIDER=mock` approves without any AI review. Development only; `/meta` reports the
  active provider so the UI can warn.
- No email means no password reset; a forgotten password loses the account.
- Open registration means the leaderboard is only as honest as its users.
- Login has no rate limiting; add a proxy-level limit before exposing this publicly.
- Display-name uniqueness uses SQLite `lower()`, which folds ASCII only — Unicode case variants of
  a name can coexist.
- Request-size middleware reads `Content-Length`; a chunked upload still needs a proxy limit.
- SQLite + one VPS; no horizontal scaling.
- `points_total` is denormalized; if it ever drifts, rebuild with `SUM(points_awarded)` over that
  user's approved submissions.

## How to verify the current state

```bash
cd backend
uv run alembic upgrade head
uv run pytest -q
uv run fastapi dev            # http://127.0.0.1:8000/docs
```

Sandbox note: if uv reports `Read-only file system`, prefix commands with
`UV_CACHE_DIR=/tmp/uv-cache`.

## Environment notes

- Python 3.12 pinned via `.python-version`; the host's 3.14 is deliberately unused.
- `backend/.env` has a real `GEMINI_API_KEY` and `GEMINI_MODEL=gemma-4-26b-a4b-it` (never commit it).
- `backend/.env.example` documents every setting and is safe to commit.
- Dev database: `backend/data/ecochallenge.db` (gitignored). Photos: `backend/uploads/` (gitignored).

## Audit history

An independent fresh-context audit (correctness + adversarial + docs) found and we fixed:

1. **Cooldown bypass** — a retried errored photo kept its old `created_at`, so two approvals could
   land inside one cooldown. Fixed by measuring cooldown from `verified_at` (D7, D14).
2. **Concurrent double-award** — check-then-act outside a transaction. Fixed by re-checking under
   the write lock (D14).
3. **Magic-byte-only uploads** — an 8-byte PNG signature earned points in mock mode. Fixed by full
   Pillow decoding (D15).
4. Provider error text leaking; integer overflow 500s; retries re-targeting another challenge; JWT
   without `exp`; docs drift. All fixed and regression-tested.

## Git

Run `git log --oneline` for history. Commits are scoped: scaffold → backend → hardening →
live-verification record → cookie auth + frontend contract.

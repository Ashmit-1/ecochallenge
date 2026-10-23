# Project state

> Living document. **Update at every milestone**, not continuously. A fresh agent should read this
> one file and know exactly where the project stands.
> Last updated: 2026-10-23 (backend complete and verified live; frontend awaiting permission)

## Where we are

**Phase:** backend complete, audited, hardened, and verified against the real Gemini/Gemma API.
**Frontend: not started** — the owner asked to give explicit permission first.

Live verification passed end to end: a real campus bicycle photo was approved (confidence 0.95,
50 points), a laptop photo on a different challenge was rejected (confidence 1.0, 0 points), the
badge unlocked once, the cooldown became active, and history recorded both attempts.

## Works now (verified)

- Registration, login (OAuth2 form), `GET/PATCH /auth/me`; Argon2 hashes, 7-day HS256 JWT requiring
  `exp` and `sub`.
- Challenge catalogue with per-student cooldown state (5 seeded challenges).
- Photo submission pipeline:
  - full Pillow decode (JPEG/PNG/WebP, ≥200×200 px, 6 MB cap, 40 MP pixel cap);
  - cooldown measured from **approval time**, enforced again under SQLite's write lock;
  - SHA-256 duplicate rejection; errored/abandoned rows retryable on the same challenge only;
  - private local storage, synchronous verification, points only on approval.
- Live provider: `gemma-4-26b-a4b-it` via `GeminiVisionProvider`; `MockVisionProvider` for offline
  work and tests. Outages return `502`, keep the attempt as `error`, never leak provider text.
- Profile: points, attempts, approvals, distinct challenges, estimated CO₂, rank, badges.
- Rule-based badges (6), new-badge reporting on approval.
- Leaderboard with `RANK()`, shared ranks on ties, pagination, current-user flag.
- Request-body limit middleware rejects oversized bodies before multipart parsing.
- 91 pytest tests, no network; `alembic check` reports no drift.

## Evidence for the claims above

| Check | Result |
|---|---|
| `uv run pytest` | 91 passed |
| Live Gemini: campus bicycle photo | `approved`, confidence 0.95, +50 points, +1,000 g CO₂ |
| Live Gemini: laptop photo on "recycle waste" | `rejected`, confidence 1.0, 0 points, concrete reason |
| Live profile after both | 50 pts, 1 approved, 1 rejected, rank 1, bike cooldown active |
| Concurrent approvals, same challenge | one `201`, one `429`, `points_total == 50` |
| Cooldown-bypass regression (10-day-old errored retry) | retry `201`, immediate second `429`, 50 points |
| 5 concurrent approvals, different challenges | all `201`, 280 points, 12,150 g CO₂ |
| Bare 8-byte PNG signature upload | `415` (was `201 approved`) |
| Fresh DB `alembic upgrade head` + `downgrade base` + re-upgrade | passes; `alembic check` → no drift |
| `uv run fastapi dev` | `/api/v1/health` ok, `/docs` 200, `/redoc` 404 |

## Frontend decisions locked (not built)

- React + Vite + TypeScript + Tailwind CSS + Bun; installable PWA.
- **TanStack Query + React Router** for data and navigation.
- **PWA scope:** installable app shell, data always online (no offline cache or queue).
- **Auth storage:** `httpOnly` cookie — this requires a backend change (cookie login, CORS
  credentials, CSRF protection) before or alongside the frontend.
- **Visual direction:** *Fresh botanical* — airy whites, leaf greens, soft rounded cards, friendly
  iconography. Must feel human, not template-generated.
- Mobile-first; must work well on phone and laptop.

## Not built yet

- Entire frontend — blocked on the owner's explicit permission.
- Cookie-based auth + CSRF for the frontend (see above).
- Password reset / email verification (out of v1 scope).
- Admin/audit portal, reward redemption, photo-metadata anti-spoofing (future enhancements).
- Deployment artifacts (Docker/nginx/systemd) — waiting on the VPS decision.

## Next up

1. Owner grants permission, then scaffold the frontend under the same documentation rules.
2. Add cookie auth + CSRF to the backend as part of that work, with tests.
3. Revisit deployment once the VPS is confirmed.

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
4. Provider error text leaking into responses/history; integer overflow 500s; retries re-targeting
   another challenge; JWT without `exp`; docs drift. All fixed and regression-tested.

## Git

- `8026c5a` scaffold: docs chain, config, pinned dependencies
- `58eb0ff` backend: API, models, migrations, services, tests
- `22dabda` hardening: cooldown/concurrency fixes, image decoding, input bounds, docs
- `3586b6f` docs: audited state
- pending: live verification results + tested model default

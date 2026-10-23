# Project state

> Living document. **Update at every milestone**, not continuously. A fresh agent should read this
> one file and know exactly where the project stands.
> Last updated: 2026-10-23 (backend hardened after independent audit)

## Where we are

**Phase:** backend implemented, tested, and hardened. **Frontend: not started** — requires the
owner's explicit permission before any frontend work begins.

The API is fully usable through Swagger at `/docs`. The one unverified path is a **live Gemini
call**: `backend/.env` still has an empty `GEMINI_API_KEY`. Everything else is covered by 91 passing
tests, migration checks, and manual end-to-end runs against throwaway databases.

## Works now (verified)

- `uv sync`, `uv run alembic upgrade head`, `uv run seed`, `uv run fastapi dev`.
- Registration, login (OAuth2 form), `GET/PATCH /auth/me`; Argon2 hashes, 7-day HS256 JWT that must
  carry `exp` and `sub`.
- Challenge catalogue with per-student cooldown state (5 seeded challenges).
- Photo submission pipeline:
  - full Pillow decode (JPEG/PNG/WebP, ≥200×200 px, 6 MB cap, 40 MP pixel cap);
  - cooldown measured from **approval time**, enforced again under SQLite's write lock;
  - SHA-256 duplicate rejection, with errored/abandoned rows retryable on the same challenge only;
  - private local storage, synchronous verification, points only on approval.
- Provider abstraction: `MockVisionProvider` (tests/offline) and `GeminiVisionProvider` (live).
  Outages return `502`, keep the attempt as `error`, and never leak provider text.
- Profile: points, attempts, approvals, distinct challenges, estimated CO₂, rank, badges.
- Rule-based badges (6), new-badge reporting on approval.
- Leaderboard with `RANK()`, shared ranks on ties, pagination, current-user flag.
- Request-body limit middleware rejects oversized bodies before multipart parsing.
- 91 pytest tests, no network; `alembic check` reports no drift.

## Evidence for the claims above

| Check | Result |
|---|---|
| `uv run pytest` | 91 passed |
| Concurrent approvals, same challenge | one `201`, one `429`, `points_total == 50` |
| Cooldown-bypass regression (10-day-old errored retry) | retry `201`, immediate second `429`, 50 points |
| 5 concurrent approvals, different challenges | all `201`, 280 points, 12,150 g CO₂ |
| Bare 8-byte PNG signature upload | `415` (was `201 approved`) |
| Fresh DB `alembic upgrade head` + `downgrade base` + re-upgrade | passes; `alembic check` → no drift |
| `uv run fastapi dev` | `/api/v1/health` ok, `/docs` 200, `/redoc` 404 |
| Uvicorn boot | health 200, docs 200, challenges 200 |

## Not built yet

- Entire frontend (React + Vite + TS + Tailwind + PWA) — intentionally blocked.
- Password reset / email verification (out of v1 scope).
- Admin/audit portal, reward redemption, photo-metadata anti-spoofing (future enhancements).
- Deployment artifacts (Docker/nginx/systemd) — waiting on the VPS decision.
- A live Gemini verification run — waiting on the API key.

## Next up

1. Add `GEMINI_API_KEY` to `backend/.env`, run one real campus-bike photo through the API, and record
   the verdict here. Update `VISION_PROVIDER` only if you intentionally want mock mode.
2. Ask the owner for permission, then scaffold the frontend under the same documentation rules.
3. Revisit deployment once the VPS is confirmed.

## Known limitations (accepted for v1)

- AI verification can be fooled by a staged photo; it is a deterrent, not proof.
- Only *exact* duplicate photos are detected; re-encoded copies pass.
- `VISION_PROVIDER=mock` approves without any AI review. It is for development only; `/meta`
  reports the active provider so the UI can warn.
- No email means no password reset; a forgotten password loses the account.
- Open registration means the leaderboard is only as honest as its users.
- Login has no rate limiting; put a limit at the reverse proxy before exposing this publicly.
- Display-name uniqueness uses SQLite `lower()`, which folds ASCII only — Unicode case variants of
  a name can coexist. Acceptable at campus scale, fixable with a casefolded key column.
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
- `backend/.env` exists locally with a random `SECRET_KEY`; `GEMINI_API_KEY` is **empty**.
- Dev database: `backend/data/ecochallenge.db` (gitignored). Photos: `backend/uploads/` (gitignored).
- The owner's machine runs this under a file sandbox: uv may need a writable cache dir.

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

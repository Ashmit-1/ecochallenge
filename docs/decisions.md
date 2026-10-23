# Decision log

Short records of choices that would be expensive to reverse. Newest last.

---

## D1 — SQLite via SQLModel, sync sessions

**Context.** Small-scale single-VPS app, one developer, no concurrent-write pressure.
**Decision.** SQLite + SQLModel + synchronous SQLAlchemy sessions, `def` endpoints (FastAPI runs
them in a threadpool), Alembic for migrations.
**Why.** SQLite removes an entire ops surface. Sync SQLModel is far less error-prone than async
sessions for a solo build, and with `def` endpoints the blocking driver never stalls the loop.
**Cost.** A slow Gemini call occupies a threadpool worker for a few seconds. Irrelevant at campus
scale; would matter under thousands of concurrent submissions.

## D2 — Denormalized `User.points_total`

**Context.** Leaderboard and rank need a total per user.
**Decision.** Store a running total, incremented in the approval transaction.
**Why.** Ranking with a window function over a pre-aggregated column stays simple and fast, and
the profile read is one row. Snapshot fields on submissions make history immutable.
**Cost.** Two sources of truth. Mitigated by updating both inside one transaction and by
documenting the rebuild query (`SUM(points_awarded)` over approved submissions).

## D3 — JWT access token, cookie session, no refresh token

**Context.** Students, low-stakes data, single deploy, a browser SPA/PWA that must survive reloads.
**Decision.** HS256 JWT with a 7-day expiry. Browsers receive it as an `HttpOnly` cookie; API
clients and Swagger may use `Authorization: Bearer`. No refresh tokens and no server-side session
table. Cookie sessions also carry a readable CSRF cookie and a double-submit header check (D16).
**Why.** Stateless and adequate. Logout is client-side. Expiry is long enough that users rarely
notice.
**Cost.** A stolen token is valid until expiry and cannot be revoked individually. Acceptable
for v1; a token-version column on `User` is the upgrade path. The login response still returns the
raw token for Swagger/API clients; the SPA is required to ignore and never store it.

## D4 — Gemini behind a `VisionProvider` interface

**Context.** AI verification is the one fragile, paid, external dependency.
**Decision.** A `Protocol` with `GeminiVisionProvider` and `MockVisionProvider` implementations,
selected by `VISION_PROVIDER`.
**Why.** Tests stay offline and deterministic; the app runs with no key; swapping to OpenAI or a
local model touches one file.
**Cost.** One extra abstraction. Justified by the testing and offline story. The model is data
(`GEMINI_MODEL`), not a code constant: `gemma-4-26b-a4b-it` is the verified default, and
`gemini-2.5-flash` also works.

## D5 — Synchronous verification

See [architecture.md](architecture.md#why-synchronous-verification). Chosen for a 2–6s verdict
with no queue, worker, or polling UI. `pending` remains a valid status for a future async path.

## D6 — Photos on local disk, served through an authenticated route

**Decision.** Files under `uploads/{user_id}/{uuid}.ext`; the DB stores a relative path. Images
are served by `GET /submissions/{id}/image`, which checks ownership.
**Why.** No cloud account or credentials; files travel with the database in backups. Evidence
photos are private, so static serving (guessable URLs) was rejected.
**Cost.** Single-VPS coupling. Moving to S3 means changing the storage service only, because
routes never touch the filesystem directly.

## D7 — One-day cooldown per challenge, applied to approvals

**Decision.** `Challenge.cooldown_hours` (default 24; sapling 168, cleanup 72). Checked against
the newest **approved** submission only, measured from `verified_at` (approval time), never from
upload time.
**Why.** Habits are daily, so one-time challenges would kill retention; unlimited repeats invite
farming. Rejections do not lock the user out, so a bad photo is recoverable immediately. Approval
time is used because a retried error row keeps its original `created_at`; charging the cooldown
from upload time let a days-old failed upload count as an old approval.
**Cost.** A student can still submit a fresh photo of the same activity every day — which is the
intended behaviour. Concurrency is handled by re-checking the cooldown inside the write
transaction that awards points (see D14).

## D8 — Exact-duplicate rejection via SHA-256

**Decision.** Unique index on `Submission.image_sha256`; check before calling the AI.
**Why.** Catches the cheapest fraud (re-uploading the same file, across accounts) for free and
saves API cost. Not perceptual hashing — that risks false positives.
**Cost.** A re-encoded copy slips through; that is what the AI and the future metadata checks are
for. Scoped honestly in the UI copy.

## D9 — Rule-based badges, computed on read

**Decision.** Badge definitions live in `services/badge_service.py`; progress is derived from
counts. Nothing is stored except the submissions themselves.
**Why.** No badge table, no award job, no drift between what the rules say and what the database
says. New badges are a code change that instantly applies retroactively.
**Cost.** Recomputing on each profile read; trivial at this scale.

## D10 — Open registration, no email in v1

**Decision.** Email + password, open signup, no verification mail, no password reset.
**Why.** Removes SMTP configuration and a whole failure mode. The leaderboard is for a campus
demo, not a competition with prizes.
**Cost.** Fake accounts are possible, and a forgotten password means a lost account (until reset
lands). Documented as a known limitation.

## D11 — Documentation that chains (`AGENTS.md` → `<folder>.md`)

**Decision.** Root `AGENTS.md` maps the project; each directory has a `<dirname>.md` describing
only its immediate children; `PROJECT_STATE.md` tracks live status.
**Why.** An agent with fresh context should reach any file in three hops without reading the
repo, and should never load a 1,000-line manual.
**Cost.** Docs must be maintained with code. Enforced by the rules in `AGENTS.md`.

## D12 — Python 3.12, not 3.14

**Decision.** Pin the project to 3.12.
**Why.** The host has 3.14, but wheel support for the SQLModel/SQLAlchemy/argon2 stack is not
guaranteed there. 3.12 is the current well-supported baseline; `uv` manages it automatically.

## D13 — `app/` package inside `backend/`

**Decision.** Importable package at `backend/app`, not a flat `backend/` module root.
**Why.** Namespacing, trivial test imports, and room for `scripts/` or a future `worker/` without
restructuring. `alembic`, `tests`, and `uploads` stay outside the package.

## D14 — Awards are finalised under SQLite's write lock

**Context.** The cooldown is a check-then-act rule: read the last approval, then award later, after
a 2–6 s AI call. Two concurrent uploads can both pass the read.
**Decision.** The award transaction starts with a conditional `UPDATE ... WHERE status = 'pending'`
(which takes SQLite's write lock), then re-checks the cooldown inside that transaction before
incrementing points. A loser is discarded and told to retry after the cooldown.
**Why.** Writers are serialised in SQLite, so the second request either sees the first's committed
approval or blocks until it commits. This is the cheapest correct fix at this scale.
**Cost.** A losing request has already paid for one AI call. Acceptable, and it cannot award points.

## D15 — Uploads are decoded, and request bodies are capped early

**Decision.** `validate_image()` decodes with Pillow (format must match the magic bytes, at least
200×200 px, under a 40 MP pixel cap). A `RequestBodyLimitMiddleware` rejects bodies larger than
`MAX_UPLOAD_MB + 256 KB` from their `Content-Length` before multipart parsing.
**Why.** Magic-byte checks alone accepted an 8-byte PNG signature and, under the mock provider,
awarded points for it. Decoding also protects the paid Gemini call from junk input. The middleware
prevents Starlette from spooling an unbounded body to disk before the handler can return 413.
**Cost.** Pillow is one extra dependency, and a reverse proxy still needs `client_max_body_size`
because a chunked request has no declared length.

## D16 — httpOnly cookie session with double-submit CSRF

**Context.** The frontend owner chose cookie auth over `localStorage` so an XSS bug cannot read the
session token from storage.
**Decision.** `access_token` is set as an `HttpOnly`, `SameSite=Lax`, `Secure`-in-production cookie.
A second, JavaScript-readable `ecochallenge_csrf` cookie is compared against an `X-CSRF-Token`
header on every unsafe method. Bearer requests are exempt (the browser does not attach them
automatically, so they are not CSRF-replayable). CORS stays credential-enabled with explicit origins.
**Why.** Double-submit is stateless and needs no extra table. `SameSite=Lax` blocks the common
cross-site POST before the header check even runs.
**Cost.** The SPA needs a fetch wrapper that adds the header and sets `credentials: "include"`.
Cookies require HTTPS in production. If the frontend and API ever live on different registrable
domains, `SameSite`/`Secure`/`COOKIE_DOMAIN` must be revisited.

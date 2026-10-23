# Project state

> Living document. **Update at every milestone**, not continuously. A fresh agent should read this
> one file and know exactly where the project stands.
> Last updated: 2026-10-23 (frontend revisions: type swap to Newsreader + Manrope, eco-doodle wallpaper, milestones 1–4 + audit fixes: 68 tests, all gates green)

## Where we are

**Phase:** backend complete and frozen. **Frontend milestones 1–4 complete, two bugfix rounds,
a three-agent audit, plus revision r2** (type swap to Newsreader + Manrope, eco-doodle wallpaper) (code review, tests, docs) — all findings integrated. All
screens, typed API client, TanStack Query layer, PWA shell (incl. offline screen), auth flow,
design polish + accessibility, **68 tests passing**. Gates: `tsc -b` 0 errors, oxlint 0/0,
`vitest` 68/68, `vite build` green. Live end-to-end verified through the Vite dev proxy.

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

## Frontend decisions (locked and implemented)

- React + Vite + TypeScript + Tailwind + Bun; installable PWA.
- TanStack Query + React Router.
- PWA: installable app shell, data always online (no offline cache or queue).
- Auth: httpOnly cookie + `X-CSRF-Token` — **backend side is done**.
- Visual direction: **Fresh botanical** — airy whites, leaf greens, soft rounded cards, friendly
  iconography; mobile and laptop equally first-class.
- Full contract: [frontend/frontend-backend-contract.md](frontend/frontend-backend-contract.md).
- Visual spec: [frontend/design.md](frontend/design.md) — palette, **Newsreader + Manrope** type,
  eco-doodle wallpaper, screen intent, states, motion, accessibility, anti-patterns.

## Frontend milestone 2 (complete)

- Shared UI primitives: Button, Card, Chip, IconChip, Skeleton, EmptyState, Input (Fresh Botanical theme).
- Layout with responsive nav: desktop top bar + mobile bottom tab bar (Challenges, Leaderboard, Profile).
- Auth pages: Login (form-urlencoded per contract) and Register with client-side validation.
- Auth guards: ProtectedRoute (redirects to /login on 401), PublicOnlyRoute (redirects away if logged in).
- Challenges list: cards with lucide icons, points chip, CO2 chip, cooldown countdown, completion count.
- Challenge detail: full info card + submission flow (file picker, preview, upload mutation, verifying/approved/rejected states, new badge celebration).
- Profile: stats grid (points, rank, approved, CO2), editable display name, badge progress bars with target tracking.
- Leaderboard: editorial list with tabular rank numerals, current-user mint highlight, tie semantics preserved.
- Lazy-loaded routes with Suspense spinner.
- vite build succeeds cleanly (1999 modules at that commit, code-split routes, self-hosted fonts);
  11 Vitest tests then (current total is listed in "Where we are").
- All convenience hooks added to queries.ts: useMe, useLogin, useRegister, useChallenges, useChallengeDetail, useProfile, useSubmissions, useLeaderboard, useMeta.

## Frontend milestone 3 (complete)

- Design polish per [frontend/design.md](frontend/design.md): 3.5% paper-grain overlay, shaped
  skeleton loaders (challenge card, leaderboard row, profile), hand-drawn botanical sprout in
  empty states, page rise-in motion, card hover lift, badge-unlock scale, points reveal.
- Accessibility: global 2px `moss` focus ring with 2px offset, `prefers-reduced-motion` support
  (transforms/count-ups dropped, fades kept), `aria-hidden` on decorative skeletons, `aria-live`
  verdict regions, `role=alert` errors, 44px minimum touch targets.
- Service worker registered in production builds (app-shell only; `/api/*` never cached).
- Verified at this milestone: `vitest` green (11 tests) and `vite build` succeeds.
  (The type gate used then — bare `tsc --noEmit` — turned out to check nothing; milestone 4b
  replaced it with `tsc -b` and fixed what it found.)

## Frontend milestone 4 (complete) — contract tests + live e2e

- Auth guard tests: `ProtectedRoute` renders children when authenticated, redirects to `/login`
  when not; `PublicOnlyRoute` the inverse (4 tests).
- Submission flow tests: multipart `FormData` to the exact contract path with CSRF header and no
  Content-Type, returned profile applied instead of optimistic points (contract §7), logout clears
  all TanStack Query caches (contract §8) (3 tests).
- Live end-to-end through the Vite dev proxy (`http://127.0.0.1:5173`):
  - register 201 + cookies → `/auth/me` 200 → `/challenges` 200 → `/profile` 200;
  - `PATCH /auth/me` without CSRF **403** (detail mentions CSRF — the client retries once) →
    with token **200**; logout without/with CSRF **403**/**204**; post-logout `/auth/me` **401**;
  - multipart photo upload → Gemini live → **201 in 2.6 s**, `status: rejected`,
    `confidence: 1.0`, concrete student-facing reason, `points_awarded: 0`, profile returned
    with `submissions_rejected: 1`;
  - one transient Google `500 INTERNAL` mapped by backend to contract `502` (no points, safe
    retry) — retry reused the same errored row as documented.

## Frontend milestone 4b (complete) — reload-loop bugfix + audit

- **Bug fix (`4ebc7ca`):** the API client used `window.location.href = "/login"` on every 401.
  On the `/login` page itself that is a full-document reload on every mount — an infinite reload
  loop that froze the browser. The fetch layer now never navigates: 401 notifies an injectable
  handler (`setUnauthorizedHandler`), and the new `src/components/AuthEvents.tsx` routes to
  `/login` through React Router with a same-path guard, so a 401 while already on an auth page
  is a no-op. Contract §2.4 is still satisfied (auth state cleared, app routes to login).
  Regression tests added (401 notifies handler; non-401 does not; safe when handler removed).
  `window.location.reload()` survives only for contract §2.5 (repeated CSRF failure on
  user-initiated mutations — it never fires on page load).
- **Type-gate correction:** bare `tsc --noEmit` was vacuous — the root `tsconfig.json` is a
  references-only stub (`{"files": []}`), so it checked nothing. The real gate is `tsc -b`.
  Running it surfaced 5 real errors that had passed the vacuous gate, including
  `Layout.tsx` using `isActive` outside its scope (a ReferenceError crash on the mobile bottom
  nav) — all fixed. **Always use `bunx tsc -b`.**
- Follow-on audits ran against this tree; their findings are recorded as milestone 4c below.

## Frontend milestone 4c (complete) — audit-fix batch

Two subagent audits (adversarial code review + test/build verification, both against the contract
and design spec) found 1 high bug still live plus ~15 medium/low issues. All integrated:

**Critical fixed first:** SPA login always returned 422 — `api()` clobbered the caller's explicit
`application/x-www-form-urlencoded` header with `application/json`, so FastAPI's form parser saw
an empty body (proved in-process with the backend venv: wrong header → 422, right header → 200).
Fixed by only defaulting to JSON when the caller set no Content-Type; regression tests lock the
login wire format. (The earlier live e2e used curl and missed this — it validates the backend,
not the SPA client.)

**Audited findings fixed:**
- Ticking cooldown countdowns (`formatCooldown` + `useNow`, 30 s) gated on server `can_submit`;
  "Ready" state when available; never a negative countdown; live countdown + absolute time on the
  detail page; unit-tested in `format.test.ts`.
- `co2_note` now shown next to the figure on challenge detail; list chips labelled "estimated";
  `/meta` environmental + verification disclaimers rendered in the Layout footer (contract §7).
- Header points chip now synced from the submission's returned `profile` (never optimistic).
- Photo-preview blob URL revoked on replace/unmount (previous code revoked the just-created URL,
  breaking previews and leaking the last one); corrected in the effect cleanup.
- Display-name rename errors surfaced (`role=alert`, server detail incl. 409 duplicates);
  logout error surfaced; logout button added to the Profile page (mobile had no logout at all);
  re-entry guards on login/register/submit/delete-name.
- Leaderboard always shows rank numerals (top-3 ranks were icon-only, hiding ties like 1,1,3);
  contrast fixes ("You" label, earned-badge icon).
- Register validation chain fixed (empty field now says "required"; email format checked).
- CSRF cookie parsing hardened against `=` values; `Retry-After` read into `ApiError` and shown
  on 429; `limit`/`offset` no longer dropped when 0; unused `msw` dependency removed.

**Contract features completed:**
- **Submission history** on Profile (design §4) with status chips and contract §6 blob thumbnails
  (cookies included, revoked on unmount) via `GET /submissions`.
- **Offline screen** (contract §8): `OfflineGuard` shows the branded page with a retry; the
  service worker now runtime-caches static assets and serves the shell for offline navigations
  while still never touching `/api/*`. Test-covered (live online/offline events).

**Process corrections:** bare `tsc --noEmit` was proven vacuous (references-only root tsconfig) —
the gate is `tsc -b`, now wired into `package.json` (`test`, `typecheck`, `build` scripts).
Navigation docs completed: eight missing `<folder>.md` files created; stale "not started"/
"planned" language purged from AGENTS.md, README.md, the contract header, and frontend.md.

## Frontend revision r2 (complete) — type swap + wallpaper

Owner feedback: the Fraunces/Figtree pairing "looked too AI generated" and the flat paper
background was monotonous. Both locked decisions were re-chosen (owner picked from options):

- **Type:** Newsreader (editorial display serif) + Manrope (warm geometric sans), self-hosted via
  `@fontsource-variable/newsreader` + `@fontsource-variable/manrope`; `--font-display` /
  `--font-body` tokens swapped, font imports swapped — layout, sizing, and tabular-numeral
  behaviour untouched. design.md §3 typography updated (with revision note).
- **Wallpaper:** WhatsApp-style eco-doodle tile (sprout, recycle arrows, leaf, sun, droplet,
  bicycle, tree, globe, pot) — 300×300 seamless, moss stroke at 0.14 opacity, generated as an
  inline data-URI by `frontend/scripts/gen-doodle.py` (motifs proven inside-tile by
  `bun run scripts/check-doodle.ts` — committed, reproducible: embeds-generator sync +
  pixel-coverage, all regions identical). `body` paints it everywhere; the six former `bg-paper` full-screen
  surfaces (Layout, auth, offline, loaders) now use a `bg-field` utility so no flat colour
  covers it. Cards still sit on `bg-surface`, as chat bubbles do over chat wallpaper.
- design.md §3 gained a "Wallpaper (eco-doodle)" spec; scripts.md/styles.md/frontend.md updated.
- Gates re-run: `tsc -b` 0, vitest **68/68**, oxlint 0/0, `vite build` green, dist contains the
  doodle var + `bg-field` utility + both new font faces (8 woff2); dev server serves them 200.
- **17 new regression tests** (agent-written, adversarially mutation-checked):
  `theme.test.ts` (font tokens, no stale families, well-formed single-prefix `--field-doodle`,
  body/utility wiring, decoded SVG structure + motif-in-tile geometry, exact generator↔CSS sync,
  no `bg-paper` contexts, every full-page wrapper on `bg-field`) and `fonts.test.ts`
  (imports + package manifest). Discrimination proven: reintroducing the doubled-prefix defect
  fails 2 tests; reintroducing a stale font package fails 1 — both restored byte-identically
  afterwards.
- A docs agent's independent re-audit caught a doubled `--field-doodle: --field-doodle:`
  paste defect (wallpaper resolved to `none`) and the leftover old font packages — both fixed
  above and now guarded by the tests + `check-doodle.ts`.

## Not built yet

- Visual review of screens at 360 px + laptop widths (dev server + backend are running) in a browser.
- Password reset / email verification (out of v1 scope).
- Admin/audit portal, reward redemption, photo-metadata anti-spoofing (future enhancements).
- Deployment artifacts (Docker/nginx/systemd) — waiting on the VPS decision.

## Next up

1. Visual review in a browser at 360 px + laptop widths (frontend dev server :5173,
   backend :8000 — both up) and on-device PWA install check.
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
uv run pytest -q             # 97 backend tests
uv run fastapi dev            # http://127.0.0.1:8000/docs

cd frontend
bunx tsc -b                  # the REAL type gate (bare `tsc --noEmit` checks nothing here)
bunx vitest run               # frontend tests
bunx vite build               # production bundle
bunx vite --port 5173         # dev server; /api proxied to http://127.0.0.1:8000
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
live-verification record → cookie auth + frontend contract → design spec → frontend
milestones 1–4 (scaffold, screens, polish, contract tests) → 401 reload-loop fix + audits.

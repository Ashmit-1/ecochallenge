# Frontend ↔ Backend contract

**This file is the frontend's only source of truth about the backend.** If the backend changes,
this file is updated in the same commit. Do not infer behaviour from backend source unless a
question is unanswered here.

- Backend status: **complete and live-verified** (see [../PROJECT_STATE.md](../PROJECT_STATE.md)).
- Frontend status: **not started**.
- API version: `/api/v1`. Dev server: `http://127.0.0.1:8000`. Swagger: `/docs`.
- All payloads are JSON except the image upload (multipart). All timestamps are ISO-8601 UTC
  ending in `Z`.

---

## 1. Running the backend locally

```bash
cd backend
cp .env.example .env        # if .env is missing; add GEMINI_API_KEY
uv sync
uv run alembic upgrade head
uv run seed                 # inserts the 5 challenges
uv run fastapi dev          # http://127.0.0.1:8000
```

- **Real AI:** `VISION_PROVIDER=gemini` + `GEMINI_API_KEY` (model `gemma-4-26b-a4b-it`).
- **Offline/demo:** `VISION_PROVIDER=mock` — every photo is approved unless its bytes contain
  `MOCK-REJECT`. No network, no key.
- Tests: `uv run pytest -q` (97 passing, offline).
- Seed accounts: none. Register through the UI or `POST /auth/register`.

---

## 2. Auth: httpOnly cookie + CSRF

Two credentials exist. **The SPA uses cookies only.**

| Cookie | HttpOnly | Purpose |
|---|---|---|
| `ecochallenge_access` | **yes** | JWT session, 7 days, `SameSite=Lax`, `Secure` in production |
| `ecochallenge_csrf` | no (readable) | Echoed in the `X-CSRF-Token` header |

Rules the frontend must implement:

1. Every API request uses `credentials: "include"`.
2. Every `POST` / `PATCH` / `PUT` / `DELETE` also sends
   `X-CSRF-Token: <value of ecochallenge_csrf>`.
3. **Never store `access_token`** from the login/register response. It exists only for Swagger and
   non-browser clients. Keep `user` in memory/cache; on reload, call `GET /auth/me`.
4. On `401`, clear local auth state and route to `/login`.
5. A `403` whose detail mentions CSRF means the header was missing/stale: re-read the cookie and
   retry **once**; if it fails again, reload the app.

```ts
// lib/api.ts — the one place that talks to the backend
const BASE = "/api/v1"; // Vite proxy in dev, same origin in production

function csrfToken(): string {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith("ecochallenge_csrf="));
  return match ? decodeURIComponent(match.split("=")[1]) : "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (method !== "GET" && method !== "HEAD") headers.set("X-CSRF-Token", csrfToken());

  const response = await fetch(`${BASE}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  if (!response.ok) throw await ApiError.fromResponse(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}
```

**Dev proxy (recommended).** In `vite.config.ts`, proxy `/api` to `http://127.0.0.1:8000` so the
browser sees one origin and cookies are first-party:

```ts
server: { proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } } }
```

CORS is already configured for `http://localhost:5173` and `http://127.0.0.1:5173` with
credentials enabled, so direct cross-origin calls also work.

### Auth endpoints

| Method | Path | Body | Success |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, display_name}` | `201` + cookies |
| POST | `/auth/login` | form-urlencoded `username`(=email), `password` | `200` + cookies |
| POST | `/auth/logout` | — | `204`, cookies cleared |
| GET | `/auth/me` | — | `200 User` |
| PATCH | `/auth/me` | `{display_name?}` | `200 User` |

`POST /auth/login` uses `application/x-www-form-urlencoded` (OAuth2 form), **not** JSON:

```ts
body: new URLSearchParams({ username: email, password })
```

Register/login response body (token ignored by the SPA):

```json
{ "access_token": "…", "token_type": "bearer", "expires_in": 604800, "user": { "…": "User" } }
```

Errors: `401` bad credentials (same message whether email exists), `403` disabled account,
`409` duplicate email or display name, `422` validation.

---

## 3. Data types (authoritative)

```ts
export type Category = "transport" | "waste" | "nature" | "reuse" | "community";
export type SubmissionStatus = "approved" | "rejected" | "error" | "pending";

export interface User {
  id: number;
  email: string;
  display_name: string;
  points_total: number;
  created_at: string; // ISO-8601 Z
}

export interface ChallengeSummary {
  id: number;
  slug: string;
  title: string;
  tagline: string;
  points: number;
  co2_saved_grams: number;
  co2_note: string;           // the assumption behind the estimate — show it
  category: Category;
  icon: string;               // lucide icon name
  cooldown_hours: number;
  times_completed: number;    // this student's approvals
  can_submit: boolean;        // server-computed; trust it
  cooldown_ends_at: string | null;
}

export interface ChallengeDetail extends ChallengeSummary {
  description: string;
  instructions: string;       // numbered plain text, newline separated
  evidence_requirements: string;
}

export interface Badge {
  key: string;
  name: string;
  description: string;
  icon: string;               // lucide icon name
  earned: boolean;
  current: number;            // capped at target
  target: number;
}

export interface Profile {
  display_name: string;
  email: string;
  points_total: number;
  submissions_total: number;
  submissions_approved: number;
  submissions_rejected: number;
  challenges_completed: number; // distinct challenges approved
  co2_saved_grams: number;
  rank: number;                 // 1-based; ties share a rank
  total_participants: number;
  badges: Badge[];
  member_since: string;
}

export interface Submission {
  id: number;
  challenge: { id: number; slug: string; title: string; points: number; icon: string };
  status: SubmissionStatus;
  points_awarded: number;
  co2_saved_grams: number;
  verification: {
    approved: boolean | null;
    confidence: number | null;  // 0–1
    reason: string | null;      // student-facing explanation
    model: string | null;
  };
  image_url: string;            // relative: /api/v1/submissions/{id}/image
  created_at: string;
  verified_at: string | null;
}

export interface SubmissionResult {
  submission: Submission;
  profile: Profile;             // already updated — no refetch needed
  new_badges: Badge[];          // show a celebratory toast if non-empty
}

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  display_name: string;
  points_total: number;
  challenges_completed: number;
  is_current_user: boolean;
}

export interface Leaderboard {
  entries: LeaderboardEntry[];
  total_participants: number;
  current_user_rank: number;
}

export interface Meta {
  name: string;
  version: string;
  verification_provider: string;   // "gemini" | "mock"
  verification_disclaimer: string;
  environmental_disclaimer: string;
  api_docs: string;
}
```

**Icon mapping** (lucide-react): challenges use `bike`, `recycle`, `sprout`, `repeat`,
`sparkles`; badges use `sprout`, `footprints`, `award`, `trophy`, `cloud-off`, `compass`.

---

## 4. Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | — | `{status, database, version}` |
| GET | `/meta` | — | app name, active AI provider, disclaimers |
| POST | `/auth/register` | — | see above |
| POST | `/auth/login` | — | see above |
| POST | `/auth/logout` | cookie | 204 |
| GET | `/auth/me` | cookie | `User` |
| PATCH | `/auth/me` | cookie | `{display_name}` → `User` |
| GET | `/challenges` | optional | `ChallengeSummary[]`, active only, sorted |
| GET | `/challenges/{slug}` | optional | `ChallengeDetail`; 404 if unknown/inactive |
| POST | `/challenges/{slug}/submissions` | cookie | multipart `image` → `SubmissionResult` |
| GET | `/submissions?limit=&offset=` | cookie | `Submission[]`, newest first (limit 1–100, default 20) |
| GET | `/submissions/{id}` | cookie | `Submission`; 404 if not yours |
| GET | `/submissions/{id}/image` | cookie | image bytes; 404 if not yours |
| GET | `/profile` | cookie | `Profile` |
| GET | `/leaderboard?limit=&offset=` | cookie | `Leaderboard` (limit 1–100, default 50) |

`/challenges` also works while logged out; personal fields then default to `times_completed: 0`,
`can_submit: true`.

---

## 5. Uploading evidence

`POST /challenges/{slug}/submissions`, `multipart/form-data`, field name **`image`**:

```ts
const form = new FormData();
form.append("image", file); // File from <input type="file" accept="image/*">
const result = await api<SubmissionResult>(`/challenges/${slug}/submissions`, {
  method: "POST",
  body: form,
});
```

Constraints (enforced server-side):

- JPEG, PNG, or WebP; the bytes are **fully decoded**, so a renamed file fails.
- At least **200×200 px**, at most **6 MB** and 40 MP.
- Verification is **synchronous**: expect 2–6 seconds with real AI. Show a pending state and
  disable double-submit.
- Results: `201` with `submission.status` `approved` or `rejected`. `502` means the AI provider
  failed — **no points were awarded**, and the same photo may be retried later.

| Code | Meaning for the UI |
|---|---|
| `409` | This exact photo was already submitted — ask for a new photo |
| `413` | File too large (or request body too large) |
| `415` | Not a valid/decodable image, or under 200×200 |
| `422` | Missing `image` field or malformed request |
| `429` | Cooldown active; read `Retry-After` and `detail` (contains the unlock time) |
| `502` | Verification unavailable; nothing awarded; retry is safe |

---

## 6. Displaying a private photo

`image_url` requires the session cookie, so a plain `<img src>` works **only if** the cookie is
sent — `<img>` does send cookies for same-origin URLs, but to be sure and to support revoking:

```ts
async function loadEvidence(imageUrl: string): Promise<string> {
  const response = await fetch(imageUrl, { credentials: "include" });
  if (!response.ok) throw new Error("Could not load photo");
  return URL.createObjectURL(await response.blob()); // revoke on unmount
}
```

Never store or display `image_url` publicly; it is owner-only and returns `404` to anyone else.

---

## 7. Rules the UI must reflect

- **Points** are awarded only after `status === "approved"`. Never optimistically add them; use the
  `profile` returned by the submission.
- **Cooldowns** are server-computed. Use `can_submit` and `cooldown_ends_at`; do not recalculate
  from `times_completed`. A rejected attempt does **not** lock the challenge.
- **Ties** share a rank (`RANK()` semantics: 1, 1, 3). Do not re-sort by name to "fix" it.
- **CO₂** is an estimate. Always show `co2_note` (or the `/meta` environmental disclaimer) next to
  any figure, and label it "estimated".
- **AI verification is fallible.** Use the `/meta` disclaimers: approval means the photo looked
  consistent, not that the activity provably happened.
- **Badges** are derived; show progress from `current` / `target`. `new_badges` is only the ones
  unlocked by that submission.
- The **leaderboard** includes active students with 0 points; `current_user_rank` is authoritative.

---

## 8. PWA requirements

- Installable: manifest, icons (192/512, maskable), `display: standalone`, theme color.
- Service worker caches the **app shell** and static assets only. **Never cache `/api/*`** —
  responses are per-user and must not leak between sessions or show stale points.
- Offline: show a branded offline screen with a retry button. No offline submissions, no queued
  mutations, no cached leaderboard.
- Cookie auth works in standalone mode; do not add a second token store.
- Logout must clear TanStack Query caches (`queryClient.clear()`).

---

## 9. Deliberately not available

Do not design UI around these; they return `404`/`405` or do not exist:

- Password reset, email verification, changing email/password.
- Deleting an account, uploading an avatar.
- Admin/audit views, reward redemption, campus-wide analytics.
- Challenge creation/editing.
- Notifications, comments, friends, photo galleries beyond your own submission history.

---

## 10. Changing this contract

The backend is frozen except for defects and the agreed frontend work. Any backend change that
affects a type, status code, or rule above must update this file in the same commit. When in doubt,
run the backend and check `/openapi.json`; this document, not the OpenAPI schema, is the product
contract.

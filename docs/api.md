# API reference

Base path: `/api/v1`. Interactive docs: `http://127.0.0.1:8000/docs`.

Auth: `Authorization: Bearer <jwt>` on everything except `health`, `meta`, `auth/register`,
and `auth/login`. Errors are `{"detail": "..."}`.

## Meta

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | — | `{status, database}`; pings SQLite |
| GET | `/meta` | — | App name, version, verification provider, disclaimer |

## Auth

| Method | Path | Auth | Body | Returns |
|---|---|---|---|---|
| POST | `/auth/register` | — | `{email, password, display_name}` | `201` user + token |
| POST | `/auth/login` | — | form: `username`(=email), `password` | `{access_token, token_type, user}` |
| GET | `/auth/me` | bearer | — | current user |
| PATCH | `/auth/me` | bearer | `{display_name?}` | updated user |

Login is an OAuth2 password form so Swagger's **Authorize** button works. Tokens expire after
7 days; there is no refresh token (see [decisions.md](decisions.md)).

## Challenges

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/challenges` | optional | Active challenges + the caller's state (`times_completed`, `can_submit`, `cooldown_ends_at`) |
| GET | `/challenges/{slug}` | optional | Full detail; `404` if unknown or inactive |

## Submissions

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/challenges/{slug}/submissions` | bearer | multipart field `image`. Runs verification synchronously. |
| GET | `/submissions?limit=&offset=` | bearer | Caller's own history, newest first |
| GET | `/submissions/{id}` | bearer | Own submission, `404` otherwise |
| GET | `/submissions/{id}/image` | bearer | Own image bytes; `404` otherwise |

### Submission response

```json
{
  "submission": {
    "id": 42,
    "challenge": {"id": 1, "slug": "bike-to-campus", "title": "Bike to Campus", "points": 50},
    "status": "approved",
    "points_awarded": 50,
    "co2_saved_grams": 1000,
    "verification": {
      "approved": true,
      "confidence": 0.92,
      "reason": "A bicycle is clearly visible…",
      "model": "gemini-2.5-flash"
    },
    "created_at": "2026-10-23T09:12:00Z",
    "verified_at": "2026-10-23T09:12:04Z"
  },
  "profile": { "...": "same shape as GET /profile" },
  "new_badges": [{ "key": "first-step", "name": "First Step" }]
}
```

Statuses: `approved`, `rejected`, `error`, `pending` (reserved for a future async flow).

### Submission errors

| Code | When |
|---|---|
| `404` | unknown/inactive challenge, or submission not owned by caller |
| `409` | identical image already submitted |
| `413` | file over `MAX_UPLOAD_MB` |
| `415` | not a JPEG/PNG/WebP |
| `422` | validation failure, or the challenge's own rules (`detail` explains) |
| `429` | cooldown active; `detail` includes when it ends |
| `502` | vision provider failed; submission recorded as `error`, no points awarded |

## Profile & leaderboard

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/profile` | bearer | Totals, rank, CO₂, badges |
| GET | `/leaderboard?limit=&offset=` | bearer | Ranked active users; caller's row flagged |

### Leaderboard row

```json
{
  "rank": 1,
  "user_id": 7,
  "display_name": "Aarav",
  "points_total": 1120,
  "challenges_completed": 9,
  "is_current_user": false
}
```

Ties share a rank (`RANK()`, not `ROW_NUMBER()`); ordering within a tie is by account age.

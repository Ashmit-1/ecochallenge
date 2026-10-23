# schemas/

Pydantic DTOs — the public contract between the API and the frontend. These are **not** database
models: they are shaped for the screens that consume them.

| File | Shapes |
|---|---|
| [common.py](common.py) | `APIModel` base, `UTCDateTime` (serialises naive-UTC as `...Z`) |
| [auth.py](auth.py) | `RegisterRequest`, `UpdateProfileRequest`, `UserRead`, `TokenResponse` |
| [challenge.py](challenge.py) | `ChallengeSummary` (list), `ChallengeDetail` (+ long copy) |
| [submission.py](submission.py) | `SubmissionRead`, `VerificationRead`, `SubmissionResult` (verdict + profile + new badges) |
| [profile.py](profile.py) | `ProfileRead`, `BadgeRead` |
| [leaderboard.py](leaderboard.py) | `LeaderboardEntry`, `LeaderboardResponse` |
| [system.py](system.py) | `HealthResponse`, `MetaResponse` |

## Conventions

- **`UTCDateTime` for every timestamp.** SQLite returns naive datetimes; this serializer re-attaches
  UTC and emits a `Z` suffix so the browser cannot misinterpret it as local time.
- **Separate list and detail shapes.** `ChallengeSummary` keeps descriptions out of list payloads.
- **Per-caller state lives in the schema** (`times_completed`, `can_submit`, `cooldown_ends_at`),
  filled by `services/challenge_service.py`, so the frontend never has to compute cooldowns.
- **Never expose `image_path` or `image_sha256`.** Files are exposed only through the
  auth-checked `/submissions/{id}/image` route.
- Validation errors surface as FastAPI's standard `422` body.

## Changing the contract

Update the schema, then the service that builds it, then [../api/api.md](../api/api.md) and
[docs/api.md](../../../docs/api.md). The frontend types (when it exists) must be updated in the
same change.

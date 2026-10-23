# services/

All business rules. Routes call these; models store; nothing here knows about HTTP routing.

| File | Responsibility |
|---|---|
| [auth_service.py](auth_service.py) | Register, authenticate, rename; duplicate-name and timing-safe login handling |
| [challenge_service.py](challenge_service.py) | Catalogue reads + per-caller cooldown state (`can_submit`, `cooldown_ends_at`) |
| [submission_service.py](submission_service.py) | The full upload pipeline and submission reads |
| [storage_service.py](storage_service.py) | Image magic-byte validation, save, safe path resolution, delete |
| [stats_service.py](stats_service.py) | Aggregate counts, CO₂ total, categories, rank via window function |
| [badge_service.py](badge_service.py) | Badge definitions and rule evaluation (derived, never stored) |
| [profile_service.py](profile_service.py) | Composes `ProfileRead` from stats + rank + badges |
| [leaderboard_service.py](leaderboard_service.py) | Paginated ranking with `RANK()` and completion counts |

## The submission pipeline

`create_submission()` is explicitly ordered. Do not reorder these steps:

1. **Validate the image** — magic bytes only (JPEG/PNG/WebP), size cap, non-empty.
2. **Cooldown** — query the newest *approved* submission for this user+challenge, measured from
   `verified_at` (approval time). Within `cooldown_hours` → `429` with `Retry-After`. Rejections
   and errors never lock a student out.
3. **Duplicate** — SHA-256 of the bytes. Same photo from another user, or from the same user after
   a *judged* submission → `409`. Same user retrying after an **error** reuses that row.
4. **Persist** — file first, then a `pending` row committed immediately, so an outage never leaves
   an invisible file. Retries claim an errored/abandoned row with a conditional UPDATE.
5. **Verify** — call the provider. Any provider failure becomes `status=error` (no points) and
   `502`; the exception text is logged, never returned or stored.
6. **Apply** — approved only: snapshot `points_awarded` and `co2_saved_grams`, re-check the cooldown
   under SQLite's write lock, atomically increment `users.points_total`, then commit once.
7. **Badges** — compare earned keys before/after; return only newly unlocked ones.

Exactly one transaction awards points. If step 6 fails, the submission stays `pending` and the
points are untouched — recoverable, never half-applied. A pending row older than 10 minutes may be
retried, so a crash or hard timeout does not permanently strand a photo.

## Invariants

- `points_awarded > 0` **only** when `status == "approved"`.
- `co2_saved_grams` on a submission is a snapshot, not a live lookup.
- `get_user_stats()` is the single definition of "completed" used by profile, badges, and leaderboard.
- Rules raise `HTTPException` with a message written for a student, not a stack trace.

## Testing hooks

- `MockVisionProvider(approve=False)` forces a rejection; the bytes `MOCK-REJECT` do the same for
  one request.
- Cooldown and duplicate behaviour are exercised in `tests/test_submissions.py`.
- Service functions take `Session` explicitly, so tests can drive them without HTTP.

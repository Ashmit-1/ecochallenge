# tests/

Pytest suite. Fast, offline, and isolated: every test gets its own SQLite file, its own uploads
folder, and a mock vision provider. Nothing here touches `data/ecochallenge.db` or the network.

```bash
uv run pytest                # everything
uv run pytest -q -k cooldown # one behaviour
uv run pytest tests/test_vision.py -v
```

## Files

| File | Covers |
|---|---|
| [conftest.py](conftest.py) | Fixtures: engine, session, seeded DB, `TestClient`, registered users, submit helper, PNG factory |
| [test_auth.py](test_auth.py) | Register, duplicate email/name (case-insensitive), login, JWT rejection, rename |
| [test_auth_cookies.py](test_auth_cookies.py) | httpOnly session cookie, CSRF header enforcement, logout, bearer exemption |
| [test_challenges.py](test_challenges.py) | Seeded catalogue, points/cooldowns, anonymous vs personal state, inactive hiding |
| [test_submissions.py](test_submissions.py) | Approve, reject, cooldown + expiry, cooldown-bypass regression, concurrent approvals, duplicate photos, invalid/empty/oversized images, provider outage + retry, pagination, private images |
| [test_badges.py](test_badges.py) | Thresholds, progress caps, new-badge reporting, uniqueness of definitions |
| [test_profile.py](test_profile.py) | Zero state, approval aggregates, rejections not scored, rank movement |
| [test_leaderboard.py](test_leaderboard.py) | Ordering, shared ranks for ties, distinct completions, pagination limits |
| [test_vision.py](test_vision.py) | Mock approve/reject, Gemini key enforcement, parsing, error mapping |
| [test_storage.py](test_storage.py) | Magic bytes, real decode rejection, size cap, traversal protection, save/read/delete |
| [test_seed.py](test_seed.py) | Idempotent seeding, deactivated challenges preserved, content refreshed |
| [test_system.py](test_system.py) | Health, meta disclaimers, redirect, OpenAPI paths, settings parsing |

## How isolation works

- `conftest.py` sets `SECRET_KEY`, `ENVIRONMENT=test`, and `VISION_PROVIDER=mock` **before**
  importing the app, so the developer's `.env` never influences a test run.
- `engine` creates a SQLite file in `tmp_path`; `SQLModel.metadata.create_all` builds the schema
  directly (migrations are exercised separately by the real app run).
- `client` overrides `get_session` with a session bound to that engine and overrides
  `get_vision_provider` with `MockVisionProvider()`.
- `isolated_uploads` (autouse) repoints `settings.uploads_dir` at `tmp_path`.
- `db_session` is the escape hatch for arranging state: backdating `verified_at` to test cooldown
  expiry, or deactivating a challenge.
- `png_bytes()` generates a real 320×320 PNG with Pillow. Upload validation fully decodes images,
  so bare magic bytes are no longer enough to pass a test.

## Conventions

- Assert on **observable API behaviour**, not internal calls, wherever possible.
- One behaviour per test, with a name that states the rule ("cooldown blocks a second attempt").
- Use the `submit` fixture rather than hand-building multipart bodies.
- Need a rejection? Pass `png(marker=b"MOCK-REJECT")` — the marker is stored in a PNG text
  chunk, so the file still decodes as a real image.
- Never hit the live Gemini API from a test, even if a key exists.
- New rule → new test in the matching file. A bug fix starts with a failing test.

## Gotchas

- Importing `app` before setting environment variables will bind the real settings; keep the env
  setup at the very top of `conftest.py`.
- `TestClient` raises unhandled server exceptions by default — that is intentional, it surfaces
  bugs instead of turning them into opaque 500s.
- SQLite locking: `db_session` must commit before the client writes in the same test.

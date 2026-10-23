# core/

Cross-cutting primitives with no knowledge of HTTP routes or tables.

| File | Contains |
|---|---|
| [config.py](config.py) | `Settings` (pydantic-settings), `get_settings()`, path/URL normalisation |
| [security.py](security.py) | Argon2 password hashing and HS256 JWT encode/decode |

## config.py

Reads `backend/.env`. Every setting is documented in [../../.env.example](../../.env.example).
Two important behaviours:

- **Relative SQLite URLs are resolved against `backend/`**, so the app finds the same database
  whether it is launched from the repo root or from `backend/`. Use `settings.sqlalchemy_url`,
  never `settings.database_url` directly.
- **`uploads_dir` is resolved** the same way via `settings.uploads_path`.

`get_settings()` is `lru_cache`d. Tests that need different settings should override the FastAPI
dependencies (`get_session`, `get_vision_provider`) rather than mutate the cached object.

## security.py

- Passwords: Argon2 via `pwdlib` — `hash_password()` / `verify_password()`.
- Tokens: `create_access_token(user_id)` returns `(token, expires_in_seconds)`.
  `decode_access_token()` returns the payload or raises `jwt.InvalidTokenError`.
- Payload is `{sub: "<user id>", exp, iat}`; the algorithm is fixed to HS256.

There is deliberately no refresh token and no server-side session store — see
[docs/decisions.md](../../../docs/decisions.md#d3--jwt-access-token-only-no-refresh-token).

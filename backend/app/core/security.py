"""Password hashing and JWT encoding — no FastAPI imports, no database access."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

ALGORITHM = "HS256"

_password_hasher = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(plain_password, hashed_password)
    except Exception:  # malformed hash in DB must not 500 the login route
        return False


def create_access_token(user_id: int, expires_minutes: int | None = None) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)`` for the given user."""
    settings = get_settings()
    minutes = expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, minutes * 60


def decode_access_token(token: str) -> dict:
    """Decode and verify a token. Raises ``jwt.InvalidTokenError`` on any problem."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[ALGORITHM],
        # A signed token without an expiry must never be accepted.
        options={"require": ["exp", "sub"]},
    )

"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User
from app.vision.base import VisionProvider
from app.vision.factory import get_vision_provider

settings = get_settings()

# SQLite stores signed 64-bit integers; larger values raise OverflowError at the driver.
MAX_DB_INT = 9_223_372_036_854_775_807

# tokenUrl is what Swagger's Authorize button posts to.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False
)

SessionDep = Annotated[Session, Depends(get_session)]
VisionDep = Annotated[VisionProvider, Depends(get_vision_provider)]

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials. Please log in again.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _load_user_from_token(token: str, session: Session) -> User:
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError as exc:
        raise _CREDENTIALS_ERROR from exc

    subject = payload.get("sub")
    if not subject:
        raise _CREDENTIALS_ERROR

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise _CREDENTIALS_ERROR from exc

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep
) -> User:
    return _load_user_from_token(token, session)


def get_optional_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)], session: SessionDep
) -> User | None:
    """Anonymous access is allowed, but a *supplied* invalid token is rejected."""
    if not token:
        return None
    return _load_user_from_token(token, session)


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]

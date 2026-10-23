"""Account registration, login, and profile edits."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.auth import RegisterRequest, UpdateProfileRequest

# Verified against even when the email does not exist, so response time does not reveal
# whether an account is registered.
_DUMMY_HASH = hash_password("ecochallenge-dummy-password-for-timing")


def register_user(session: Session, payload: RegisterRequest) -> User:
    email = str(payload.email).strip().lower()
    display_name = payload.display_name.strip()

    if session.exec(select(User).where(func.lower(User.email) == email)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Try logging in instead.",
        )
    if session.exec(
        select(User).where(func.lower(User.display_name) == display_name.lower())
    ).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That display name is already taken. Try another.",
        )

    user = User(
        email=email,
        display_name=display_name,
        hashed_password=hash_password(payload.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        # Lost a race against a concurrent signup with the same email/name.
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or display name already exists.",
        ) from exc
    session.refresh(user)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User:
    user = session.exec(select(User).where(func.lower(User.email) == email.strip().lower())).first()
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled.",
        )
    return user


def update_display_name(session: Session, user: User, payload: UpdateProfileRequest) -> User:
    new_name = payload.display_name
    if new_name is None or new_name == user.display_name:
        return user

    clash = session.exec(
        select(User).where(
            func.lower(User.display_name) == new_name.lower(),
            User.id != user.id,
        )
    ).first()
    if clash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That display name is already taken. Try another.",
        )

    user.display_name = new_name
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That display name is already taken. Try another.",
        ) from exc
    session.refresh(user)
    return user

"""Registration, login, and the current user's account."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import (
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserRead,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user.id or 0)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and receive a token",
)
def register(payload: RegisterRequest, session: SessionDep) -> TokenResponse:
    return _token_response(auth_service.register_user(session, payload))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email and password (OAuth2 form)",
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> TokenResponse:
    # `username` carries the email so Swagger's Authorize button works unchanged.
    user = auth_service.authenticate_user(session, form.username, form.password)
    return _token_response(user)


@router.get("/me", response_model=UserRead, summary="Current account")
def read_me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserRead, summary="Change display name")
def update_me(
    payload: UpdateProfileRequest, user: CurrentUser, session: SessionDep
) -> User:
    return auth_service.update_display_name(session, user, payload)

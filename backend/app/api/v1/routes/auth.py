"""Registration, login, logout, and the current user's account.

Browsers authenticate with an httpOnly session cookie plus a double-submit CSRF cookie. The JSON
`access_token` is kept for Swagger and non-browser API clients; the SPA must not persist it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.security import create_access_token, create_csrf_token
from app.models import User
from app.schemas.auth import (
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserRead,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _start_session(response: Response, user: User) -> TokenResponse:
    """Set the session + CSRF cookies and return the API-client token response."""
    settings = get_settings()
    token, expires_in = create_access_token(user.id or 0)
    cookie_options = {
        "max_age": expires_in,
        "secure": settings.use_secure_cookies,
        "samesite": settings.cookie_samesite,
        "path": "/",
        "domain": settings.cookie_domain,
    }
    response.set_cookie(
        settings.access_cookie_name, token, httponly=True, **cookie_options
    )
    # Readable by JavaScript on purpose: the SPA echoes it in the X-CSRF-Token header.
    response.set_cookie(
        settings.csrf_cookie_name, create_csrf_token(), httponly=False, **cookie_options
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account, start a cookie session, and receive a token",
)
def register(
    payload: RegisterRequest, response: Response, session: SessionDep
) -> TokenResponse:
    return _start_session(response, auth_service.register_user(session, payload))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in (cookie session + token for API clients)",
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    session: SessionDep,
) -> TokenResponse:
    # `username` carries the email so Swagger's Authorize button works unchanged.
    user = auth_service.authenticate_user(session, form.username, form.password)
    return _start_session(response, user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the session cookies",
)
def logout(response: Response) -> None:
    settings = get_settings()
    for name in (settings.access_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(name, path="/", domain=settings.cookie_domain)


@router.get("/me", response_model=UserRead, summary="Current account")
def read_me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserRead, summary="Change display name")
def update_me(
    payload: UpdateProfileRequest, user: CurrentUser, session: SessionDep
) -> User:
    return auth_service.update_display_name(session, user, payload)

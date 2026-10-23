"""The current student's progress profile."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.profile import ProfileRead
from app.services.profile_service import build_profile

router = APIRouter(tags=["profile"])


@router.get(
    "/profile",
    response_model=ProfileRead,
    summary="Points, impact, rank, and badges for the current student",
)
def read_profile(user: CurrentUser, session: SessionDep) -> ProfileRead:
    return build_profile(session, user)

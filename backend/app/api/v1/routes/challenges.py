"""Challenge catalogue endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import OptionalUser, SessionDep
from app.schemas.challenge import ChallengeDetail, ChallengeSummary
from app.services import challenge_service

router = APIRouter(prefix="/challenges", tags=["challenges"])


@router.get(
    "",
    response_model=list[ChallengeSummary],
    summary="List active challenges with your cooldown state",
)
def list_challenges(user: OptionalUser, session: SessionDep) -> list[ChallengeSummary]:
    return challenge_service.list_challenges(session, user)


@router.get(
    "/{slug}",
    response_model=ChallengeDetail,
    summary="Challenge detail, instructions, and evidence requirements",
)
def get_challenge(slug: str, user: OptionalUser, session: SessionDep) -> ChallengeDetail:
    return challenge_service.get_challenge_detail(session, slug, user)

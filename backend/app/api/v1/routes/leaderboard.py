"""Campus leaderboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import MAX_DB_INT, CurrentUser, SessionDep
from app.schemas.leaderboard import LeaderboardResponse
from app.services.leaderboard_service import get_leaderboard

router = APIRouter(tags=["leaderboard"])


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    summary="Ranked students by points, with your own position",
)
def read_leaderboard(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=MAX_DB_INT)] = 0,
) -> LeaderboardResponse:
    return get_leaderboard(session, user, limit=limit, offset=offset)

"""Pydantic DTOs — the public wire contract. Database models are never returned directly."""

from app.schemas.auth import (
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserRead,
)
from app.schemas.challenge import ChallengeDetail, ChallengeSummary
from app.schemas.common import APIModel, UTCDateTime
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse
from app.schemas.profile import BadgeRead, ProfileRead
from app.schemas.submission import (
    ChallengeRef,
    SubmissionRead,
    SubmissionResult,
    VerificationRead,
)
from app.schemas.system import HealthResponse, MetaResponse

__all__ = [
    "APIModel",
    "BadgeRead",
    "ChallengeDetail",
    "ChallengeRef",
    "ChallengeSummary",
    "HealthResponse",
    "LeaderboardEntry",
    "LeaderboardResponse",
    "MetaResponse",
    "ProfileRead",
    "RegisterRequest",
    "SubmissionRead",
    "SubmissionResult",
    "TokenResponse",
    "UTCDateTime",
    "UpdateProfileRequest",
    "UserRead",
    "VerificationRead",
]

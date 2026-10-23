"""Submission and verification contracts."""

from __future__ import annotations

from app.schemas.common import APIModel, UTCDateTime
from app.schemas.profile import BadgeRead, ProfileRead


class ChallengeRef(APIModel):
    id: int
    slug: str
    title: str
    points: int
    icon: str


class VerificationRead(APIModel):
    approved: bool | None = None
    confidence: float | None = None
    reason: str | None = None
    model: str | None = None


class SubmissionRead(APIModel):
    id: int
    challenge: ChallengeRef
    status: str
    points_awarded: int
    co2_saved_grams: int
    verification: VerificationRead
    image_url: str
    created_at: UTCDateTime
    verified_at: UTCDateTime | None


class SubmissionResult(APIModel):
    """Everything the 'your submission' screen needs in one round trip."""

    submission: SubmissionRead
    profile: ProfileRead
    new_badges: list[BadgeRead] = []

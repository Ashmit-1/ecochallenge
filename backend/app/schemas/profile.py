"""Profile and badge contracts."""

from __future__ import annotations

from pydantic import EmailStr

from app.schemas.common import APIModel, UTCDateTime


class BadgeRead(APIModel):
    key: str
    name: str
    description: str
    icon: str
    earned: bool
    current: int
    target: int


class ProfileRead(APIModel):
    display_name: str
    email: EmailStr
    points_total: int
    submissions_total: int
    submissions_approved: int
    submissions_rejected: int
    challenges_completed: int
    co2_saved_grams: int
    rank: int
    total_participants: int
    badges: list[BadgeRead]
    member_since: UTCDateTime

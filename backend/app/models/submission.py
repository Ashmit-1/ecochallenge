"""Photo-evidence submissions and their verification outcome."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import utcnow
from app.models.challenge import Challenge


class SubmissionStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    error = "error"


class Submission(SQLModel, table=True):
    __tablename__ = "submissions"
    __table_args__ = (
        # Supports the cooldown lookup: newest approved row for (user, challenge).
        Index("ix_submissions_user_challenge_created", "user_id", "challenge_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    challenge_id: int = Field(foreign_key="challenges.id", index=True)

    image_path: str = Field(max_length=255)
    image_sha256: str = Field(unique=True, index=True, max_length=64)
    image_mime: str = Field(max_length=40)

    status: str = Field(default=SubmissionStatus.pending.value, max_length=10, index=True)

    ai_approved: bool | None = Field(default=None)
    ai_confidence: float | None = Field(default=None, ge=0, le=1)
    ai_reason: str | None = Field(default=None)
    model_used: str | None = Field(default=None, max_length=60)

    # Snapshotted at approval so later edits to the challenge cannot rewrite history.
    points_awarded: int = Field(default=0, ge=0)
    co2_saved_grams: int = Field(default=0, ge=0)

    created_at: datetime = Field(default_factory=utcnow, index=True)
    verified_at: datetime | None = Field(default=None)

    challenge: Challenge | None = Relationship()

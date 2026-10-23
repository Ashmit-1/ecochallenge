"""Student accounts."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    display_name: str = Field(unique=True, index=True, min_length=2, max_length=30)
    hashed_password: str = Field(max_length=255)

    # Denormalised running total, updated in the same transaction as an approval.
    # Rebuildable with: SELECT SUM(points_awarded) FROM submissions
    #                  WHERE user_id = ? AND status = 'approved'.
    points_total: int = Field(default=0, ge=0)

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

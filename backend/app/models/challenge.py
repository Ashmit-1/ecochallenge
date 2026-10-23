"""Eco challenges — the catalogue students pick from."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class ChallengeCategory(StrEnum):
    transport = "transport"
    waste = "waste"
    nature = "nature"
    reuse = "reuse"
    community = "community"


class Challenge(SQLModel, table=True):
    __tablename__ = "challenges"

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True, max_length=60)
    title: str = Field(max_length=80)
    tagline: str = Field(max_length=160)
    description: str
    instructions: str
    evidence_requirements: str

    points: int = Field(gt=0, le=1000)
    co2_saved_grams: int = Field(default=0, ge=0)
    co2_note: str = Field(default="", max_length=240)

    category: str = Field(default=ChallengeCategory.community.value, max_length=20, index=True)
    icon: str = Field(default="leaf", max_length=40)

    # Minimum hours between two *approved* submissions of this challenge.
    cooldown_hours: int = Field(default=24, ge=1, le=8760)

    is_active: bool = Field(default=True, index=True)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)

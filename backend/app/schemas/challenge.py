"""Challenge catalogue contracts."""

from __future__ import annotations

from app.schemas.common import APIModel, UTCDateTime


class ChallengeSummary(APIModel):
    """List-view shape: enough to choose a challenge, without the long copy."""

    id: int
    slug: str
    title: str
    tagline: str
    points: int
    co2_saved_grams: int
    co2_note: str
    category: str
    icon: str
    cooldown_hours: int

    # Per-caller state (defaults apply to anonymous requests).
    times_completed: int = 0
    can_submit: bool = True
    cooldown_ends_at: UTCDateTime | None = None


class ChallengeDetail(ChallengeSummary):
    description: str
    instructions: str
    evidence_requirements: str

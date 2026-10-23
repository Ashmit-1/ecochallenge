"""Assembles the profile payload from stats, rank, and badge rules."""

from __future__ import annotations

from sqlmodel import Session

from app.models import User
from app.schemas.profile import ProfileRead
from app.services.badge_service import compute_badges
from app.services.stats_service import get_user_rank, get_user_stats


def build_profile(session: Session, user: User) -> ProfileRead:
    stats = get_user_stats(session, user.id)
    rank, total_participants = get_user_rank(session, user)
    return ProfileRead(
        display_name=user.display_name,
        email=user.email,
        points_total=user.points_total,
        submissions_total=stats.submissions_total,
        submissions_approved=stats.submissions_approved,
        submissions_rejected=stats.submissions_rejected,
        challenges_completed=stats.challenges_completed,
        co2_saved_grams=stats.co2_saved_grams,
        rank=rank,
        total_participants=total_participants,
        badges=compute_badges(stats, user.points_total),
        member_since=user.created_at,
    )

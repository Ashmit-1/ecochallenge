"""Challenge catalogue reads, including per-student cooldown state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.models import Challenge, Submission, SubmissionStatus, User
from app.models.base import utcnow
from app.schemas.challenge import ChallengeDetail, ChallengeSummary


@dataclass(frozen=True, slots=True)
class ChallengeState:
    times_completed: int = 0
    last_approved_at: datetime | None = None


def list_challenges(session: Session, user: User | None) -> list[ChallengeSummary]:
    challenges = session.exec(
        select(Challenge)
        .where(Challenge.is_active == True)  # noqa: E712 — SQLAlchemy needs the operator
        .order_by(Challenge.sort_order, Challenge.id)
    ).all()
    if not challenges:
        return []

    states = (
        _states_for(session, user.id, [c.id for c in challenges if c.id is not None])
        if user is not None
        else {}
    )
    return [_to_summary(c, states.get(c.id)) for c in challenges]


def get_challenge_detail(session: Session, slug: str, user: User | None) -> ChallengeDetail:
    challenge = get_active_challenge(session, slug)
    state = (
        _states_for(session, user.id, [challenge.id]).get(challenge.id)
        if user is not None and challenge.id is not None
        else None
    )
    return _to_detail(challenge, state)


def get_active_challenge(session: Session, slug: str) -> Challenge:
    challenge = session.exec(select(Challenge).where(Challenge.slug == slug)).first()
    if challenge is None or not challenge.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That challenge does not exist or is no longer available.",
        )
    return challenge


def cooldown_ends_at(challenge: Challenge, state: ChallengeState | None) -> datetime | None:
    """When the challenge reopens for this student, or ``None`` if it is open now."""
    if state is None or state.last_approved_at is None:
        return None
    ends = state.last_approved_at + timedelta(hours=challenge.cooldown_hours)
    return ends if ends > utcnow() else None


def _states_for(
    session: Session, user_id: int, challenge_ids: list[int]
) -> dict[int, ChallengeState]:
    if not challenge_ids:
        return {}
    rows = session.exec(
        select(
            Submission.challenge_id,
            func.count(Submission.id),
            func.max(Submission.created_at),
        )
        .where(
            Submission.user_id == user_id,
            Submission.challenge_id.in_(challenge_ids),
            Submission.status == SubmissionStatus.approved.value,
        )
        .group_by(Submission.challenge_id)
    ).all()
    return {
        int(challenge_id): ChallengeState(
            times_completed=int(count), last_approved_at=last_approved
        )
        for challenge_id, count, last_approved in rows
    }


def _base_fields(challenge: Challenge, state: ChallengeState | None) -> dict:
    ends = cooldown_ends_at(challenge, state)
    return {
        "id": challenge.id,
        "slug": challenge.slug,
        "title": challenge.title,
        "tagline": challenge.tagline,
        "points": challenge.points,
        "co2_saved_grams": challenge.co2_saved_grams,
        "co2_note": challenge.co2_note,
        "category": challenge.category,
        "icon": challenge.icon,
        "cooldown_hours": challenge.cooldown_hours,
        "times_completed": state.times_completed if state else 0,
        "can_submit": ends is None,
        "cooldown_ends_at": ends,
    }


def _to_summary(challenge: Challenge, state: ChallengeState | None) -> ChallengeSummary:
    return ChallengeSummary(**_base_fields(challenge, state))


def _to_detail(challenge: Challenge, state: ChallengeState | None) -> ChallengeDetail:
    return ChallengeDetail(
        **_base_fields(challenge, state),
        description=challenge.description,
        instructions=challenge.instructions,
        evidence_requirements=challenge.evidence_requirements,
    )

"""The submission pipeline: validate → cooldown → dedupe → store → verify → award.

This is the one flow where several rules must hold together, so it lives in a single function with
an explicit, ordered sequence rather than a chain of hidden callbacks.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, update

from app.core.config import get_settings
from app.models import Challenge, Submission, SubmissionStatus, User
from app.models.base import utcnow
from app.schemas.profile import BadgeRead
from app.schemas.submission import ChallengeRef, SubmissionRead, VerificationRead
from app.services import storage_service
from app.services.badge_service import compute_badges, earned_keys
from app.services.stats_service import get_user_stats
from app.vision.base import VerificationRequest, VisionError, VisionProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SubmissionOutcome:
    submission: Submission
    new_badges: list[BadgeRead]


def create_submission(
    *,
    session: Session,
    user: User,
    challenge: Challenge,
    image_bytes: bytes,
    provider: VisionProvider,
) -> SubmissionOutcome:
    mime = storage_service.validate_image(image_bytes)
    _enforce_cooldown(session, user, challenge)

    digest = hashlib.sha256(image_bytes).hexdigest()
    submission = _resolve_duplicate(
        session=session,
        user=user,
        challenge=challenge,
        image_bytes=image_bytes,
        mime=mime,
        digest=digest,
    )

    try:
        verdict = provider.verify(
            VerificationRequest(
                image_bytes=image_bytes,
                mime_type=mime,
                challenge_title=challenge.title,
                challenge_description=challenge.description,
                evidence_requirements=challenge.evidence_requirements,
            )
        )
    except VisionError as exc:
        # An outage is not a rejection: record the attempt as errored, award nothing, and let the
        # student retry the same photo once the provider recovers.
        logger.warning("Verification unavailable for challenge %s: %s", challenge.slug, exc)
        submission.status = SubmissionStatus.error.value
        submission.ai_approved = None
        submission.ai_reason = f"Verification unavailable: {str(exc)[:300]}"
        submission.verified_at = utcnow()
        session.add(submission)
        session.commit()
        session.refresh(submission)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Photo verification is unavailable right now, so no points were awarded. "
                f"Please try again shortly. ({str(exc)[:180]})"
            ),
        ) from exc

    approved = verdict.approved
    before_earned = earned_keys(
        compute_badges(
            get_user_stats(session, user.id),
            user.points_total,
        )
    )

    submission.status = (
        SubmissionStatus.approved.value if approved else SubmissionStatus.rejected.value
    )
    submission.ai_approved = approved
    submission.ai_confidence = verdict.confidence
    submission.ai_reason = verdict.reason
    submission.model_used = verdict.model
    submission.verified_at = utcnow()

    if approved:
        submission.points_awarded = challenge.points
        submission.co2_saved_grams = challenge.co2_saved_grams
        # Atomic increment: concurrent approvals cannot overwrite each other's points.
        session.exec(
            update(User)
            .where(User.id == user.id)
            .values(points_total=User.points_total + challenge.points)
        )

    session.add(submission)
    session.commit()
    session.refresh(submission)
    session.refresh(user)

    new_badges: list[BadgeRead] = []
    if approved:
        after_badges = compute_badges(get_user_stats(session, user.id), user.points_total)
        new_badges = [b for b in after_badges if b.earned and b.key not in before_earned]

    return SubmissionOutcome(submission=submission, new_badges=new_badges)


def list_submissions(
    session: Session, user: User, *, limit: int, offset: int
) -> list[Submission]:
    return list(
        session.exec(
            select(Submission)
            .where(Submission.user_id == user.id)
            .order_by(Submission.created_at.desc(), Submission.id.desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(Submission.challenge))
        ).all()
    )


def get_submission(session: Session, user: User, submission_id: int) -> Submission:
    submission = session.exec(
        select(Submission)
        .where(Submission.id == submission_id, Submission.user_id == user.id)
        .options(selectinload(Submission.challenge))
    ).first()
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )
    return submission


def to_submission_read(submission: Submission) -> SubmissionRead:
    challenge = submission.challenge
    if challenge is None:  # pragma: no cover - guarded by eager loading everywhere
        raise RuntimeError("submission.challenge must be loaded before serialising")
    return SubmissionRead(
        id=submission.id or 0,
        challenge=ChallengeRef(
            id=challenge.id or 0,
            slug=challenge.slug,
            title=challenge.title,
            points=challenge.points,
            icon=challenge.icon,
        ),
        status=submission.status,
        points_awarded=submission.points_awarded,
        co2_saved_grams=submission.co2_saved_grams,
        verification=VerificationRead(
            approved=submission.ai_approved,
            confidence=submission.ai_confidence,
            reason=submission.ai_reason,
            model=submission.model_used,
        ),
        image_url=f"{get_settings().api_v1_prefix}/submissions/{submission.id}/image",
        created_at=submission.created_at,
        verified_at=submission.verified_at,
    )


# --------------------------------------------------------------------------- internals


def _enforce_cooldown(session: Session, user: User, challenge: Challenge) -> None:
    last_approved = session.exec(
        select(Submission.created_at)
        .where(
            Submission.user_id == user.id,
            Submission.challenge_id == challenge.id,
            Submission.status == SubmissionStatus.approved.value,
        )
        .order_by(Submission.created_at.desc())
        .limit(1)
    ).first()
    if last_approved is None:
        return

    ends = last_approved + timedelta(hours=challenge.cooldown_hours)
    now = utcnow()
    if ends <= now:
        return

    retry_after = max(1, int((ends - now).total_seconds()))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            f"You already completed this challenge recently. "
            f"You can submit it again after {_format_utc(ends)}."
        ),
        headers={"Retry-After": str(retry_after)},
    )


def _resolve_duplicate(
    *,
    session: Session,
    user: User,
    challenge: Challenge,
    image_bytes: bytes,
    mime: str,
    digest: str,
) -> Submission:
    """Return a fresh or reusable submission row, rejecting re-used photos.

    A retry of an *errored* attempt by the same student reuses the row it left behind, so a
    provider outage does not permanently burn that photo.
    """
    existing = session.exec(
        select(Submission).where(Submission.image_sha256 == digest)
    ).first()

    if existing is not None:
        retryable = (
            existing.user_id == user.id
            and existing.status == SubmissionStatus.error.value
        )
        if not retryable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This exact photo has already been submitted. "
                    "Upload a new photo of this activity."
                ),
            )
        existing.challenge_id = challenge.id
        existing.challenge = challenge
        existing.status = SubmissionStatus.pending.value
        existing.ai_approved = None
        existing.ai_confidence = None
        existing.ai_reason = None
        existing.model_used = None
        existing.points_awarded = 0
        existing.co2_saved_grams = 0
        existing.verified_at = None
        existing.image_mime = mime
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    relative_path = storage_service.save_image(image_bytes, mime, user.id)
    submission = Submission(
        user_id=user.id,
        challenge_id=challenge.id,
        image_path=relative_path,
        image_sha256=digest,
        image_mime=mime,
        status=SubmissionStatus.pending.value,
    )
    submission.challenge = challenge
    session.add(submission)
    try:
        session.commit()
    except IntegrityError as exc:
        # Concurrent upload of the same bytes won the unique constraint.
        session.rollback()
        storage_service.delete_image(relative_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This exact photo has already been submitted. "
                "Upload a new photo of this activity."
            ),
        ) from exc
    session.refresh(submission)
    return submission


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

"""The submission pipeline: validate → cooldown → dedupe → store → verify → award.

This is the one flow where several rules must hold together, so it lives in a single function with
an explicit, ordered sequence rather than a chain of hidden callbacks.

Two invariants are load-bearing:

1. **Cooldown is measured from approval time** (``verified_at``), never upload time. An errored
   attempt can be retried days later; using ``created_at`` would make that retry look like an old
   approval and let the student submit again immediately.
2. **The award runs under SQLite's write lock.** The conditional ``UPDATE`` that claims the row is
   the first statement of the award transaction, and the cooldown is re-checked *after* it. SQLite
   serialises writers, so a competing award either committed before us (and is visible to the
   re-check) or is still blocked. Check-then-act outside a write transaction is a bug.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, func, select, update

from app.core.config import get_settings
from app.models import Challenge, Submission, SubmissionStatus, User
from app.models.base import utcnow
from app.schemas.profile import BadgeRead
from app.schemas.submission import ChallengeRef, SubmissionRead, VerificationRead
from app.services import storage_service
from app.services.badge_service import compute_badges, earned_keys
from app.services.stats_service import get_user_stats
from app.vision.base import VerificationRequest, VisionProvider

logger = logging.getLogger(__name__)

APPROVED = SubmissionStatus.approved.value
REJECTED = SubmissionStatus.rejected.value
PENDING = SubmissionStatus.pending.value
ERROR = SubmissionStatus.error.value

# A pending row older than this is assumed abandoned (crash, hard timeout) and may be retried.
STALE_PENDING = timedelta(minutes=10)

VERIFICATION_UNAVAILABLE = (
    "Photo verification is unavailable right now, so no points were awarded. "
    "Please try again shortly."
)
ALREADY_SUBMITTED = (
    "This exact photo has already been submitted. Upload a new photo of this activity."
)


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

    # Snapshot badge state before any award, then close the read transaction: the award below must
    # start directly with a write, so SQLite never has to upgrade a read lock (deadlock/BUSY).
    before_earned = earned_keys(
        compute_badges(get_user_stats(session, user.id), user.points_total)
    )
    session.commit()

    digest = hashlib.sha256(image_bytes).hexdigest()
    submission = _resolve_duplicate(
        session=session,
        user=user,
        challenge=challenge,
        image_bytes=image_bytes,
        mime=mime,
        digest=digest,
    )

    verdict = _verify(
        session=session,
        submission=submission,
        provider=provider,
        challenge=challenge,
        image_bytes=image_bytes,
        mime=mime,
    )

    new_badges = _apply_verdict(
        session=session,
        user=user,
        challenge=challenge,
        submission=submission,
        verdict=verdict,
        before_earned=before_earned,
    )
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


def _approval_time():
    """SQL expression for 'when this was approved', tolerant of legacy rows."""
    return func.coalesce(Submission.verified_at, Submission.created_at)


def _enforce_cooldown(session: Session, user: User, challenge: Challenge) -> None:
    last_approved = session.exec(
        select(_approval_time())
        .where(
            Submission.user_id == user.id,
            Submission.challenge_id == challenge.id,
            Submission.status == APPROVED,
        )
        .order_by(_approval_time().desc())
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
            "You already completed this challenge recently. "
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
    """Return a claimed submission row, rejecting re-used photos.

    A retry of an **errored** attempt (or an abandoned ``pending`` one) by the same student on the
    *same* challenge reuses that row. The claim is a conditional UPDATE, so two concurrent retries
    cannot both win.
    """
    existing = session.exec(
        select(Submission).where(Submission.image_sha256 == digest)
    ).first()

    if existing is not None:
        # A photo belongs to the challenge it was submitted against; retries must not re-target it.
        if existing.user_id != user.id or existing.challenge_id != challenge.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_SUBMITTED)

        retryable = existing.status == ERROR or (
            existing.status == PENDING and existing.created_at < utcnow() - STALE_PENDING
        )
        if not retryable:
            if existing.status == PENDING:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This photo is already being checked. Give it a moment, then retry.",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=ALREADY_SUBMITTED
            )

        previous_status = existing.status
        claimed = session.exec(
            update(Submission)
            .where(
                Submission.id == existing.id,
                Submission.status == previous_status,
            )
            .values(
                status=PENDING,
                ai_approved=None,
                ai_confidence=None,
                ai_reason=None,
                model_used=None,
                points_awarded=0,
                co2_saved_grams=0,
                verified_at=None,
                image_mime=mime,
            )
        )
        if claimed.rowcount != 1:  # another request claimed it first
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This photo is already being checked. Give it a moment, then retry.",
            )
        session.commit()
        session.refresh(existing)
        session.commit()  # close the refresh's read transaction before verification
        return existing

    relative_path = storage_service.save_image(image_bytes, mime, user.id)
    submission = Submission(
        user_id=user.id,
        challenge_id=challenge.id,
        image_path=relative_path,
        image_sha256=digest,
        image_mime=mime,
        status=PENDING,
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
            status_code=status.HTTP_409_CONFLICT, detail=ALREADY_SUBMITTED
        ) from exc
    session.refresh(submission)
    session.commit()  # close the refresh's read transaction before verification
    return submission


def _verify(
    *,
    session: Session,
    submission: Submission,
    provider: VisionProvider,
    challenge: Challenge,
    image_bytes: bytes,
    mime: str,
):
    try:
        return provider.verify(
            VerificationRequest(
                image_bytes=image_bytes,
                mime_type=mime,
                challenge_title=challenge.title,
                challenge_description=challenge.description,
                evidence_requirements=challenge.evidence_requirements,
            )
        )
    except Exception as exc:  # noqa: BLE001 - any provider failure must not award points
        # Details (including SDK messages) go to the server log only; the student and stored
        # history get a stable, non-leaking explanation.
        logger.warning(
            "Verification failed for challenge %s: %s", challenge.slug, exc, exc_info=True
        )
        session.exec(
            update(Submission)
            .where(Submission.id == submission.id)
            .values(
                status=ERROR,
                ai_approved=None,
                ai_confidence=None,
                ai_reason="Verification service unavailable; no points were awarded.",
                model_used=None,
                verified_at=utcnow(),
            )
        )
        session.commit()
        session.refresh(submission)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=VERIFICATION_UNAVAILABLE
        ) from exc


def _apply_verdict(
    *,
    session: Session,
    user: User,
    challenge: Challenge,
    submission: Submission,
    verdict,
    before_earned: set[str],
) -> list[BadgeRead]:
    now = utcnow()
    values: dict = {
        "ai_approved": verdict.approved,
        "ai_confidence": verdict.confidence,
        "ai_reason": verdict.reason,
        "model_used": verdict.model,
        "verified_at": now,
    }
    if verdict.approved:
        values["status"] = APPROVED
        values["points_awarded"] = challenge.points
        values["co2_saved_grams"] = challenge.co2_saved_grams
    else:
        values["status"] = REJECTED

    # First statement of the award transaction: takes the write lock and proves we are the only
    # request allowed to finalise this row.
    claimed = session.exec(
        update(Submission)
        .where(Submission.id == submission.id, Submission.status == PENDING)
        .values(**values)
    )
    if claimed.rowcount != 1:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This submission was already finalised by another request.",
        )

    if verdict.approved:
        # Holding the write lock: any competing approval is either committed (visible below) or
        # still blocked, so this re-check is authoritative.
        last_approved = session.exec(
            select(_approval_time())
            .where(
                Submission.user_id == user.id,
                Submission.challenge_id == challenge.id,
                Submission.status == APPROVED,
                Submission.id != submission.id,
                _approval_time() > now - timedelta(hours=challenge.cooldown_hours),
            )
            .order_by(_approval_time().desc())
            .limit(1)
        ).first()
        if last_approved is not None:
            ends = last_approved + timedelta(hours=challenge.cooldown_hours)
            retry_after = max(1, int((ends - now).total_seconds()))
            session.rollback()
            _discard_submission(session, submission)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Another submission of this challenge was just approved. "
                    f"You can submit it again after {_format_utc(ends)}."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        # Atomic increment: concurrent approvals of different challenges cannot lose points.
        session.exec(
            update(User)
            .where(User.id == user.id)
            .values(points_total=User.points_total + challenge.points)
        )

    session.commit()
    session.refresh(submission)
    session.refresh(user)

    if not verdict.approved:
        return []

    after_badges = compute_badges(get_user_stats(session, user.id), user.points_total)
    return [b for b in after_badges if b.earned and b.key not in before_earned]


def _discard_submission(session: Session, submission: Submission) -> None:
    """Remove a submission that lost a cooldown race; it never awarded points."""
    image_path = submission.image_path
    session.delete(submission)
    session.commit()
    storage_service.delete_image(image_path)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

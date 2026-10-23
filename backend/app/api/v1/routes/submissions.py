"""Photo submissions: upload, history, and private image serving."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Path, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import MAX_DB_INT, CurrentUser, SessionDep, VisionDep
from app.core.config import get_settings
from app.schemas.submission import SubmissionRead, SubmissionResult
from app.services import challenge_service, profile_service, storage_service, submission_service

router = APIRouter(tags=["submissions"])


@router.post(
    "/challenges/{slug}/submissions",
    response_model=SubmissionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload photo evidence and get a verification verdict",
    responses={
        409: {"description": "This exact photo was already submitted"},
        413: {"description": "Photo too large"},
        415: {"description": "Not a JPEG/PNG/WebP photo"},
        429: {"description": "Challenge is on cooldown for this student"},
        502: {"description": "Verification service unavailable — no points awarded"},
    },
)
def submit_evidence(
    slug: str,
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP photo evidence")],
    user: CurrentUser,
    session: SessionDep,
    provider: VisionDep,
) -> SubmissionResult:
    challenge = challenge_service.get_active_challenge(session, slug)
    # Read at most one byte past the limit: enough to detect oversize without loading a huge file.
    image_bytes = image.file.read(get_settings().max_upload_bytes + 1)

    outcome = submission_service.create_submission(
        session=session,
        user=user,
        challenge=challenge,
        image_bytes=image_bytes,
        provider=provider,
    )
    return SubmissionResult(
        submission=submission_service.to_submission_read(outcome.submission),
        profile=profile_service.build_profile(session, user),
        new_badges=outcome.new_badges,
    )


@router.get(
    "/submissions",
    response_model=list[SubmissionRead],
    summary="Your submission history, newest first",
)
def list_my_submissions(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=MAX_DB_INT)] = 0,
) -> list[SubmissionRead]:
    submissions = submission_service.list_submissions(
        session, user, limit=limit, offset=offset
    )
    return [submission_service.to_submission_read(s) for s in submissions]


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionRead,
    summary="One of your submissions",
)
def get_my_submission(
    submission_id: Annotated[int, Path(ge=1, le=MAX_DB_INT)],
    user: CurrentUser,
    session: SessionDep,
) -> SubmissionRead:
    submission = submission_service.get_submission(session, user, submission_id)
    return submission_service.to_submission_read(submission)


@router.get(
    "/submissions/{submission_id}/image",
    response_class=FileResponse,
    summary="Your submitted photo (owner only)",
    responses={404: {"description": "Submission not found or not yours"}},
)
def get_submission_image(
    submission_id: Annotated[int, Path(ge=1, le=MAX_DB_INT)],
    user: CurrentUser,
    session: SessionDep,
) -> FileResponse:
    submission = submission_service.get_submission(session, user, submission_id)
    path = storage_service.resolve_image_path(submission.image_path)
    return FileResponse(
        path,
        media_type=submission.image_mime,
        headers={"Cache-Control": "private, max-age=3600"},
    )

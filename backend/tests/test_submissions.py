"""The submission pipeline: approval, rejection, cooldown, duplicates, failures, and images."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import select

from app.core.config import get_settings
from app.main import app
from app.models import Submission, SubmissionStatus
from app.models.base import utcnow
from app.vision.base import VisionProviderError
from app.vision.factory import get_vision_provider
from app.vision.mock import MockVisionProvider

SUBMIT_PATH = "/api/v1/challenges/{slug}/submissions"


class BrokenProvider:
    name = "broken"

    def verify(self, request):  # noqa: ANN001
        raise VisionProviderError("simulated verification outage")


def test_approved_submission_awards_points_badge_and_impact(client: TestClient, register, submit):
    user = register("Approved User")
    response = submit(user, "bike-to-campus")
    assert response.status_code == 201, response.text

    body = response.json()
    submission = body["submission"]
    assert submission["status"] == "approved"
    assert submission["points_awarded"] == 50
    assert submission["co2_saved_grams"] == 1000
    assert submission["verification"]["approved"] is True
    assert submission["verification"]["model"] == "mock"
    assert submission["verification"]["reason"]
    assert submission["image_url"].endswith("/image")
    assert submission["created_at"].endswith("Z")

    assert body["profile"]["points_total"] == 50
    assert body["profile"]["co2_saved_grams"] == 1000
    assert [b["key"] for b in body["new_badges"]] == ["first-step"]


def test_rejected_submission_awards_nothing_but_stays_in_history(
    client: TestClient, register, submit, png
):
    user = register("Rejected User")
    response = submit(user, "bike-to-campus", image=png(marker=b"MOCK-REJECT"))
    assert response.status_code == 201

    body = response.json()
    assert body["submission"]["status"] == "rejected"
    assert body["submission"]["points_awarded"] == 0
    assert body["submission"]["verification"]["approved"] is False
    assert body["submission"]["verification"]["reason"]
    assert body["profile"]["points_total"] == 0
    assert body["new_badges"] == []

    history = client.get("/api/v1/submissions", headers=user.headers).json()
    assert len(history) == 1
    assert history[0]["status"] == "rejected"


def test_cooldown_blocks_a_second_attempt_on_the_same_challenge(
    client: TestClient, register, submit, png
):
    user = register("Cooldown User")
    assert submit(user, "bike-to-campus").status_code == 201

    second = submit(user, "bike-to-campus", image=png())
    assert second.status_code == 429
    assert "Retry-After" in second.headers
    assert "again after" in second.json()["detail"]

    # A different challenge is unaffected.
    assert submit(user, "recycle-waste-batch", image=png()).status_code == 201


def test_cooldown_expires_after_the_window(
    client: TestClient, register, submit, db_session, png
):
    user = register("Patient User")
    assert submit(user, "bike-to-campus").status_code == 201

    rows = db_session.exec(
        select(Submission).where(Submission.user_id == user.user["id"])
    ).all()
    for row in rows:
        row.created_at = utcnow() - timedelta(hours=25)
        row.verified_at = utcnow() - timedelta(hours=25)
        db_session.add(row)
    db_session.commit()

    retry = submit(user, "bike-to-campus", image=png())
    assert retry.status_code == 201
    assert retry.json()["profile"]["points_total"] == 100  # second approval counted


def test_identical_photo_from_another_user_is_rejected(client: TestClient, register, submit, png):
    first = register("Photo Owner")
    second = register("Photo Copier")
    image = png(payload=b"shared-photo")

    assert submit(first, "bike-to-campus", image=image).status_code == 201
    response = submit(second, "recycle-waste-batch", image=image)
    assert response.status_code == 409
    assert "already been submitted" in response.json()["detail"]


def test_identical_photo_on_another_challenge_is_rejected(
    client: TestClient, register, submit, png
):
    user = register("Repeat Photo")
    image = png(payload=b"same-photo")
    assert submit(user, "bike-to-campus", image=image).status_code == 201
    assert submit(user, "recycle-waste-batch", image=image).status_code == 409


def test_non_image_file_is_415(client: TestClient, register, submit):
    user = register("Bad Upload")
    response = submit(user, image=b"this is plain text, not an image")
    assert response.status_code == 415


def test_empty_file_is_422(client: TestClient, register, submit):
    user = register("Empty Upload")
    assert submit(user, image=b"").status_code == 422


def test_missing_file_is_422(client: TestClient, register):
    user = register("No File")
    response = client.post(
        SUBMIT_PATH.format(slug="bike-to-campus"), headers=user.headers
    )
    assert response.status_code == 422


def test_oversized_photo_is_413(client: TestClient, register, submit, png, monkeypatch):
    user = register("Large Upload")
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    response = submit(user, image=png(payload=b"too-big"))
    assert response.status_code == 413


def test_submission_requires_authentication(client: TestClient, png):
    response = client.post(
        SUBMIT_PATH.format(slug="bike-to-campus"),
        files={"image": ("proof.png", png(), "image/png")},
    )
    assert response.status_code == 401


def test_inactive_challenge_cannot_be_submitted_to(client: TestClient, register, db_session, submit):
    from app.models import Challenge

    challenge = db_session.exec(
        select(Challenge).where(Challenge.slug == "bike-to-campus")
    ).one()
    challenge.is_active = False
    db_session.add(challenge)
    db_session.commit()

    user = register("Late User")
    assert submit(user, "bike-to-campus").status_code == 404


def test_provider_outage_is_502_with_no_points_and_can_be_retried(
    client: TestClient, register, submit, png
):
    user = register("Outage User")
    image = png(payload=b"outage-photo")

    app.dependency_overrides[get_vision_provider] = lambda: BrokenProvider()
    try:
        failed = submit(user, "bike-to-campus", image=image)
    finally:
        app.dependency_overrides[get_vision_provider] = lambda: MockVisionProvider()

    assert failed.status_code == 502
    assert "no points were awarded" in failed.json()["detail"]

    history = client.get("/api/v1/submissions", headers=user.headers).json()
    assert len(history) == 1
    assert history[0]["status"] == "error"
    assert client.get("/api/v1/profile", headers=user.headers).json()["points_total"] == 0

    retried = submit(user, "bike-to-campus", image=image)
    assert retried.status_code == 201
    assert retried.json()["submission"]["status"] == "approved"

    # The errored row was reused, not duplicated.
    history = client.get("/api/v1/submissions", headers=user.headers).json()
    assert len(history) == 1
    assert history[0]["status"] == "approved"


def test_history_pagination(client: TestClient, register, submit, png):
    user = register("History User")
    for slug in ("bike-to-campus", "recycle-waste-batch", "plant-a-sapling"):
        assert submit(user, slug, image=png()).status_code == 201

    first_page = client.get(
        "/api/v1/submissions?limit=2&offset=0", headers=user.headers
    ).json()
    second_page = client.get(
        "/api/v1/submissions?limit=2&offset=2", headers=user.headers
    ).json()
    assert len(first_page) == 2
    assert len(second_page) == 1
    assert first_page[0]["id"] != second_page[0]["id"]


def test_submission_detail_and_image_are_owner_only(
    client: TestClient, register, submit, png
):
    owner = register("Image Owner")
    stranger = register("Image Stranger")
    image = png(payload=b"private-evidence")
    created = submit(owner, "bike-to-campus", image=image).json()["submission"]
    submission_id = created["id"]

    detail = client.get(f"/api/v1/submissions/{submission_id}", headers=owner.headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == submission_id

    image_response = client.get(
        f"/api/v1/submissions/{submission_id}/image", headers=owner.headers
    )
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"
    assert image_response.content == image

    assert (
        client.get(f"/api/v1/submissions/{submission_id}", headers=stranger.headers).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/submissions/{submission_id}/image", headers=stranger.headers
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/submissions/{submission_id}/image").status_code == 401


def test_bare_magic_bytes_are_not_an_image(client: TestClient, register, submit):
    user = register("Signature Only")
    assert submit(user, image=b"\x89PNG\r\n\x1a\n").status_code == 415


def test_corrupted_image_body_is_rejected(client: TestClient, register, submit):
    user = register("Corrupt Image")
    assert submit(user, image=b"\x89PNG\r\n\x1a\n" + b"garbage" * 100).status_code == 415


def test_tiny_image_is_rejected(client: TestClient, register, submit):
    user = register("Tiny Image")
    buffer = BytesIO()
    Image.new("RGB", (64, 64), (10, 20, 30)).save(buffer, format="PNG")
    assert submit(user, image=buffer.getvalue()).status_code == 415


def test_errored_photo_cannot_be_retried_on_a_different_challenge(
    client: TestClient, register, submit, png
):
    user = register("Reattributed Photo")
    image = png()

    app.dependency_overrides[get_vision_provider] = lambda: BrokenProvider()
    try:
        assert submit(user, "bike-to-campus", image=image).status_code == 502
        # The photo belongs to the challenge it was submitted against.
        assert submit(user, "recycle-waste-batch", image=image).status_code == 409
    finally:
        app.dependency_overrides[get_vision_provider] = lambda: MockVisionProvider()

    history = client.get("/api/v1/submissions", headers=user.headers).json()
    assert len(history) == 1
    assert history[0]["challenge"]["slug"] == "bike-to-campus"


def test_retry_of_an_old_errored_photo_cannot_bypass_the_cooldown(
    client: TestClient, register, submit, png, db_session
):
    """Regression: cooldown must run from approval time, not upload time."""
    user = register("Cooldown Bypass")
    image = png()

    app.dependency_overrides[get_vision_provider] = lambda: BrokenProvider()
    try:
        assert submit(user, "bike-to-campus", image=image).status_code == 502
    finally:
        app.dependency_overrides[get_vision_provider] = lambda: MockVisionProvider()

    # The errored row looks ten days old, but it has never been approved.
    row = db_session.exec(
        select(Submission).where(Submission.user_id == user.user["id"])
    ).one()
    row.created_at = utcnow() - timedelta(days=10)
    db_session.add(row)
    db_session.commit()

    retried = submit(user, "bike-to-campus", image=image)
    assert retried.status_code == 201, retried.text
    assert retried.json()["submission"]["status"] == "approved"

    # The fresh approval starts the cooldown now; an immediate new photo must not pass.
    second = submit(user, "bike-to-campus", image=png())
    assert second.status_code == 429, second.text

    profile = client.get("/api/v1/profile", headers=user.headers).json()
    assert profile["points_total"] == 50


def test_concurrent_submissions_for_one_challenge_award_points_once(
    client: TestClient, register, submit, png
):
    user = register("Race User")
    images = [png(), png()]

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda image: submit(user, "bike-to-campus", image=image), images)
        )

    codes = sorted(response.status_code for response in responses)
    assert codes == [201, 429], [response.text for response in responses]

    profile = client.get("/api/v1/profile", headers=user.headers).json()
    assert profile["points_total"] == 50
    history = client.get("/api/v1/submissions", headers=user.headers).json()
    assert len([row for row in history if row["status"] == "approved"]) == 1

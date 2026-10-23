"""Challenge catalogue: content, visibility, and per-student cooldown state."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from app.models import Challenge


def test_lists_the_five_seeded_challenges_anonymously(client: TestClient):
    response = client.get("/api/v1/challenges")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert [c["slug"] for c in body][0] == "bike-to-campus"
    assert body[0]["can_submit"] is True
    assert body[0]["times_completed"] == 0


def test_point_values_match_the_product_spec(client: TestClient):
    by_slug = {c["slug"]: c for c in client.get("/api/v1/challenges").json()}
    assert by_slug["bike-to-campus"]["points"] == 50
    assert by_slug["recycle-waste-batch"]["points"] == 30
    assert by_slug["plant-a-sapling"]["points"] == 100
    assert by_slug["plant-a-sapling"]["cooldown_hours"] == 168
    assert by_slug["bike-to-campus"]["co2_saved_grams"] == 1000


def test_detail_includes_instructions_and_evidence_rules(client: TestClient):
    response = client.get("/api/v1/challenges/bike-to-campus")
    assert response.status_code == 200
    body = response.json()
    assert body["instructions"]
    assert body["evidence_requirements"]
    assert body["description"]


def test_unknown_slug_is_404(client: TestClient):
    assert client.get("/api/v1/challenges/does-not-exist").status_code == 404


def test_inactive_challenge_is_hidden_and_404(client: TestClient, db_session):
    challenge = db_session.exec(
        select(Challenge).where(Challenge.slug == "campus-cleanup")
    ).one()
    challenge.is_active = False
    db_session.add(challenge)
    db_session.commit()

    slugs = [c["slug"] for c in client.get("/api/v1/challenges").json()]
    assert "campus-cleanup" not in slugs
    assert len(slugs) == 4
    assert client.get("/api/v1/challenges/campus-cleanup").status_code == 404


def test_user_state_reflects_a_completed_challenge(client: TestClient, register, submit):
    user = register("State User")
    assert submit(user, "bike-to-campus").status_code == 201

    by_slug = {c["slug"]: c for c in client.get("/api/v1/challenges", headers=user.headers).json()}
    bike = by_slug["bike-to-campus"]
    assert bike["times_completed"] == 1
    assert bike["can_submit"] is False
    assert bike["cooldown_ends_at"] is not None

    other = by_slug["recycle-waste-batch"]
    assert other["can_submit"] is True
    assert other["times_completed"] == 0


def test_anonymous_sees_no_personal_state_after_someone_else_completes(
    client: TestClient, register, submit
):
    user = register("Private User")
    submit(user, "bike-to-campus")
    anonymous = {c["slug"]: c for c in client.get("/api/v1/challenges").json()}
    assert anonymous["bike-to-campus"]["times_completed"] == 0
    assert anonymous["bike-to-campus"]["can_submit"] is True

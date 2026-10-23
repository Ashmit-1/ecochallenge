"""Profile aggregates: zero state, ranking, and honest accounting of rejections."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_initial_profile_is_empty(client: TestClient, register):
    user = register("Blank Slate")
    body = client.get("/api/v1/profile", headers=user.headers).json()

    assert body["points_total"] == 0
    assert body["submissions_total"] == 0
    assert body["submissions_approved"] == 0
    assert body["submissions_rejected"] == 0
    assert body["challenges_completed"] == 0
    assert body["co2_saved_grams"] == 0
    assert body["rank"] == 1
    assert body["total_participants"] == 1
    assert len(body["badges"]) == 6
    assert all(badge["earned"] is False for badge in body["badges"])
    assert body["member_since"].endswith("Z")


def test_profile_reflects_an_approval(client: TestClient, register, submit):
    user = register("Progress User")
    submit(user, "plant-a-sapling")

    body = client.get("/api/v1/profile", headers=user.headers).json()
    assert body["points_total"] == 100
    assert body["submissions_total"] == 1
    assert body["submissions_approved"] == 1
    assert body["challenges_completed"] == 1
    assert body["co2_saved_grams"] == 10_000

    earned = {badge["key"] for badge in body["badges"] if badge["earned"]}
    assert {"first-step", "carbon-cutter"} <= earned


def test_rejections_count_as_attempts_but_not_points(
    client: TestClient, register, submit, png
):
    user = register("Rejected Attempt")
    submit(user, "bike-to-campus", image=png(marker=b"MOCK-REJECT"))

    body = client.get("/api/v1/profile", headers=user.headers).json()
    assert body["points_total"] == 0
    assert body["submissions_total"] == 1
    assert body["submissions_approved"] == 0
    assert body["submissions_rejected"] == 1
    assert body["challenges_completed"] == 0


def test_rank_updates_as_other_students_earn_points(client: TestClient, register, submit):
    first = register("Earlier User")
    submit(first, "bike-to-campus")  # 50

    second = register("Later User")
    assert client.get("/api/v1/profile", headers=second.headers).json()["rank"] == 2

    submit(second, "plant-a-sapling")  # 100 -> takes the lead
    profile = client.get("/api/v1/profile", headers=second.headers).json()
    assert profile["rank"] == 1
    assert profile["total_participants"] == 2

    first_profile = client.get("/api/v1/profile", headers=first.headers).json()
    assert first_profile["rank"] == 2

"""Leaderboard ordering, ties, pagination, and per-entry completion counts."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_orders_by_points_and_flags_the_current_user(client: TestClient, register, submit):
    alice = register("Alice")
    bob = register("Bob")
    cara = register("Cara")

    assert submit(alice, "bike-to-campus").status_code == 201  # 50
    assert submit(bob, "plant-a-sapling").status_code == 201  # 100
    assert submit(cara, "recycle-waste-batch").status_code == 201  # 30

    body = client.get("/api/v1/leaderboard", headers=alice.headers).json()

    assert [entry["display_name"] for entry in body["entries"]] == ["Bob", "Alice", "Cara"]
    assert [entry["rank"] for entry in body["entries"]] == [1, 2, 3]
    assert [entry["points_total"] for entry in body["entries"]] == [100, 50, 30]
    assert [entry["is_current_user"] for entry in body["entries"]] == [False, True, False]
    assert body["current_user_rank"] == 2
    assert body["total_participants"] == 3


def test_ties_share_a_rank_and_skip_the_next(client: TestClient, register, submit):
    first = register("Tie One")
    second = register("Tie Two")
    last = register("Tie Three")

    assert submit(first, "bike-to-campus").status_code == 201
    assert submit(second, "bike-to-campus").status_code == 201

    body = client.get("/api/v1/leaderboard", headers=last.headers).json()
    ranks = sorted(entry["rank"] for entry in body["entries"])
    assert ranks == [1, 1, 3]
    assert body["current_user_rank"] == 3


def test_challenges_completed_counts_distinct_challenges(client: TestClient, register, submit):
    user = register("Multi Challenge")
    assert submit(user, "bike-to-campus").status_code == 201
    assert submit(user, "recycle-waste-batch").status_code == 201

    body = client.get("/api/v1/leaderboard", headers=user.headers).json()
    entry = next(e for e in body["entries"] if e["is_current_user"])
    assert entry["challenges_completed"] == 2


def test_new_student_starts_at_rank_one(client: TestClient, register):
    user = register("Fresh Start")
    body = client.get("/api/v1/leaderboard", headers=user.headers).json()
    assert body["total_participants"] == 1
    assert body["entries"][0]["is_current_user"] is True
    assert body["entries"][0]["rank"] == 1
    assert body["entries"][0]["points_total"] == 0


def test_pagination(client: TestClient, register):
    users = [register(f"Pager {index}") for index in range(3)]
    page = client.get(
        "/api/v1/leaderboard?limit=2&offset=1", headers=users[0].headers
    ).json()
    assert len(page["entries"]) == 2
    assert page["total_participants"] == 3


def test_invalid_pagination_is_422(client: TestClient, register):
    user = register("Bad Pager")
    assert client.get("/api/v1/leaderboard?limit=0", headers=user.headers).status_code == 422
    assert client.get("/api/v1/leaderboard?limit=101", headers=user.headers).status_code == 422

"""Badge rules: thresholds, progress, and the union of earned badges."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.badge_service import BADGES, compute_badges, earned_keys
from app.services.stats_service import UserStats


def _by_key(badges):
    return {badge.key: badge for badge in badges}


def test_badge_definitions_are_unique_and_well_formed():
    keys = [definition.key for definition in BADGES]
    assert len(keys) == len(set(keys))
    for definition in BADGES:
        assert definition.target > 0
        assert definition.name
        assert definition.description
        assert definition.icon


def test_nothing_is_earned_at_zero():
    badges = compute_badges(UserStats(), points_total=0)
    assert len(badges) == len(BADGES)
    assert earned_keys(badges) == set()
    assert all(badge.current == 0 for badge in badges)


def test_every_threshold_is_reachable():
    stats = UserStats(
        submissions_approved=15,
        challenges_completed=15,
        co2_saved_grams=10_000,
        categories_completed=3,
    )
    assert earned_keys(compute_badges(stats, points_total=250)) == {
        "first-step",
        "habit-forming",
        "eco-warrior",
        "century-club",
        "carbon-cutter",
        "all-rounder",
    }


def test_progress_is_capped_at_the_target():
    badges = _by_key(compute_badges(UserStats(submissions_approved=3), points_total=0))
    assert badges["first-step"].earned is True
    assert badges["first-step"].current == 1  # capped, not 3
    assert badges["habit-forming"].earned is False
    assert badges["habit-forming"].current == 3
    assert badges["habit-forming"].target == 5


def test_points_badge_uses_the_running_total():
    badges = _by_key(compute_badges(UserStats(), points_total=250))
    assert badges["century-club"].earned is True
    assert badges["century-club"].current == 250


def test_new_badges_are_reported_once(client: TestClient, register, submit):
    user = register("Badge User")

    first = submit(user, "bike-to-campus").json()
    assert [b["key"] for b in first["new_badges"]] == ["first-step"]

    second = submit(user, "recycle-waste-batch").json()
    assert second["new_badges"] == []

    profile = client.get("/api/v1/profile", headers=user.headers).json()
    earned = {badge["key"] for badge in profile["badges"] if badge["earned"]}
    assert earned == {"first-step"}

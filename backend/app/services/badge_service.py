"""Badge rules. Badges are derived, never stored — see decisions.md D9."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.profile import BadgeRead
from app.services.stats_service import UserStats

BadgeMetric = Literal["approved", "points", "co2", "categories"]


@dataclass(frozen=True, slots=True)
class BadgeDefinition:
    key: str
    name: str
    description: str
    icon: str
    metric: BadgeMetric
    target: int


BADGES: tuple[BadgeDefinition, ...] = (
    BadgeDefinition(
        key="first-step",
        name="First Step",
        description="Complete your first verified challenge.",
        icon="sprout",
        metric="approved",
        target=1,
    ),
    BadgeDefinition(
        key="habit-forming",
        name="Habit Forming",
        description="Get five submissions approved.",
        icon="footprints",
        metric="approved",
        target=5,
    ),
    BadgeDefinition(
        key="eco-warrior",
        name="Eco Warrior",
        description="Reach fifteen approved submissions.",
        icon="award",
        metric="approved",
        target=15,
    ),
    BadgeDefinition(
        key="century-club",
        name="Century Club",
        description="Earn 250 points from verified actions.",
        icon="trophy",
        metric="points",
        target=250,
    ),
    BadgeDefinition(
        key="carbon-cutter",
        name="Carbon Cutter",
        description="Save an estimated 10 kg of CO₂.",
        icon="cloud-off",
        metric="co2",
        target=10_000,
    ),
    BadgeDefinition(
        key="all-rounder",
        name="All-Rounder",
        description="Get approved in three different challenge categories.",
        icon="compass",
        metric="categories",
        target=3,
    ),
)


def _metric_value(definition: BadgeDefinition, stats: UserStats, points_total: int) -> int:
    match definition.metric:
        case "approved":
            return stats.submissions_approved
        case "points":
            return points_total
        case "co2":
            return stats.co2_saved_grams
        case "categories":
            return stats.categories_completed
    return 0


def compute_badges(stats: UserStats, points_total: int) -> list[BadgeRead]:
    badges: list[BadgeRead] = []
    for definition in BADGES:
        value = _metric_value(definition, stats, points_total)
        badges.append(
            BadgeRead(
                key=definition.key,
                name=definition.name,
                description=definition.description,
                icon=definition.icon,
                earned=value >= definition.target,
                current=min(value, definition.target),
                target=definition.target,
            )
        )
    return badges


def earned_keys(badges: list[BadgeRead]) -> set[str]:
    return {badge.key for badge in badges if badge.earned}

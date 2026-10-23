"""Leaderboard contracts."""

from __future__ import annotations

from app.schemas.common import APIModel


class LeaderboardEntry(APIModel):
    rank: int
    user_id: int
    display_name: str
    points_total: int
    challenges_completed: int
    is_current_user: bool = False


class LeaderboardResponse(APIModel):
    entries: list[LeaderboardEntry]
    total_participants: int
    current_user_rank: int

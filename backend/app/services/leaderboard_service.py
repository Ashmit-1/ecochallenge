"""Campus leaderboard built with SQLite window functions."""

from __future__ import annotations

from sqlmodel import Session, func, select

from app.models import Submission, SubmissionStatus, User
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse
from app.services.stats_service import get_user_rank


def get_leaderboard(
    session: Session,
    current_user: User,
    *,
    limit: int,
    offset: int,
) -> LeaderboardResponse:
    completed = (
        select(
            Submission.user_id.label("user_id"),
            func.count(func.distinct(Submission.challenge_id)).label("completed"),
        )
        .where(Submission.status == SubmissionStatus.approved.value)
        .group_by(Submission.user_id)
        .subquery()
    )

    ranked = (
        select(
            User.id.label("user_id"),
            User.display_name.label("display_name"),
            User.points_total.label("points_total"),
            User.created_at.label("created_at"),
            # Points only: students on equal points share a rank.
            func.rank().over(order_by=User.points_total.desc()).label("rank"),
        )
        .where(User.is_active == True)  # noqa: E712
        .subquery()
    )

    rows = session.exec(
        select(
            ranked.c.user_id,
            ranked.c.display_name,
            ranked.c.points_total,
            ranked.c.rank,
            func.coalesce(completed.c.completed, 0),
        )
        .select_from(ranked)
        .outerjoin(completed, completed.c.user_id == ranked.c.user_id)
        # Ties share a rank; account age then user id make the displayed order stable.
        .order_by(ranked.c.rank.asc(), ranked.c.created_at.asc(), ranked.c.user_id.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    entries = [
        LeaderboardEntry(
            rank=int(row[3]),
            user_id=int(row[0]),
            display_name=str(row[1]),
            points_total=int(row[2]),
            challenges_completed=int(row[4]),
            is_current_user=int(row[0]) == current_user.id,
        )
        for row in rows
    ]

    current_rank, total_participants = get_user_rank(session, current_user)
    return LeaderboardResponse(
        entries=entries,
        total_participants=total_participants,
        current_user_rank=current_rank,
    )

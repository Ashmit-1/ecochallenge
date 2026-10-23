"""Aggregate per-student statistics and ranking.

Kept in one place so the profile, badge rules, and leaderboard all agree on what "completed" means.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, case, func, select

from app.models import Challenge, Submission, SubmissionStatus, User


@dataclass(frozen=True, slots=True)
class UserStats:
    submissions_total: int = 0
    submissions_approved: int = 0
    submissions_rejected: int = 0
    challenges_completed: int = 0
    co2_saved_grams: int = 0
    categories_completed: int = 0


def get_user_stats(session: Session, user_id: int) -> UserStats:
    approved = SubmissionStatus.approved.value
    rejected = SubmissionStatus.rejected.value

    row = session.exec(
        select(
            func.count(Submission.id),
            func.coalesce(func.sum(case((Submission.status == approved, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Submission.status == rejected, 1), else_=0)), 0),
            func.coalesce(
                func.sum(
                    case(
                        (Submission.status == approved, Submission.co2_saved_grams),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(Submission.user_id == user_id)
    ).one()

    distinct_challenges = session.exec(
        select(func.count(func.distinct(Submission.challenge_id))).where(
            Submission.user_id == user_id,
            Submission.status == approved,
        )
    ).one()

    distinct_categories = session.exec(
        select(func.count(func.distinct(Challenge.category)))
        .select_from(Submission)
        .join(Challenge, Challenge.id == Submission.challenge_id)
        .where(
            Submission.user_id == user_id,
            Submission.status == approved,
        )
    ).one()

    return UserStats(
        submissions_total=int(row[0] or 0),
        submissions_approved=int(row[1] or 0),
        submissions_rejected=int(row[2] or 0),
        challenges_completed=int(distinct_challenges or 0),
        co2_saved_grams=int(row[3] or 0),
        categories_completed=int(distinct_categories or 0),
    )


def get_total_participants(session: Session) -> int:
    total = session.exec(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    ).one()
    return int(total or 0)


def get_user_rank(session: Session, user: User) -> tuple[int, int]:
    """Return ``(rank, total_participants)``.

    Rank is 1-based among active users by points. Ties share a rank (``RANK()`` semantics), so a
    student with 50 points alongside another with 50 is rank 1, not rank 2.
    """
    rank_column = func.rank().over(order_by=User.points_total.desc()).label("rank")
    ranked = (
        select(User.id.label("user_id"), rank_column)
        .where(User.is_active == True)  # noqa: E712
        .subquery()
    )
    rank = session.exec(select(ranked.c.rank).where(ranked.c.user_id == user.id)).first()
    return int(rank or 1), get_total_participants(session)

"""SQLModel tables. Importing this package registers every table with the metadata."""

from app.models.base import utcnow
from app.models.challenge import Challenge, ChallengeCategory
from app.models.submission import Submission, SubmissionStatus
from app.models.user import User

__all__ = [
    "Challenge",
    "ChallengeCategory",
    "Submission",
    "SubmissionStatus",
    "User",
    "utcnow",
]

"""Seeding is idempotent and never resurrects a retired challenge."""

from __future__ import annotations

from sqlmodel import select

from app.db.seed import CHALLENGES, apply_seed
from app.models import Challenge


def test_seed_creates_then_refreshes_without_duplicates(db_session):
    assert apply_seed(db_session) == (5, 0)
    assert apply_seed(db_session) == (0, 5)

    challenges = db_session.exec(select(Challenge)).all()
    assert len(challenges) == 5
    assert {c.slug for c in challenges} == {c["slug"] for c in CHALLENGES}


def test_seed_preserves_a_deactivated_challenge(db_session):
    apply_seed(db_session)
    challenge = db_session.exec(
        select(Challenge).where(Challenge.slug == "campus-cleanup")
    ).one()
    challenge.is_active = False
    db_session.add(challenge)
    db_session.commit()

    apply_seed(db_session)
    db_session.refresh(challenge)
    assert challenge.is_active is False


def test_seed_refreshes_edited_content(db_session):
    apply_seed(db_session)
    challenge = db_session.exec(
        select(Challenge).where(Challenge.slug == "bike-to-campus")
    ).one()
    challenge.points = 999
    db_session.add(challenge)
    db_session.commit()

    apply_seed(db_session)
    db_session.refresh(challenge)
    assert challenge.points == 50


def test_seeded_co2_notes_are_present_for_the_estimate_disclaimer(db_session):
    apply_seed(db_session)
    for challenge in db_session.exec(select(Challenge)).all():
        if challenge.co2_saved_grams > 0:
            assert challenge.co2_note, f"{challenge.slug} is missing its CO2 assumption"

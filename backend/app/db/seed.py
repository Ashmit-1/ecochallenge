"""Starter challenge catalogue.

Idempotent: keyed by ``slug``. Existing rows get their content refreshed, but ``is_active`` is
left untouched so a deactivated challenge is not resurrected by re-seeding.

Run with ``uv run seed`` (schema must exist first).
"""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.db.session import SessionLocal
from app.models import Challenge, ChallengeCategory

# Every challenge is data, not code, so points/cooldowns/impact can be tuned without a migration.
# CO2 figures are deliberately conservative estimates; the note is shown in the UI next to them.
CHALLENGES: list[dict[str, Any]] = [
    {
        "slug": "bike-to-campus",
        "title": "Bike to Campus",
        "tagline": "Skip the engine. Keep the morning air.",
        "description": (
            "Swap the bike, scooter, or car for a cycle on your way to campus. Every pedal stroke "
            "replaces a motorised trip and keeps a little more carbon out of the air. It counts "
            "whether you ride the whole way or park and pedal the last stretch."
        ),
        "instructions": (
            "1. Choose a day and cycle to campus instead of taking a motor vehicle.\n"
            "2. Lock your cycle at a campus stand.\n"
            "3. Take a photo showing the cycle at campus.\n"
            "4. Describe the trip briefly when you submit."
        ),
        "evidence_requirements": (
            "A photo of your bicycle parked at a campus stand or gate. The campus setting should be "
            "recognisable — a bike in an unrelated room will not pass."
        ),
        "points": 50,
        "co2_saved_grams": 1000,
        "co2_note": "Estimate: a 5 km round trip cycled instead of driven in an average petrol car (~200 g CO₂/km).",
        "category": ChallengeCategory.transport.value,
        "icon": "bike",
        "cooldown_hours": 24,
        "sort_order": 10,
    },
    {
        "slug": "recycle-waste-batch",
        "title": "Recycle a Waste Batch",
        "tagline": "Sorted right, kept out of the landfill.",
        "description": (
            "Collect a batch of recyclable waste — paper, plastic, glass, or metal — and take it to "
            "a proper recycling point instead of the general bin. Small batches count; consistency "
            "is what matters."
        ),
        "instructions": (
            "1. Gather a batch of recyclables from your room, hostel, or department.\n"
            "2. Rinse and dry anything food-stained.\n"
            "3. Sort by material and drop it at a campus recycling station.\n"
            "4. Photograph the sorted batch at the drop-off point."
        ),
        "evidence_requirements": (
            "A photo of the sorted recyclables beside the recycling bin or drop-off point. "
            "A closed, unlabelled bag is not enough — the materials should be visible."
        ),
        "points": 30,
        "co2_saved_grams": 800,
        "co2_note": "Estimate: ~2 kg of mixed recyclables diverted from landfill, using typical avoided-emission factors.",
        "category": ChallengeCategory.waste.value,
        "icon": "recycle",
        "cooldown_hours": 24,
        "sort_order": 20,
    },
    {
        "slug": "plant-a-sapling",
        "title": "Plant a Sapling",
        "tagline": "A hundred years starts with one afternoon.",
        "description": (
            "Plant a sapling in a campus garden, your home, or a community patch — and commit to "
            "watering it while it establishes. Native species need less help and support local birds "
            "and insects."
        ),
        "instructions": (
            "1. Pick a native sapling suited to your area.\n"
            "2. Dig a hole twice the width of the root ball and plant it at the right depth.\n"
            "3. Water it thoroughly and add a light layer of mulch.\n"
            "4. Photograph the planted sapling and note where it is."
        ),
        "evidence_requirements": (
            "A photo of the freshly planted sapling, with the disturbed soil around its base visible. "
            "Include yourself or a handwritten date note so the planting is clearly new."
        ),
        "points": 100,
        "co2_saved_grams": 10000,
        "co2_note": "Estimate: roughly 10 kg CO₂ sequestered by one establishing sapling in its first year.",
        "category": ChallengeCategory.nature.value,
        "icon": "sprout",
        "cooldown_hours": 168,
        "sort_order": 30,
    },
    {
        "slug": "reuse-instead-of-disposable",
        "title": "Choose Reuse Over Disposable",
        "tagline": "The best bottle is the one you already own.",
        "description": (
            "Carry and use a reusable bottle, cup, bag, or container instead of buying a single-use "
            "alternative for a day on campus. It is the least dramatic challenge and the one that "
            "adds up fastest."
        ),
        "instructions": (
            "1. Bring a reusable bottle, cup, bag, or lunch box with you.\n"
            "2. Use it instead of the disposable option at the canteen, shop, or water point.\n"
            "3. Photograph your reusable item in use on campus."
        ),
        "evidence_requirements": (
            "A photo of the reusable item in a campus context — on a canteen table, in your hand at a "
            "water station, or in your bag. Disposable items in the frame will fail the check."
        ),
        "points": 40,
        "co2_saved_grams": 150,
        "co2_note": "Estimate: one avoided single-use cup or bottle, including production and disposal.",
        "category": ChallengeCategory.reuse.value,
        "icon": "repeat",
        "cooldown_hours": 24,
        "sort_order": 40,
    },
    {
        "slug": "campus-cleanup",
        "title": "Campus Cleanup",
        "tagline": "Leave it better than you found it.",
        "description": (
            "Spend at least fifteen minutes picking up litter in a campus area — a courtyard, the "
            "grounds around the canteen, or a garden path. Bring a friend and it becomes a habit "
            "instead of a chore."
        ),
        "instructions": (
            "1. Take gloves and a bag (reuse one you already have).\n"
            "2. Spend at least fifteen minutes collecting litter in one area.\n"
            "3. Separate recyclables from general waste and dispose of both properly.\n"
            "4. Photograph the cleaned area and the collected bag."
        ),
        "evidence_requirements": (
            "A photo of the cleaned area with the bag of collected litter in frame. A before/after pair "
            "is even better. An empty bag on an already-clean lawn will not pass."
        ),
        "points": 60,
        "co2_saved_grams": 200,
        "co2_note": "Indirect estimate: litter diverted from open dumping or burning rather than a direct transport saving.",
        "category": ChallengeCategory.community.value,
        "icon": "sparkles",
        "cooldown_hours": 72,
        "sort_order": 50,
    },
]


def apply_seed(session: Session) -> tuple[int, int]:
    """Insert missing challenges and refresh known ones.

    Returns ``(created, updated)``. ``is_active`` is never overwritten.
    """
    created = 0
    updated = 0
    for payload in CHALLENGES:
        existing = session.exec(select(Challenge).where(Challenge.slug == payload["slug"])).first()
        if existing is None:
            session.add(Challenge(**payload))
            created += 1
            continue
        for field, value in payload.items():
            if field != "is_active":
                setattr(existing, field, value)
        session.add(existing)
        updated += 1
    session.commit()
    return created, updated


def main() -> None:
    with SessionLocal() as session:
        created, updated = apply_seed(session)
    print(f"Seed complete: {created} created, {updated} refreshed.")


if __name__ == "__main__":
    main()

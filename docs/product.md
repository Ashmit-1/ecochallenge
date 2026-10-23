# Product rules, in implementation terms

The product idea is in the project brief; this file is the version a developer can test against.

## Challenges

Each challenge has: title, tagline, description, step-by-step instructions, evidence requirements,
points, an estimated CO₂ saving with a stated assumption, a category, a cooldown, and an icon name.
Challenges are **data**, seeded from `backend/app/db/seed.py`, not hardcoded in routes.

| Slug | Points | Cooldown | Est. CO₂ | Category |
|---|---|---|---|---|
| `bike-to-campus` | 50 | 24 h | 1,000 g | transport |
| `recycle-waste-batch` | 30 | 24 h | 800 g | waste |
| `plant-a-sapling` | 100 | 168 h | 10,000 g | nature |
| `reuse-instead-of-disposable` | 40 | 24 h | 150 g | reuse |
| `campus-cleanup` | 60 | 72 h | 200 g | community |

CO₂ figures are **estimates** with documented assumptions shown in `co2_note`; the UI must label
them as such. They exist to make impact tangible, not to be audited.

## Submission rules

1. Only active challenges accept submissions.
2. The image must be JPEG/PNG/WebP under 6 MB.
3. Rejected: same challenge **approved** within `cooldown_hours` → `429`, with a retry time.
4. Rejected: identical bytes already submitted by anyone → `409`.
5. Points are awarded **only** on an approved verdict, in the same transaction.
6. A provider error is not a rejection: no points, status `error`, and the photo may be retried.
7. Every attempt stays in history, including rejections.

## Points

Awarded equal to the challenge's point value at the moment of approval, snapshotted on the
submission. Ties on the leaderboard break by account age (earlier account ranks higher), so the
order is stable.

## Badges

Computed from approved submissions only.

| Key | Name | Rule | Icon name |
|---|---|---|---|
| `first-step` | First Step | 1 approved submission | `sprout` |
| `habit-forming` | Habit Forming | 5 approved submissions | `footprints` |
| `eco-warrior` | Eco Warrior | 15 approved submissions | `award` |
| `century-club` | Century Club | 250 points earned | `trophy` |
| `carbon-cutter` | Carbon Cutter | 10,000 g CO₂ saved | `cloud-off` |
| `all-rounder` | All-Rounder | approved in 3 different categories | `compass` |

Each badge reports `earned`, plus `current` / `target` so the UI can show progress bars.

## Profile

- `points_total`
- `submissions_approved`, `submissions_rejected`, `submissions_total`
- `challenges_completed` (distinct challenges ever approved)
- `co2_saved_grams`
- `rank` among active users, `total_participants`
- badge list with progress

## Leaderboard

Active users only, ordered by points desc then account age asc, ranked with SQLite's `RANK()`.
Paginated by `limit`/`offset` (max 100). The current user's row is flagged so the UI can pin it.

## Language the UI must use

- AI verification "helps confirm" evidence; it "can be wrong". Never "proves".
- CO₂ numbers are "estimated".
- A rejection explains what was wrong and how to fix it, without accusing the student.

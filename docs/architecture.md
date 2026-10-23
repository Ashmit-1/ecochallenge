# Architecture

## Shape

One FastAPI service, one SQLite database, one folder of uploaded photos. The future React SPA
will be a separate app that talks to this API over HTTP; the API has no knowledge of the UI.

```
browser ──HTTP/JSON──> FastAPI (/api/v1) ──> services ──> SQLModel ──> SQLite
                                 │
                                 └──> vision provider ──> Gemini (or mock)
```

## Request lifecycle

Every authenticated request goes through the same chain:

1. **Route** (`app/api/v1/routes/*`) — parses input, declares the response model, one job only.
2. **Dependency** (`app/api/deps.py`) — opens the DB session, decodes the JWT, loads the user.
3. **Service** (`app/services/*`) — all business rules live here: cooldowns, points, badges,
   dedupe, impact. Routes never contain rules.
4. **Model** (`app/models/*`) — SQLModel tables. No behaviour beyond tiny computed helpers.
5. **Schema** (`app/schemas/*`) — Pydantic shapes going out (and small ones coming in). Database
   models are never returned directly.

The rule of thumb: **a route should read like a table of contents.** If it has an `if` about the
domain, the logic belongs in a service.

## The photo-submission flow (the important one)

`POST /challenges/{slug}/submissions` (multipart image):

1. Validate the challenge is active, and **decode** the file with Pillow as a real JPEG/PNG/WebP
   (at least 200×200 px, under the size and pixel caps). Magic bytes alone are not accepted.
2. **Cooldown check** — reject with `429` if an *approved* submission for this user+challenge
   exists within `cooldown_hours`, measured from **approval time** (`verified_at`). Rejected
   attempts and errored uploads do not lock the user out.
3. **Duplicate check** — SHA-256 the bytes; reject with `409` if any submission already used it.
4. Persist the file as `uploads/{user_id}/{uuid}.{ext}` and create the submission as `pending`.
5. **Verify** through `VisionProvider`: image + challenge context → `approved`, `confidence`,
   `reason`. On provider failure the submission becomes `error` and no points move.
6. On approval only, inside one write transaction: conditionally claim the `pending` row, re-check
   the cooldown now that the write lock is held, snapshot `points`/`co2_saved_grams`, and increment
   the user's total. A competing approval either committed first (visible to the re-check) or is
   still blocked, so two uploads cannot both be awarded. Then compute newly earned badges.
7. Return the submission, the verification verdict, the refreshed profile totals, and any new
   badges — one round trip, because the user is waiting on this screen.

Rejected submissions keep their record (history + audit) and award nothing.

## Why synchronous verification

The product experience is "upload → verdict". A job queue would add a worker, a status machine,
and polling UI for a flow that normally takes 2–6 seconds. The provider call is bounded by a
timeout, and failures degrade to `error` with a retry message rather than corrupting points.
If traffic ever makes this untenable, `pending` is already a valid status and the provider
interface does not need to change.

## Data model at a glance

```
User 1───* Submission *───1 Challenge
```

- `User.points_total` is **denormalized** — updated in the same transaction as an approval. It
  keeps the leaderboard and rank queries trivial; it can always be rebuilt from approved
  submissions if it ever drifts.
- `Submission` snapshots `points_awarded` and `co2_saved_grams` at approval time, so editing a
  challenge later never rewrites someone's history.
- `Challenge` carries its own `cooldown_hours` and `co2_note` (the assumption behind its number),
  making challenges data, not code.

## Layered folders

```
backend/app/
├── api/       HTTP boundary: routes, dependencies
├── core/      config, security primitives
├── db/        engine/session, seed script
├── models/    SQLModel tables
├── schemas/   request/response DTOs
├── services/  business rules
└── vision/    AI verification behind a swappable interface
```

A change to a rule touches `services/`. A change to a field touches `models/` + a migration +
`schemas/`. A new endpoint touches `api/`. Nothing reaches across layers.

## Environments

| | Development | Test |
|---|---|---|
| Database | `backend/data/ecochallenge.db` | temp file per test |
| Vision | Gemini if key present, else configured mock | always mock |
| Config | `backend/.env` | overridden fixtures |

There is no production environment yet; a VPS is planned but unconfirmed. When it happens, the
only code-level change needed is a real `SECRET_KEY`, a real `DATABASE_URL`, strict
`CORS_ORIGINS`, and a reverse proxy in front of `fastapi run`.

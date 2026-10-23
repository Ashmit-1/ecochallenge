# app/

The application package. Everything the API runs lives here, layered so that HTTP concerns,
business rules, and persistence never bleed into each other.

| Path | What it owns | Open it when |
|---|---|---|
| [main.py](main.py) | App factory, lifespan, middleware, router mount, error handlers | Changing global wiring |
| [api/](api/api.md) | Routes and dependencies — the HTTP boundary | Adding/changing an endpoint |
| [core/](core/core.md) | Settings, JWT, password hashing | Config or auth primitives |
| [db/](db/db.md) | Engine/session, seed data | Connection or starter data |
| [models/](models/models.md) | SQLModel tables | Schema changes (then a migration) |
| [schemas/](schemas/schemas.md) | Request/response DTOs | Changing the API contract |
| [services/](services/services.md) | Business rules: points, cooldowns, badges, ranking | Changing what the app *does* |
| [vision/](vision/vision.md) | AI photo verification providers | Touching verification |

## Layering rule

```
api (routes) → services (rules) → models (persistence)
```

- Routes parse, authorize, and shape responses. No domain `if`s.
- Services hold every rule and may raise `HTTPException` (this is a FastAPI app, not a library).
- Models are tables only.
- Schemas are the wire format; never return a model directly.

## Import order notes

`app.db.session` creates the engine at import time from `core.config.get_settings()`. That means
importing `app` requires a valid `.env` (at minimum `SECRET_KEY`). Tests set environment variables
before importing, or override the session dependency.

The app is assembled by `create_app()` in `main.py` rather than a module-level `app = FastAPI()`,
so tests can build isolated instances with overridden settings.

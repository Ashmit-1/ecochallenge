# syntax=docker/dockerfile:1
# EcoChallenge API — Cloud Run image.
#
# The database is Turso and photos live in Cloudflare R2, so the container holds no state:
# Cloud Run's disk is ephemeral. Configuration arrives as environment variables at runtime.

# --- Build: resolve and install the locked dependency graph -------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: application edits then reuse this layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Application code, migrations, and the project itself (the `seed` entry point).
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

# --- Runtime: nothing but the venv and the app --------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

# SQLite is the local-development default; the directories keep that path writable too.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /app/uploads \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

ENTRYPOINT ["/app/docker-entrypoint.sh"]

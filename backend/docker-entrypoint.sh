#!/bin/sh
# Cloud Run container entrypoint.
#
# Migrations run on boot so a new revision brings its own schema. Run a single instance (or a
# separate job) while migrating: two containers upgrading the same database at once can race.
set -eu

PORT="${PORT:-8080}"

echo "Applying database migrations..."
alembic upgrade head

echo "Seeding the challenge catalogue..."
python -m app.db.seed

echo "Starting API on 0.0.0.0:${PORT}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --proxy-headers \
    --forwarded-allow-ips='*'

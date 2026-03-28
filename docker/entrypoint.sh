#!/bin/sh
set -e

# If a full command is passed (e.g. celery worker/beat), run it directly
if [ "$1" = "uv" ]; then
    exec "$@"
fi

echo "Running database migrations..."
uv run alembic upgrade head

if [ "$DEV_MODE" = "true" ]; then
    echo "Seeding development data..."
    uv run python scripts/seed_dev.py
fi

echo "Starting server..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"

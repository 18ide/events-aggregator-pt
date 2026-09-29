#!/bin/bash
set -uo pipefail

echo "=== events-aggregator starting ==="
echo "PORT=${PORT:-<not set>}"
echo "DATABASE_URL set: $([ -n "${DATABASE_URL:-}" ] && echo yes || echo no)"
echo "EVENTS_PROVIDER_URL: ${EVENTS_PROVIDER_URL:-<not set>}"
echo "EVENTS_PROVIDER_API_KEY set: $([ -n "${EVENTS_PROVIDER_API_KEY:-}" ] && echo yes || echo no)"

echo "=== skipping alembic (temporary) ==="
# uv run alembic upgrade head

echo "=== starting uvicorn ==="
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --proxy-headers
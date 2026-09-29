#!/bin/bash
set -uo pipefail

echo "=== events-aggregator starting ==="
echo "PORT=${PORT:-<not set>}"
echo "DATABASE_URL set: $([ -n "${DATABASE_URL:-}" ] && echo yes || echo no)"
echo "EVENTS_PROVIDER_URL: ${EVENTS_PROVIDER_URL:-<not set>}"
echo "EVENTS_PROVIDER_API_KEY set: $([ -n "${EVENTS_PROVIDER_API_KEY:-}" ] && echo yes || echo no)"

echo "=== alembic upgrade head ==="
uv run alembic upgrade head
ALEMBIC_STATUS=$?
echo "alembic exit code: $ALEMBIC_STATUS"
if [ $ALEMBIC_STATUS -ne 0 ]; then
  echo "!!! MIGRATION FAILED, ABORTING !!!"
  exit $ALEMBIC_STATUS
fi

echo "=== starting uvicorn on 0.0.0.0:${PORT:-8000} ==="
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --proxy-headers
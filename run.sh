#!/bin/bash

{
  echo "=== env ==="
  echo "PWD=$(pwd)"
  echo "PORT=${PORT:-<not set>}"
  echo "DATABASE_URL set: $([ -n "${DATABASE_URL:-}" ] && echo yes || echo no)"
  echo "EVENTS_PROVIDER_URL: ${EVENTS_PROVIDER_URL:-<not set>}"
  echo "EVENTS_PROVIDER_API_KEY set: $([ -n "${EVENTS_PROVIDER_API_KEY:-}" ] && echo yes || echo no)"

  echo ""
  echo "=== ls /app ==="
  ls -la /app

  echo ""
  echo "=== ls /app/.venv/bin ==="
  ls -la /app/.venv/bin 2>&1

  echo ""
  echo "=== ls /app/src ==="
  ls -la /app/src 2>&1

  echo ""
  echo "=== python version ==="
  /app/.venv/bin/python --version 2>&1

  echo ""
  echo "=== import app.main ==="
  cd /app
  PYTHONPATH=/app/src /app/.venv/bin/python -c "import app.main; print('IMPORT OK')" 2>&1

  echo ""
  echo "=== import settings ==="
  PYTHONPATH=/app/src /app/.venv/bin/python -c "from app.core.config import settings; print('settings OK, db set:', bool(settings.database_url))" 2>&1

  echo ""
  echo "=== uvicorn version ==="
  /app/.venv/bin/python -m uvicorn --version 2>&1

  echo ""
  echo "=== try to start uvicorn (5 sec) ==="
  cd /app
  PYTHONPATH=/app/src timeout 5 /app/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 2>&1 || echo "uvicorn exited with code $?"

} > /app/diag.txt 2>&1

echo "=== starting http.server, diag available at /diag.txt ==="
cd /app
exec python3 -m http.server 8000 --bind 0.0.0.0 --directory /app
#!/bin/bash

DIAG=/tmp/diag.txt

{
  echo "=== env ==="
  echo "PWD=$(pwd)"
  echo "USER=$(whoami)"
  echo "PORT=${PORT:-<not set>}"
  echo "DATABASE_URL set: $([ -n "${DATABASE_URL:-}" ] && echo yes || echo no)"
  echo "EVENTS_PROVIDER_URL: ${EVENTS_PROVIDER_URL:-<not set>}"
  echo "EVENTS_PROVIDER_API_KEY set: $([ -n "${EVENTS_PROVIDER_API_KEY:-}" ] && echo yes || echo no)"

  echo ""
  echo "=== test write to /app ==="
  touch /app/_test_write 2>&1 && echo "/app writable" && rm -f /app/_test_write || echo "/app NOT writable"

  echo ""
  echo "=== ls -la /app ==="
  ls -la /app 2>&1

  echo ""
  echo "=== ls -la /app/.venv/bin ==="
  ls -la /app/.venv/bin 2>&1

  echo ""
  echo "=== python version ==="
  /app/.venv/bin/python --version 2>&1
  echo "exit: $?"

  echo ""
  echo "=== import app.main ==="
  cd /app
  PYTHONPATH=/app/src /app/.venv/bin/python -c "import app.main; print('IMPORT OK')" 2>&1
  echo "exit: $?"

  echo ""
  echo "=== import settings ==="
  PYTHONPATH=/app/src /app/.venv/bin/python -c "from app.core.config import settings; print('settings OK, db set:', bool(settings.database_url))" 2>&1
  echo "exit: $?"

  echo ""
  echo "=== uvicorn start test on port 8001 (5 sec) ==="
  PYTHONPATH=/app/src timeout 5 /app/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 2>&1
  echo "uvicorn exit code: $?"

} > "$DIAG" 2>&1

echo "=== diag written to $DIAG, size: $(wc -c < $DIAG) bytes ==="

echo "=== starting http.server on /tmp ==="
cd /tmp
exec python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp
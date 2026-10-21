#!/bin/bash
DIAG=/tmp/diag.txt
{
  echo "=== env ==="
  echo "GLITCHTIP_DSN set: $([ -n "${GLITCHTIP_DSN:-}" ] && echo yes || echo no)"
  if [ -n "${GLITCHTIP_DSN:-}" ]; then
    echo "GLITCHTIP_DSN length: ${#GLITCHTIP_DSN}"
    echo "GLITCHTIP_DSN prefix: ${GLITCHTIP_DSN:0:30}..."
    case "$GLITCHTIP_DSN" in
      https://*) echo "starts with https:// OK" ;;
      *) echo "WRONG prefix" ;;
    esac
    case "$GLITCHTIP_DSN" in
      */60) echo "ends with /60 OK" ;;
      */60/) echo "ends with /60/ (ok)" ;;
      *) echo "ends with WRONG suffix" ;;
    esac
  fi

  echo ""
  echo "=== sentry send test ==="
  cd /app
  PYTHONPATH=/app/src /app/.venv/bin/python -c "
import os
import sentry_sdk
dsn = os.environ.get('GLITCHTIP_DSN')
print('dsn present:', bool(dsn))
if not dsn:
    print('SKIP: no dsn')
else:
    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0, environment='diag')
    try:
        raise RuntimeError('sentry diag from container')
    except Exception as e:
        event_id = sentry_sdk.capture_exception(e)
        print('captured event_id:', event_id)
    flushed = sentry_sdk.flush(timeout=15)
    print('flush result:', flushed)
" 2>&1
  echo "sentry script exit: $?"

  echo ""
  echo "=== alembic upgrade head ==="
  /app/.venv/bin/python -m alembic upgrade head 2>&1
  echo "alembic exit: $?"
} > "$DIAG" 2>&1

echo "=== diag at /diag.txt ==="
cd /tmp
exec python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp
#!/bin/bash
DIAG=/tmp/diag.txt
{
  echo "=== curl verify-on ==="
  curl -s -o /dev/null -w "status: %{http_code}\n" --max-time 5 https://glitchtip.dev-2.python-labs.ru/api/0/

  echo "=== curl verify-off ==="
  curl -sk -o /dev/null -w "status: %{http_code}\n" --max-time 5 https://glitchtip.dev-2.python-labs.ru/api/0/

  echo "=== internal .svc ==="
  curl -s -o /dev/null -w "status: %{http_code}\n" --max-time 5 http://student-system-glitchtip-web.student-system-glitchtip.svc:8000/api/0/

  echo "=== python sentry test ==="
  cd /app
  PYTHONPATH=/app/src /app/.venv/bin/python -c "
import os
from sentry_sdk.transport import HttpTransport
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

class NoVerify(HttpTransport):
    def _get_pool(self):
        from urllib3 import PoolManager
        from urllib3.util.retry import Retry
        return PoolManager(num_pools=10, maxsize=10, cert_reqs='CERT_NONE', retries=Retry(0))

dsn = os.environ.get('GLITCHTIP_DSN')
sentry_sdk.init(dsn=dsn, transport=NoVerify, traces_sample_rate=0.0)
try:
    raise RuntimeError('diag with SSL off')
except Exception as e:
    eid = sentry_sdk.capture_exception(e)
    print('captured:', eid)
sentry_sdk.flush(timeout=10)
print('flush done')
" 2>&1
} > "$DIAG" 2>&1

echo "=== diag at /diag.txt ==="
cd /tmp
exec python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp
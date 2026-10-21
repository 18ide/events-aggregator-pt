#!/bin/bash
DIAG=/tmp/diag.txt
{
  echo "=== python httpx connectivity ==="
  cd /app
  PYTHONPATH=/app/src /app/.venv/bin/python -c "
import httpx

tests = [
    ('external https', 'https://glitchtip.dev-2.python-labs.ru/api/0/'),
    ('internal svc http', 'http://student-system-glitchtip-web.student-system-glitchtip.svc:8000/api/0/'),
    ('internal svc https', 'https://student-system-glitchtip-web.student-system-glitchtip.svc:8000/api/0/'),
]

for name, url in tests:
    try:
        r = httpx.get(url, verify=False, timeout=5)
        print(f'{name}: HTTP {r.status_code}')
    except Exception as e:
        print(f'{name}: FAILED — {type(e).__name__}: {e}')
" 2>&1

  echo ""
  echo "=== dns lookup ==="
  PYTHONPATH=/app/src /app/.venv/bin/python -c "
import socket
hosts = [
    'glitchtip.dev-2.python-labs.ru',
    'student-system-glitchtip-web.student-system-glitchtip.svc',
]
for h in hosts:
    try:
        ip = socket.gethostbyname(h)
        print(f'{h} -> {ip}')
    except Exception as e:
        print(f'{h} -> FAILED: {e}')
" 2>&1
} > "$DIAG" 2>&1

echo "=== diag at /diag.txt ==="
cd /tmp
exec python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp
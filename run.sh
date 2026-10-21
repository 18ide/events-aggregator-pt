#!/bin/bash
DIAG=/tmp/diag.txt
{
  echo "=== DNS lookup candidates ==="
  cd /app
  PYTHONPATH=/app/src /app/.venv/bin/python -c "
import socket

candidates = [
    'student-system-glitchtip-web.student-system-glitchtip.svc',
    'student-system-glitchtip-web.student-system-glitchtip.svc.cluster.local',
    'glitchtip-web.glitchtip.svc',
    'glitchtip-web.glitchtip.svc.cluster.local',
    'student-system-glitchtip.svc',
    'glitchtip.svc',
    'student-system-events-provider-web.student-system-events-provider.svc',
]

for host in candidates:
    try:
        ip = socket.gethostbyname(host)
        print(f'OK  {host} -> {ip}')
    except Exception as e:
        print(f'FAIL {host} -> {e}')
" 2>&1

  echo ""
  echo "=== HTTP connectivity (httpx) ==="
  PYTHONPATH=/app/src /app/.venv/bin/python -c "
import httpx

urls = [
    'http://student-system-glitchtip-web.student-system-glitchtip.svc:8000/api/0/',
    'http://glitchtip-web.glitchtip.svc:8000/api/0/',
    'http://student-system-glitchtip.svc:8000/api/0/',
    'http://glitchtip.svc:8000/api/0/',
    'https://glitchtip.dev-2.python-labs.ru/api/0/',
]

for url in urls:
    try:
        r = httpx.get(url, verify=False, timeout=3.0, follow_redirects=True)
        print(f'HTTP {r.status_code}  {url}')
    except Exception as e:
        print(f'ERR  {type(e).__name__}  {url}')
" 2>&1
} > "$DIAG" 2>&1

echo "=== diag at /diag.txt ==="
cd /tmp
exec python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp
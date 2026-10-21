#!/bin/bash
DIAG=/tmp/diag.txt
{
  echo "=== try glitchtip-web.glitchtip.svc on multiple ports ==="
  cd /app
  PYTHONPATH=/app/src /app/.venv/bin/python -c "
import httpx

host = 'glitchtip-web.glitchtip.svc'
attempts = [
    ('http',  80),
    ('http',  8000),
    ('http',  8080),
    ('http',  3000),
    ('https', 443),
    ('https', 8000),
    ('https', 8443),
]

for scheme, port in attempts:
    url = f'{scheme}://{host}:{port}/api/0/'
    try:
        r = httpx.get(url, verify=False, timeout=3.0, follow_redirects=True)
        print(f'OK  HTTP {r.status_code}  {url}')
    except Exception as e:
        print(f'ERR {type(e).__name__:25s} {url}')
" 2>&1

  echo ""
  echo "=== try https on default port (443) without explicit ==="
  PYTHONPATH=/app/src /app/.venv/bin/python -c "
import httpx
for url in [
    'https://glitchtip-web.glitchtip.svc/api/0/',
    'http://glitchtip-web.glitchtip.svc/api/0/',
]:
    try:
        r = httpx.get(url, verify=False, timeout=3.0, follow_redirects=True)
        print(f'OK  HTTP {r.status_code}  {url}')
    except Exception as e:
        print(f'ERR {type(e).__name__:25s} {url}')
" 2>&1
} > "$DIAG" 2>&1

echo "=== diag at /diag.txt ==="
cd /tmp
exec python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp
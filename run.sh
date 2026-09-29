#!/bin/bash
set -e

echo "=== diag mode: simple http server ==="
echo "PORT=${PORT:-<not set>}"
echo "Start at $(date)"

exec python3 -m http.server "${PORT:-8000}" --bind 0.0.0.0
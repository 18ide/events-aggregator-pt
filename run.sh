#!/bin/bash

echo "=== diag started ==="
echo "PWD=$(pwd)"
echo "whoami=$(whoami)"
echo "ls /app:"
ls -la /app || echo "cannot list /app"
echo "ls /app/.venv/bin:"
ls -la /app/.venv/bin 2>&1 || echo "no /app/.venv/bin"
echo "which python3:"
which python3 || echo "no python3"
echo "which uv:"
which uv || echo "no uv"

echo "=== trying /app/.venv/bin/python ==="
/app/.venv/bin/python --version 2>&1 || echo "FAILED: /app/.venv/bin/python not executable"

echo "=== sleeping 30s so we can inspect ==="
sleep 30

echo "=== starting simple http server ==="
exec python3 -m http.server 8000 --bind 0.0.0.0
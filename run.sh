#!/usr/bin/env bash
set -e

# Resolve repository root directory regardless of current working directory
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -x "$APP_DIR/.venv/bin/python" ]; then
    PYTHON="$APP_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "[!] Python 3 not found." >&2
    exit 1
fi

exec "$PYTHON" "$APP_DIR/main.py" "$@"

#!/usr/bin/env bash
set -e

# Resolve repository root directory regardless of current working directory
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ensure user-local Tk/Tcl libraries are available if present
if [ -d "$HOME/.local/lib/tk8.6" ]; then
    export TK_LIBRARY="${TK_LIBRARY:-$HOME/.local/lib/tk8.6}"
fi
if [ -d "$HOME/.local/lib" ]; then
    export LD_LIBRARY_PATH="$HOME/.local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

if [ -x "$APP_DIR/.venv/bin/python" ]; then
    PYTHON="$APP_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "[!] Python 3 not found." >&2
    exit 1
fi

exec "$PYTHON" "$APP_DIR/main.py" "$@"


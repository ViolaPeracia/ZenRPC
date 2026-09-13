#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

echo "[1/3] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "  [!] Python 3 not found. Please install Python 3.8+."
    exit 1
fi
echo "  [OK] $(python3 --version)"

echo "[2/3] Setting up environment and dependencies..."
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    VENV_PYTHON="$VIRTUAL_ENV/bin/python"
    echo "  [OK] Using active virtual environment: $VIRTUAL_ENV"
else
    VENV_DIR="$APP_DIR/.venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo "  [*] Creating virtual environment in .venv..."
        if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
            echo "  [!] Failed to create virtual environment using 'python3 -m venv'."
            echo "      Please ensure python3-venv is installed:"
            echo "        Debian/Ubuntu: sudo apt install python3-venv"
            echo "        Fedora:        sudo dnf install python3-virtualenv"
            echo "        Arch/CachyOS:  sudo pacman -S python"
            exit 1
        fi
        echo "  [OK] Created virtual environment (.venv)."
    else
        echo "  [OK] Existing virtual environment found (.venv)."
    fi
    VENV_PYTHON="$VENV_DIR/bin/python"
fi

if ! "$VENV_PYTHON" -m pip --version &>/dev/null; then
    echo "  [*] Bootstrapping pip..."
    "$VENV_PYTHON" -m ensurepip --default-pip
fi

echo "  [*] Installing dependencies from requirements.txt..."
"$VENV_PYTHON" -m pip install -r requirements.txt
echo "  [OK] Dependencies installed successfully."

echo "[3/3] Setting up configuration..."
if [ ! -f "config.json" ]; then
    cp config.example.json config.json
    echo "  [OK] Created config.json from template."
else
    echo "  [OK] config.json already exists."
fi

chmod +x run.sh

echo ""
echo "========================================================"
echo " Installation complete!"
echo " 1. Edit config.json and enter your Discord client_id."
echo " 2. Run with: ./run.sh"
echo "    (or: source .venv/bin/activate && python3 main.py)"
echo "========================================================"
echo ""

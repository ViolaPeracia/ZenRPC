#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "[1/3] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "  [!] Python 3 not found. Please install Python 3.8+."
    exit 1
fi
echo "  [OK] $(python3 --version)"

echo "[2/3] Installing dependencies..."
python3 -m pip install -r requirements.txt

echo "[3/3] Setting up configuration..."
if [ ! -f "config.json" ]; then
    cp config.example.json config.json
    echo "  [OK] Created config.json from template."
else
    echo "  [OK] config.json already exists."
fi

echo ""
echo "========================================================"
echo " Installation complete!"
echo " 1. Edit config.json and enter your Discord client_id."
echo " 2. Run with: python3 main.py"
echo "========================================================"
echo ""

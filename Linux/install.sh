#!/bin/bash
set -e

echo ""
echo "================================"
echo " Discord RPC Watcher - Linux"
echo "================================"
echo ""

# ── Check Python ──────────────────────────────────────────────────────────────
echo "[1/4] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "  [!] Python3 not found. Installing..."
    sudo apt update && sudo apt install -y python3 python3-pip
fi
echo "  [OK] $(python3 --version)"

# ── Install system dependencies ───────────────────────────────────────────────
echo "[2/4] Installing system dependencies..."

# xdotool — detect active window on X11
if ! command -v xdotool &>/dev/null; then
    echo "  [..] Installing xdotool..."
    sudo apt install -y xdotool
fi
echo "  [OK] xdotool"

# AppIndicator3 for GNOME tray (optional, falls back to pystray)
sudo apt install -y gir1.2-appindicator3-0.1 python3-gi 2>/dev/null || true
echo "  [OK] AppIndicator3 (optional)"

# ── Install Python packages ───────────────────────────────────────────────────
echo "[3/4] Installing Python packages..."
pip3 install -r requirements.txt --break-system-packages -q
echo "  [OK] All packages installed"

# ── Check config ──────────────────────────────────────────────────────────────
echo "[4/4] Checking config..."
if [ ! -f "config.json" ]; then
    python3 main.py &
    sleep 1
    kill %1 2>/dev/null || true
fi

if grep -q "YOUR_CLIENT_ID_HERE" config.json 2>/dev/null; then
    echo "  [!] Remember to set client_id in config.json before running!"
    echo "      nano config.json"
fi

echo ""
echo "================================"
echo " Done! Run with: python3 main.py"
echo "================================"
echo ""

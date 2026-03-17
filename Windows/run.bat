@echo off
title Discord RPC Watcher

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python not install. Download at: https://python.org
    pause
    exit
)

echo install lib...
pip install -r requirements.txt -q

echo Starting Discord RPC Watcher...
start pythonw main.py

echo [v] Started! Check tray icon at the bottom right corner of your screen.
timeout /t 3 >nul

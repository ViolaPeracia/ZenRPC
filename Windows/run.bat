@echo off
title Discord RPC Watcher

echo Kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python chua duoc cai dat. Tai tai: https://python.org
    pause
    exit
)

echo Cai thu vien...
pip install -r requirements.txt -q

echo Khoi dong Discord RPC Watcher...
start pythonw main.py

echo [v] Da khoi dong! Kiem tra tray icon goc duoi ben phai man hinh.
timeout /t 3 >nul

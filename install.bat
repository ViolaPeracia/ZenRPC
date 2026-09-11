@echo off
title Discord RPC Watcher - Installer
cd /d "%~dp0"

echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python is not installed or not on PATH.
    echo     Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [2/3] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [!] Failed to install dependencies.
    pause
    exit /b 1
)

echo [3/3] Setting up configuration...
if not exist "config.json" (
    copy "config.example.json" "config.json" >nul
    echo [OK] Created config.json from template.
) else (
    echo [OK] config.json already exists.
)

echo.
echo ========================================================
echo  Installation complete!
echo  1. Edit config.json and enter your Discord client_id.
echo  2. Run run.bat to start Discord RPC Watcher.
echo ========================================================
echo.
pause

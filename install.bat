@echo off
setlocal enabledelayedexpansion
title ZenRPC - Installer
cd /d "%~dp0"

echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [!] Python is not installed or not on PATH.
    echo       Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo   [OK] %%v

echo [2/3] Setting up environment and dependencies...

set "VENV_PYTHON="

:: Check active virtual environment first
if defined VIRTUAL_ENV (
    if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
        set "VENV_PYTHON=%VIRTUAL_ENV%\Scripts\python.exe"
        echo   [OK] Using active virtual environment: %VIRTUAL_ENV%
    )
)

:: If not in an active venv, check or create project .venv
if not defined VENV_PYTHON (
    if not exist ".venv\Scripts\python.exe" (
        echo   [*] Creating virtual environment in .venv...
        python -m venv --system-site-packages .venv >nul 2>&1
        if errorlevel 1 (
            python -m venv .venv
        )
    )
    if exist ".venv\Scripts\python.exe" (
        set "VENV_PYTHON=.venv\Scripts\python.exe"
        echo   [OK] Using virtual environment (.venv)
    ) else (
        set "VENV_PYTHON=python"
        echo   [!] Could not create .venv; falling back to system Python.
    )
)

:: Ensure pip is installed in the target Python environment
"%VENV_PYTHON%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   [*] Bootstrapping pip...
    "%VENV_PYTHON%" -m ensurepip --default-pip >nul 2>&1
)

echo   [*] Installing dependencies from requirements.txt...
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo   [!] Failed to install dependencies.
    pause
    exit /b 1
)
echo   [OK] Dependencies installed successfully.

echo [3/3] Setting up configuration...
if not exist "config.json" (
    copy "config.example.json" "config.json" >nul
    echo   [OK] Created config.json from template.
) else (
    echo   [OK] config.json already exists.
)

echo.
echo ========================================================
echo  Installation complete!
echo  1. Edit config.json and enter your Discord client_id.
echo  2. Run run.bat to start ZenRPC.
echo     (or: .venv\Scripts\activate ^&^& python main.py)
echo ========================================================
echo.
pause

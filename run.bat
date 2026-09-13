@echo off
title ZenRPC
cd /d "%~dp0"

if defined VIRTUAL_ENV (
    if exist "%VIRTUAL_ENV%\Scripts\pythonw.exe" (
        start "" "%VIRTUAL_ENV%\Scripts\pythonw.exe" main.py %*
        exit /b 0
    )
)

if exist .venv\Scripts\pythonw.exe (
    start "" .venv\Scripts\pythonw.exe main.py %*
) else (
    start "" pythonw main.py %*
)

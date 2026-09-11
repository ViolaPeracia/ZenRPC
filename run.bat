@echo off
title Discord RPC Watcher
cd /d "%~dp0"

if exist .venv\Scripts\pythonw.exe (
    start "" .venv\Scripts\pythonw.exe main.py
) else (
    start "" pythonw main.py
)

@echo off
title Discord RPC Watcher - Installer

echo.
echo  ================================
echo   Discord RPC Watcher Installer
echo  ================================
echo.

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python not install. Direct to Python...
    start https://www.python.org/downloads/
    echo  [!] After Installed Python, Rerun this file .
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo  [OK] %PY_VER%

echo [2/4] Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo  [!] pip not install. Installing...
    python -m ensurepip --upgrade
)
echo  [OK] pip ready

echo [3/4] Upgrade pip...
python -m pip install --upgrade pip -q
echo  [OK] pip upgraded

echo [4/4] Installing Lib...
echo.

echo  -- pypresence
python -m pip install "pypresence>=4.3.0" -q
if errorlevel 1 ( echo  [!] Error when Installing pypresence ) else ( echo  [OK] pypresence )

echo  -- psutil
python -m pip install "psutil>=5.9.0" -q
if errorlevel 1 ( echo  [!] Error when Installing psutil ) else ( echo  [OK] psutil )

echo  -- pywin32
python -m pip install "pywin32>=306" -q
if errorlevel 1 ( echo  [!] Error when Installing pywin32 ) else ( echo  [OK] pywin32 )

echo  -- pystray
python -m pip install "pystray>=0.19.5" -q
if errorlevel 1 ( echo  [!] Error when Installing pystray ) else ( echo  [OK] pystray )

echo  -- Pillow
python -m pip install "Pillow>=10.0.0" -q
if errorlevel 1 ( echo  [!] Error when Installing Pillow ) else ( echo  [OK] Pillow )

echo.
echo  ================================
echo   Install successful!
echo   Run run.bat to start.
echo  ================================
echo.
pause

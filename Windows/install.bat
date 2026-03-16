@echo off
title Discord RPC Watcher - Installer

echo.
echo  ================================
echo   Discord RPC Watcher Installer
echo  ================================
echo.

echo [1/4] Kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python chua duoc cai. Dang mo trang tai...
    start https://www.python.org/downloads/
    echo  [!] Sau khi cai Python xong, chay lai file nay.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo  [OK] %PY_VER%

echo [2/4] Kiem tra pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo  [!] pip chua co. Dang cai...
    python -m ensurepip --upgrade
)
echo  [OK] pip san sang

echo [3/4] Nang cap pip...
python -m pip install --upgrade pip -q
echo  [OK] pip da duoc nang cap

echo [4/4] Cai cac thu vien...
echo.

echo  -- pypresence
python -m pip install "pypresence>=4.3.0" -q
if errorlevel 1 ( echo  [!] Loi khi cai pypresence ) else ( echo  [OK] pypresence )

echo  -- psutil
python -m pip install "psutil>=5.9.0" -q
if errorlevel 1 ( echo  [!] Loi khi cai psutil ) else ( echo  [OK] psutil )

echo  -- pywin32
python -m pip install "pywin32>=306" -q
if errorlevel 1 ( echo  [!] Loi khi cai pywin32 ) else ( echo  [OK] pywin32 )

echo  -- pystray
python -m pip install "pystray>=0.19.5" -q
if errorlevel 1 ( echo  [!] Loi khi cai pystray ) else ( echo  [OK] pystray )

echo  -- Pillow
python -m pip install "Pillow>=10.0.0" -q
if errorlevel 1 ( echo  [!] Loi khi cai Pillow ) else ( echo  [OK] Pillow )

echo.
echo  ================================
echo   Cai dat hoan tat!
echo   Chay run.bat de bat dau.
echo  ================================
echo.
pause

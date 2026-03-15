@echo off
title VMlaunch — Build EXE
color 0A
cls

echo.
echo  =========================================
echo   VMlaunch  ^>  Windows EXE Builder
echo  =========================================
echo.

:: ── Make sure we run from the script's own folder ────────────────────────────
cd /d "%~dp0"

:: ── Step 1: Python ───────────────────────────────────────────────────────────
echo  [1/4]  Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python not found on PATH.
    echo.
    echo  Fix:
    echo    1. Go to https://www.python.org/downloads/
    echo    2. Download and run the installer
    echo    3. Tick "Add Python to PATH"  ^<-- important!
    echo    4. Re-run this script
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo         %%v  found
echo.

:: ── Step 2: pip ──────────────────────────────────────────────────────────────
echo  [2/4]  Checking pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] pip not available.  Try:  python -m ensurepip
    pause
    exit /b 1
)
echo         pip  OK
echo.

:: ── Step 3: PyInstaller ──────────────────────────────────────────────────────
echo  [3/4]  Installing PyInstaller  (skip if already installed)...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo  [ERROR] Could not install PyInstaller.
    echo  Try running this script as Administrator.
    pause
    exit /b 1
)
echo         PyInstaller  OK
echo.

:: ── Check vmlaunch.py is here ────────────────────────────────────────────────
if not exist "vmlaunch.py" (
    echo  [ERROR] vmlaunch.py not found in this folder.
    echo.
    echo  Make sure build.bat and vmlaunch.py are in the SAME folder.
    echo  Current folder:  %CD%
    echo.
    pause
    exit /b 1
)

:: ── Step 4: Build ────────────────────────────────────────────────────────────
echo  [4/4]  Building VMlaunch.exe ...
echo         (this takes about 30-60 seconds, please wait)
echo.

pyinstaller --onefile --windowed --name VMlaunch --clean vmlaunch.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed.
    echo  Check the messages above for clues.
    echo  Common fix: run this script as Administrator.
    echo.
    pause
    exit /b 1
)

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  =========================================
echo   SUCCESS!
echo  =========================================
echo.
echo   Your EXE is ready at:
echo   %CD%\dist\VMlaunch.exe
echo.
echo   You can copy VMlaunch.exe anywhere and run it.
echo   No Python or anything else needed on the target PC.
echo  =========================================
echo.

:: Open the dist folder automatically
explorer "%CD%\dist"

pause

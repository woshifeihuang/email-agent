@echo off
cd /d "%~dp0"

echo ============================================
echo  Email Agent Plugin - one-click setup
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist .venv (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
)

echo [2/3] Installing dependencies...
.venv\Scripts\python -m pip install --disable-pip-version-check -q -r requirements.txt

echo [3/3] Running setup wizard...
.venv\Scripts\python setup.py

echo.
echo Setup done. Open this folder in Claude Code to start using it.
pause

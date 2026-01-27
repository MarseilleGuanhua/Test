@echo off
setlocal
title UOP CarbonTrace Launcher

echo ==================================================
echo         UOP CarbonTrace - Graph Digitizer
echo ==================================================

REM 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed.
    echo Please install Python from the Software Center or python.org.
    pause
    exit /b
)

REM 2. Setup Environment
if not exist "venv_carbon" (
    echo [INFO] Initializing CarbonTrace Environment...
    python -m venv venv_carbon
    
    echo [INFO] Activating...
    call venv_carbon\Scripts\activate
    
    echo [INFO] Installing dependencies...
    pip install PySide6 matplotlib numpy
    
    if %errorlevel% neq 0 (
        echo [ERROR] Installation failed. Check internet/VPN.
        pause
        exit /b
    )
    echo [SUCCESS] Ready!
) else (
    echo [INFO] Loading Environment...
    call venv_carbon\Scripts\activate
)

REM 3. Run
echo [INFO] Starting Application...
python UOP_CarbonTrace.py

echo [INFO] Session ended.
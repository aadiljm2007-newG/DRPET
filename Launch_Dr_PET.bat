@echo off
SETLOCAL
TITLE Dr. PET - Behavioral Intelligence System
COLOR 0B

:: Dr. PET Header
echo.
echo   [96m  _____   _____    _____  ______ _______  [0m
echo   [96m ^|  __ \ ^|  __ \  ^|  __ \^|  ____^|__   __^| [0m
echo   [96m ^| ^|  ^| ^|^| ^|__) ^| ^| ^|__) ^| ^|__     ^| ^|    [0m
echo   [96m ^| ^|  ^| ^|^|  _  /  ^|  ___/^|  __^|    ^| ^|    [0m
echo   [96m ^| ^|__^| ^|^| ^| \ \  ^| ^|    ^| ^|____   ^| ^|    [0m
echo   [96m ^|_____/ ^|_^|  \_\ ^|_^|    ^|______^|  ^|_^|    [0m
echo.
echo   -------------------------------------------------------
echo           PROJECT: DR. PET BEHAVIOR INTELLIGENCE
echo   -------------------------------------------------------
echo.

:: 1. Navigate to the root folder
cd /d "%~dp0"

:: 2. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [91m[ERROR] Python is not installed or not in PATH! [0m
    pause
    exit /b
)

:: 3. Check for Virtual Environment
set "PYTHON_EXE=python"
if exist venv\Scripts\python.exe (
    echo   [92m[INFO] [0m Virtual environment found.
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else if exist .venv\Scripts\python.exe (
    echo   [92m[INFO] [0m .venv found.
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

:: 4. Start Backend Service
echo   [94m[SYSTEM] [0m Starting FastAPI Backend...
echo   [94m[SYSTEM] [0m Waiting for models and database to initialize...
:: Killing any stuck python processes from previous failed runs to clear database locks
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Dr. PET Backend Server*" >nul 2>&1
start "Dr. PET Backend Server" cmd /k "TITLE Dr. PET Backend Server && COLOR 07 && "%PYTHON_EXE%" backend\main.py"

:: 5. Wait for initialization
timeout /t 6 > nul

:: 6. Open Frontend Dashboard
echo   [94m[SYSTEM] [0m Initialization sequence complete. Opening Dashboard...
start http://localhost:8000

echo.
echo   =======================================================
echo     SUCCESS: Dr. PET is now running! 
echo   =======================================================
echo.
echo   Note: If the backend window shows a 'RuntimeError', 
echo   please close all terminal windows and try again.
echo.
pause

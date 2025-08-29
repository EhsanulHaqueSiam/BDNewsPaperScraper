@echo off
REM Enhanced spider runner for Windows - Batch file wrapper
REM Usage: run_spiders_optimized.bat [arguments...]
REM This file simply calls the Python script with all arguments

echo Starting BDNewsPaper Scraper (Windows)
echo.

python run_spiders_optimized.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Error occurred. Exit code: %ERRORLEVEL%
    echo.
    echo Troubleshooting tips:
    echo 1. Make sure Python is installed and in PATH
    echo 2. Make sure UV is installed: pip install uv
    echo 3. Make sure dependencies are installed: uv sync
    echo 4. Check internet connection
    echo.
    pause
    exit /b %ERRORLEVEL%
) else (
    echo.
    echo ✅ Spider run completed successfully!
    echo.
)
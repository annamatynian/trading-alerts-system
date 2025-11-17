@echo off
REM Windows batch script for running all tests
REM Usage: test_all.bat

echo ================================================================================
echo                    TESTING AUTHENTICATION SYSTEM
echo ================================================================================
echo.

REM Run the Python test script
python test_all.py

REM Check if python command exists
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Python not found in PATH
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo OR
    echo Make sure Python is added to your PATH environment variable
    echo.
    pause
    exit /b 1
)

echo.
pause

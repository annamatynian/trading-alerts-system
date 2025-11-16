@echo off
REM Запуск мультипользовательской версии Trading Alert System

echo ========================================
echo 🚀 Trading Alert System - MULTIUSER TEST
echo ========================================
echo.
echo 🎯 Testing Variant 1B: User ID Filter
echo.
echo Changes:
echo   ✅ User ID is now REQUIRED
echo   ✅ Filter by User ID added
echo   ✅ View your own signals only
echo.
echo ========================================
echo.

REM Переходим в директорию скрипта
cd /d "%~dp0"

REM Проверяем виртуальное окружение
if not exist venv (
    echo ❌ Virtual environment not found!
    echo Creating virtual environment...
    python -m venv venv
    echo ✅ Virtual environment created
    echo.
    echo Installing dependencies...
    call venv\Scripts\activate
    pip install -r requirements.txt
    echo ✅ Dependencies installed
) else (
    echo ✅ Virtual environment found
    call venv\Scripts\activate
)

echo.
echo 📦 Checking dependencies...
pip install gradio pandas --quiet
echo ✅ Gradio ready
echo.

echo 🌐 Starting Gradio Web Interface...
echo.
echo 📝 Interface will be available at: http://localhost:7860
echo.
echo 🧪 Test Checklist:
echo   1. Try creating signal WITHOUT User ID (should fail)
echo   2. Create signal with User ID: anna
echo   3. Create signal with User ID: john
echo   4. Filter by User ID: anna (should see only anna's signals)
echo   5. Filter by User ID: john (should see only john's signals)
echo   6. Click "Refresh All" (should see all signals)
echo.
echo See TEST_MULTIUSER.md for detailed test instructions
echo.
echo ========================================
echo.

python app.py

echo.
echo ========================================
echo Gradio stopped
echo ========================================
pause

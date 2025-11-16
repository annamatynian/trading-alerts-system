@echo off
REM Запуск Gradio Web Interface для Trading Alert System

echo ========================================
echo 🚀 Trading Signal System - Gradio UI
echo ========================================
echo.

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
echo Interface will be available at: http://localhost:7860
echo.

python gradio_app.py

pause

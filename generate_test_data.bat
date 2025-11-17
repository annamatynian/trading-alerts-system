@echo off
REM ========================================
REM ЁЯЪА Generate Test Signals for Anna & Tomas
REM ========================================

echo.
echo ========================================
echo ЁЯЪА ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ
echo ========================================
echo.
echo Этот скрипт создаст тестовые сигналы для:
echo   - anna (4 сигнала)
echo   - tomas (5 сигналов)
echo.
echo ========================================
echo.

REM Активируем виртуальное окружение если есть
if exist venv\Scripts\activate.bat (
    echo ✅ Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  Virtual environment not found, using system Python
)

REM Проверяем .env
if not exist .env (
    echo.
    echo ❌ ERROR: .env file not found!
    echo    Please copy .env.example to .env and configure it
    echo.
    pause
    exit /b 1
)

echo.
echo ЁЯЪл Generating test signals...
echo.

REM Запускаем скрипт генерации
python generate_test_signals.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✅ SUCCESS!
    echo ========================================
    echo.
    echo Тестовые данные созданы!
    echo Теперь можете тестировать фильтр по User ID
    echo.
) else (
    echo.
    echo ========================================
    echo ❌ FAILED
    echo ========================================
    echo.
    echo Проверьте логи выше для деталей
    echo.
)

pause

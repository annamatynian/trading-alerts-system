@echo off
REM Простая проверка - есть ли незакоммиченные изменения

echo ========================================
echo 🔍 QUICK CHECK - Uncommitted Changes
echo ========================================
echo.

cd /d "%~dp0"

echo Checking for modified files...
git diff --name-only
echo.

echo Checking for untracked files...
git ls-files --others --exclude-standard
echo.

echo ========================================
echo 📊 STATUS:
echo ========================================
git status --short
echo.

if not exist "MULTIUSER_CHANGES.md" (
    echo.
    echo ⚠️  MULTIUSER_CHANGES.md NOT found in Git!
    echo This means our new files are NOT committed yet.
) else (
    echo ✅ MULTIUSER_CHANGES.md exists
)

echo.
echo ========================================
echo 🎯 RESULT:
echo ========================================
echo.

REM Проверка изменений в app.py
findstr /C:"User ID (Required)" app.py >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ app.py has our changes "User ID (Required)"
    echo.
    echo Now checking if it's committed...
    git diff --quiet app.py
    if %errorlevel% equ 0 (
        echo ✅ app.py changes ARE committed
    ) else (
        echo ⚠️  app.py changes are NOT committed yet!
    )
) else (
    echo ❌ app.py doesn't have our changes!
)

echo.
pause

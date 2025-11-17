@echo off
REM Быстрая проверка - только секретные файлы

echo ========================================
echo 🚨 SECURITY CHECK - Secrets in Commit
echo ========================================
echo.

cd /d "%~dp0"

echo Checking last commit for sensitive files...
echo.

echo [1] Checking for secret-*.json files:
git show --name-only --pretty=format:"" HEAD | findstr /I "secret.*\.json" > nul
if %errorlevel% equ 0 (
    echo    ❌ FOUND! SECRET JSON FILES IN COMMIT!
    git show --name-only --pretty=format:"" HEAD | findstr /I "secret.*\.json"
    set SECRETS_FOUND=1
) else (
    echo    ✅ No secret-*.json files
)
echo.

echo [2] Checking for .env file:
git show --name-only --pretty=format:"" HEAD | findstr /I "^\.env$" > nul
if %errorlevel% equ 0 (
    echo    ⚠️  FOUND! .env file in commit
    echo    Check if it contains real credentials!
    set SECRETS_FOUND=1
) else (
    echo    ✅ No .env file
)
echo.

echo [3] Checking for .env.example:
git show --name-only --pretty=format:"" HEAD | findstr /I "\.env\.example" > nul
if %errorlevel% equ 0 (
    echo    ℹ️  .env.example found (this is OK if no real secrets)
) else (
    echo    ✅ No .env.example
)
echo.

echo [4] Checking for api_key or credentials in filenames:
git show --name-only --pretty=format:"" HEAD | findstr /I "credentials api_key apikey" > nul
if %errorlevel% equ 0 (
    echo    ⚠️  Files with 'credentials' or 'api_key' in name:
    git show --name-only --pretty=format:"" HEAD | findstr /I "credentials api_key apikey"
    set SECRETS_FOUND=1
) else (
    echo    ✅ No credential-related filenames
)
echo.

echo ========================================
echo 📊 RESULT:
echo ========================================
if defined SECRETS_FOUND (
    echo.
    echo ❌❌❌ POTENTIAL SECRETS FOUND! ❌❌❌
    echo.
    echo 🚨 IMMEDIATE ACTION REQUIRED:
    echo.
    echo 1. Check if these files contain REAL secrets
    echo 2. If YES - we need to remove from Git history NOW
    echo 3. Rotate all API keys and credentials
    echo.
    echo Type 'check' to see detailed guide
    set /p ACTION="Do you see secret files above? (yes/no): "
    if /i "!ACTION!" EQU "yes" (
        echo.
        echo Opening emergency guide...
        notepad EMERGENCY_SECRETS_REMOVAL.md 2>nul || echo Run: git_remove_secrets.bat
    )
) else (
    echo.
    echo ✅✅✅ NO SECRETS DETECTED! ✅✅✅
    echo.
    echo Your commit looks safe!
    echo You can proceed with Claude GitHub.
)
echo.
echo ========================================

pause

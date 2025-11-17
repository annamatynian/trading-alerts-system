@echo off
REM Проверка последнего коммита - что туда попало

echo ========================================
echo 🔍 Last Commit - Files Check
echo ========================================
echo.

cd /d "%~dp0"

echo Last commit message:
echo ----------------------------------------
git log -1 --pretty=format:"%%s%%n%%n%%b"
echo.
echo ----------------------------------------
echo.

echo Files in last commit:
echo ----------------------------------------
git show --name-only --pretty=format:"" HEAD
echo ----------------------------------------
echo.

echo ========================================
echo 🚨 CHECKING FOR SENSITIVE FILES:
echo ========================================
echo.

git show --name-only --pretty=format:"" HEAD | findstr /I "secret.*\.json"
if %errorlevel% equ 0 (
    echo.
    echo ⚠️⚠️⚠️ WARNING! ⚠️⚠️⚠️
    echo SECRET JSON FILES FOUND IN COMMIT!
    echo.
    echo 🚨 ACTION REQUIRED:
    echo 1. Remove secrets from GitHub immediately
    echo 2. Rotate all API keys and credentials
    echo 3. Use 'git filter-branch' or BFG to remove from history
    echo.
) else (
    echo ✅ No obvious secret files found
)

echo.
git show --name-only --pretty=format:"" HEAD | findstr /I "\.env"
if %errorlevel% equ 0 (
    echo.
    echo ⚠️ .env file found in commit!
    echo Check if it contains real credentials!
) else (
    echo ✅ No .env file in commit
)

echo.
echo ========================================
pause

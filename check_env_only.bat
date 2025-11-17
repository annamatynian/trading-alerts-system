@echo off
echo Checking if .env (real secrets) is in commit...
cd /d "%~dp0"
git show --name-only --pretty=format:"" HEAD | findstr /X "\.env" > nul
if %errorlevel% equ 0 (
    echo ❌ DANGER! Real .env file is in commit!
) else (
    echo ✅ Real .env file is NOT in commit
)
pause

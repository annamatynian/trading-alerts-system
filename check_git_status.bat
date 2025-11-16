@echo off
REM Проверка статуса Git репозитория

echo ========================================
echo 📊 Git Status Check
echo ========================================
echo.

cd /d "%~dp0"

echo 🔍 Checking Git status...
echo.

git status

echo.
echo ========================================
echo 📝 Summary:
echo ========================================
echo.

echo Untracked files: Files that are NOT in Git yet
echo Modified files: Files changed but NOT committed
echo Staged files: Files ready to commit
echo.

echo ========================================
echo 📋 Quick Commands:
echo ========================================
echo.
echo To see detailed changes:
echo   git diff
echo.
echo To add ALL changes:
echo   git add .
echo.
echo To commit changes:
echo   git commit -m "Add multiuser support (Variant 1B)"
echo.
echo To push to GitHub:
echo   git push
echo.
echo ========================================

pause

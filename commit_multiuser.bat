@echo off
REM Коммит изменений для мультипользовательской поддержки

echo ========================================
echo 📦 Git Commit - Multiuser Support
echo ========================================
echo.

cd /d "%~dp0"

echo 🔍 Current Git status:
echo.
git status --short
echo.

echo ========================================
echo 📝 Files to be committed:
echo ========================================
echo.
echo Modified:
echo   - app.py (User ID filter + validation)
echo.
echo New files:
echo   - MULTIUSER_CHANGES.md
echo   - TEST_MULTIUSER.md
echo   - run_multiuser_test.bat
echo   - check_git_status.bat
echo   - commit_multiuser.bat
echo.

set /p CONFIRM="Do you want to commit these changes? (Y/N): "
if /i "%CONFIRM%" NEQ "Y" (
    echo.
    echo ❌ Commit cancelled
    pause
    exit /b
)

echo.
echo 📦 Adding files to Git...
git add app.py
git add MULTIUSER_CHANGES.md
git add TEST_MULTIUSER.md
git add run_multiuser_test.bat
git add check_git_status.bat
git add commit_multiuser.bat

echo.
echo ✅ Files staged
echo.

echo 💾 Committing changes...
git commit -m "feat: Add multiuser support with User ID filter (Variant 1B)

- Make User ID required field with validation
- Add User ID column to signals table
- Add filter by User ID in View Signals tab
- Update get_signals_table() to support filtering
- Add comprehensive test documentation
- Create test scripts for multiuser functionality

This allows multiple users to:
- Create signals with their own User ID
- Filter and view only their own signals
- Prepare for per-user Pushover notifications"

echo.
echo ✅ Changes committed!
echo.

echo ========================================
echo 🚀 Next Steps:
echo ========================================
echo.
echo 1. Push to GitHub:
echo    git push
echo.
echo 2. Or push to specific branch:
echo    git push origin main
echo.

set /p PUSH="Do you want to push to GitHub now? (Y/N): "
if /i "%PUSH%" EQU "Y" (
    echo.
    echo 🚀 Pushing to GitHub...
    git push
    echo.
    echo ✅ Pushed to GitHub!
) else (
    echo.
    echo ⏸️  Push skipped. Run 'git push' manually when ready.
)

echo.
echo ========================================
echo ✅ Done!
echo ========================================
pause

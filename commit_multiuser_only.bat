@echo off
REM Коммит ТОЛЬКО мультипользовательских изменений

echo ========================================
echo 📦 Selective Commit - Multiuser Only
echo ========================================
echo.

cd /d "%~dp0"

echo Files to commit:
echo.
echo Modified:
echo   тЬЕ app.py
echo.
echo New files (multiuser-related):
echo   тЬЕ MULTIUSER_CHANGES.md
echo   тЬЕ TEST_MULTIUSER.md
echo   тЬЕ run_multiuser_test.bat
echo   тЬЕ GIT_COMMIT_GUIDE.md
echo   тЬЕ check_git_status.bat
echo   тЬЕ commit_multiuser.bat
echo   тЬЕ full_git_diagnostic.bat
echo   тЬЕ quick_check.bat
echo.
echo All other untracked files will be IGNORED for now.
echo.

set /p CONFIRM="Commit these multiuser files? (Y/N): "
if /i "%CONFIRM%" NEQ "Y" (
    echo ❌ Cancelled
    pause
    exit /b
)

echo.
echo 📦 Adding files...
git add app.py
git add MULTIUSER_CHANGES.md
git add TEST_MULTIUSER.md
git add run_multiuser_test.bat
git add GIT_COMMIT_GUIDE.md
git add check_git_status.bat
git add commit_multiuser.bat
git add full_git_diagnostic.bat
git add quick_check.bat

echo тЬЕ Files staged
echo.

echo 💾 Committing...
git commit -m "feat: Add multiuser support with User ID filter (Variant 1B)

Changes:
- Make User ID required field with validation in create_signal
- Add User ID column to signals display table
- Add filter by User ID in View Signals tab with dual buttons
- Update get_signals_table() to support optional user_id filtering
- Add comprehensive test documentation (TEST_MULTIUSER.md)
- Add diagnostic and commit helper scripts

Features:
- Multiple users can create signals with unique User IDs
- Each user can filter to see only their own signals
- Prepared for per-user Pushover notifications in Lambda

Test files:
- run_multiuser_test.bat - launch app for testing
- full_git_diagnostic.bat - complete Git status check
- GIT_COMMIT_GUIDE.md - commit workflow documentation"

if %errorlevel% equ 0 (
    echo.
    echo тЬЕ Commit successful!
    echo.
    
    set /p PUSH="Push to GitHub now? (Y/N): "
    if /i "!PUSH!" EQU "Y" (
        echo.
        echo 🚀 Pushing to GitHub...
        git push
        
        if %errorlevel% equ 0 (
            echo.
            echo тЬЕтЬЕтЬЕ SUCCESS! Changes pushed to GitHub!
            echo тЬЕ Ready for Claude GitHub!
        ) else (
            echo.
            echo тЪая╕П Push failed. You may need to:
            echo   - Set upstream: git push -u origin clean-branch
            echo   - Or manually push later
        )
    ) else (
        echo.
        echo тП╕яВП Push skipped. Run 'git push' when ready.
    )
) else (
    echo тЪая╕П Commit failed!
)

echo.
echo ========================================
pause

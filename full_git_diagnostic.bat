@echo off
REM Полная диагностика Git репозитория перед работой с Claude GitHub

echo ========================================
echo 🔍 FULL GIT DIAGNOSTIC
echo ========================================
echo.

cd /d "%~dp0"

echo 📁 Current Directory:
cd
echo.

echo ========================================
echo 1️⃣ Git Configuration
echo ========================================
echo.
echo Git User:
git config user.name
git config user.email
echo.

echo ========================================
echo 2️⃣ Remote Repository
echo ========================================
echo.
git remote -v
echo.

echo ========================================
echo 3️⃣ Current Branch
echo ========================================
echo.
git branch
echo.

echo ========================================
echo 4️⃣ Recent Commits (last 5)
echo ========================================
echo.
git log --oneline -5
echo.

echo ========================================
echo 5️⃣ Files Status (SHORT)
echo ========================================
echo.
git status --short
echo.

echo ========================================
echo 6️⃣ Detailed Status
echo ========================================
echo.
git status
echo.

echo ========================================
echo 7️⃣ Files NOT Committed (if any)
echo ========================================
echo.
echo Modified files:
git diff --name-only
echo.
echo Untracked files:
git ls-files --others --exclude-standard
echo.

echo ========================================
echo 8️⃣ Last Commit Details
echo ========================================
echo.
git log -1 --stat
echo.

echo ========================================
echo 📊 SUMMARY
echo ========================================
echo.

REM Проверяем есть ли незакоммиченные изменения
git diff-index --quiet HEAD --
if %errorlevel% equ 0 (
    echo ✅ WORKING TREE IS CLEAN
    echo ✅ All changes are committed
    echo ✅ Ready for Claude GitHub!
) else (
    echo ⚠️  YOU HAVE UNCOMMITTED CHANGES
    echo ⚠️  Run commit_multiuser.bat to commit
)
echo.

REM Проверяем есть ли unpushed коммиты
git diff --quiet HEAD @{u}
if %errorlevel% equ 0 (
    echo ✅ ALL COMMITS PUSHED TO GITHUB
) else (
    echo ⚠️  YOU HAVE UNPUSHED COMMITS
    echo ⚠️  Run: git push
)
echo.

echo ========================================
echo 🎯 NEXT STEPS
echo ========================================
echo.
echo If you see warnings above:
echo   1. Run: commit_multiuser.bat  (to commit)
echo   2. Run: git push              (to push to GitHub)
echo.
echo If everything is clean:
echo   ✅ You can start working with Claude GitHub!
echo.
echo ========================================

pause

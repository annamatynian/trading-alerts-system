@echo off
cd /d "%~dp0"

echo ============================================================
echo 🚀 GIT PUSH TO GITHUB - SIMPLE VERSION
echo ============================================================
echo.

echo Current directory: %CD%
echo.

echo 📦 Step 1: Git add all changes...
git add -A

echo.
echo 💾 Step 2: Git commit...
git commit -m "v4.0.1: Fixed logger initialization bug"

echo.
echo 🌐 Step 3: Git push to GitHub...
git push origin main

echo.
echo ============================================================
echo ✅ DONE! Check GitHub and Leapcell now!
echo ============================================================
echo.
echo GitHub: https://github.com/annamatynian/trading-alert-bot
echo Leapcell: https://trading-alert-bot-annamatynian7683-5yi72l08.leapcell.dev/kaithhealthcheck
echo.
pause

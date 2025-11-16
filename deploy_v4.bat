@echo off
echo ============================================================
echo 🚀 DEPLOYING VERSION 4.0 TO GITHUB
echo ============================================================
echo.

REM Добавляем только изменённые файлы (без секретов)
echo 📦 Adding changed files...
git add requirements.txt
git add src/check_alerts_cron.py
git add src/exchanges/binance.py
git add src/exchanges/coinbase.py
git add src/main.py
git add src/services/price_checker.py

echo.
echo 💾 Committing changes...
git commit -m "v4.0: Fixed terminology Alert→Signal, added version tracking, improved error handling"

echo.
echo 🌐 Pushing to GitHub...
git push origin main

echo.
echo ============================================================
echo ✅ DEPLOY COMPLETE!
echo ============================================================
echo.
echo Leapcell will automatically redeploy from GitHub.
echo Wait 1-2 minutes and check:
echo https://trading-alert-bot-annamatynian7683-5yi72l08.leapcell.dev/kaithhealthcheck
echo.
echo You should see: ✅ HEALTHCHECK ВЕРСИИ 4.0-FIXED-TERMINOLOGY
echo.
pause

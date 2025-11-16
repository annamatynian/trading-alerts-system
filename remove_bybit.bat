@echo off
echo ===================================
echo REMOVING BYBIT FROM SYSTEM
echo ===================================

cd /d "%~dp0"

echo.
echo Step 1: Deleting bybit.py...
git rm src\exchanges\bybit.py

echo.
echo Step 2: Adding modified files to git...
git add src\models\alert.py
git add src\utils\config.py
git add src\main.py
git add src\services\price_checker.py
git add src\exchanges\coinbase.py

echo.
echo Step 3: Committing changes...
git commit -m "Remove Bybit: Not needed (blocked in USA). Keep only Binance + Coinbase"

echo.
echo Step 4: Pushing to Railway...
git push

echo.
echo ===================================
echo DONE! Bybit removed!
echo ===================================
echo.
echo Changes:
echo   - Deleted: src/exchanges/bybit.py
echo   - Updated: src/models/alert.py (removed BYBIT enum)
echo   - Updated: src/utils/config.py (removed Bybit init)
echo   - Updated: src/main.py (removed Bybit import and init)
echo   - Updated: src/services/price_checker.py (added fallback support)
echo.
echo Now you have only 2 exchanges:
echo   1. Binance (fast, primary)
echo   2. Coinbase (reliable, fallback)
echo.
echo Wait 2-3 minutes for Railway to deploy...
echo Then check logs!
echo.
pause

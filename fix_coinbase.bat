@echo off
echo ===================================
echo FIXING COINBASE
echo ===================================

cd /d "%~dp0"

echo.
echo Adding coinbase.py to git...
git add src\exchanges\coinbase.py

echo.
echo Committing...
git commit -m "fix: Add async is_symbol_valid method to Coinbase"

echo.
echo Pushing to server...
git push

echo.
echo ===================================
echo DONE! Check logs in 2-3 minutes!
echo ===================================
pause

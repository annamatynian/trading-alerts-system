@echo off
echo ===================================
echo MAKING EXCHANGE OPTIONAL
echo ===================================

cd /d "%~dp0"

echo.
echo Adding changes to git...
git add src\services\sheets_reader.py

echo.
echo Committing...
git commit -m "feat: Make Exchange column optional - defaults to Binance with auto fallback to Coinbase"

echo.
echo Pushing to server...
git push

echo.
echo ===================================
echo DONE! 
echo ===================================
echo.
echo Now you can:
echo   1. Remove Exchange column from Google Sheets
echo   2. OR leave it empty
echo   3. System will use Binance by default
echo   4. Auto fallback to Coinbase if Binance fails
echo.
echo Wait 2-3 minutes for deployment...
pause

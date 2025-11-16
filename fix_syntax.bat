@echo off
echo ===================================
echo FIXING SYNTAX ERROR
echo ===================================

cd /d "%~dp0"

echo.
echo Adding fix to git...
git add src\services\sheets_reader.py

echo.
echo Committing...
git commit -m "fix: Close parenthesis in sheets_reader.py"

echo.
echo Pushing...
git push

echo.
echo ===================================
echo DONE! Fixed syntax error!
echo ===================================
pause

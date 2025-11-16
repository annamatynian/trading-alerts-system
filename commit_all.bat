@echo off
REM Коммит ВСЕХ изменений и новых файлов

echo ========================================
echo 📦 Commit ALL Changes
echo ========================================
echo.

cd /d "%~dp0"

echo тЪая╕П WARNING: This will commit ALL untracked files!
echo.
echo This includes:
echo   - Modified: app.py
echo   - All documentation files (.md)
echo   - All scripts (.bat, .py)
echo   - Lambda files
echo   - Config files
echo.
echo Total files: ~70+ files
echo.

set /p CONFIRM="Are you SURE you want to commit everything? (Y/N): "
if /i "%CONFIRM%" NEQ "Y" (
    echo ❌ Cancelled
    pause
    exit /b
)

echo.
echo 📦 Adding ALL files...
git add .

echo.
echo 💾 Committing...
git commit -m "feat: Add multiuser support and complete documentation

Major Changes:
- Multiuser support with User ID filter (Variant 1B)
- Complete system documentation
- Deployment guides (AWS Lambda, Hugging Face)
- Test scripts and diagnostic tools
- Lambda functions and configurations

Multiuser Features:
- Required User ID field with validation
- Filter signals by User ID
- Prepared for per-user notifications

Documentation:
- Architecture diagrams and guides
- Deployment instructions for multiple platforms
- Testing and troubleshooting guides
- API configuration examples"

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
            echo тЬЕтЬЕтЬЕ SUCCESS! All changes pushed to GitHub!
            echo тЬЕ Ready for Claude GitHub!
        ) else (
            echo.
            echo тЪая╕П Push failed. Try: git push -u origin clean-branch
        )
    )
) else (
    echo тЪая╕П Commit failed!
)

echo.
echo ========================================
pause

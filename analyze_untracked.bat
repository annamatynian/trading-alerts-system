@echo off
REM Анализ untracked файлов по категориям

echo ========================================
echo 📊 Untracked Files Analysis
echo ========================================
echo.

cd /d "%~dp0"

echo ┌─────────────────────────────────────┐
echo │ 🔧 INFRASTRUCTURE (Important)        │
echo └─────────────────────────────────────┘
git ls-files --others --exclude-standard | findstr /I "lambda_.*\.py build_.*\.py"
echo.

echo ┌─────────────────────────────────────┐
echo │ 📚 DOCUMENTATION (Keep)              │
echo └─────────────────────────────────────┘
git ls-files --others --exclude-standard | findstr /I "\.md$"
echo.

echo ┌─────────────────────────────────────┐
echo │ 🚀 DEPLOYMENT SCRIPTS (Important)    │
echo └─────────────────────────────────────┘
git ls-files --others --exclude-standard | findstr /I "deploy commit run" | findstr /I "\.bat$"
echo.

echo ┌─────────────────────────────────────┐
echo │ ⚙️ CONFIG FILES (Check carefully)   │
echo └─────────────────────────────────────┘
git ls-files --others --exclude-standard | findstr /I "\.json$ \.txt$ \.yaml$ Procfile runtime"
echo.

echo ┌─────────────────────────────────────┐
echo │ 🧪 TESTS (Important)                 │
echo └─────────────────────────────────────┘
git ls-files --others --exclude-standard | findstr /I "test.*\.py tests/"
echo.

echo ┌─────────────────────────────────────┐
echo │ ⚠️ SENSITIVE (DO NOT COMMIT!)       │
echo └─────────────────────────────────────┘
git ls-files --others --exclude-standard | findstr /I "secret.*\.json \.env"
echo.

echo ┌─────────────────────────────────────┐
echo │ 🗑️ JUNK (Can ignore)                │
echo └─────────────────────────────────────┘
git ls-files --others --exclude-standard | findstr /I "__pycache__ \.pyc \.zip"
echo.

echo ========================================
echo 💡 RECOMMENDATION:
echo ========================================
echo.
echo ✅ SHOULD commit:
echo    - Infrastructure files (lambda_*.py)
echo    - Documentation (.md files)
echo    - Deployment scripts (.bat files)
echo    - Config files (requirements_*.txt, etc)
echo    - Tests
echo.
echo ❌ SHOULD NOT commit:
echo    - secret-*.json files (contain credentials!)
echo    - .env file (if it has real secrets)
echo    - __pycache__ directories
echo    - .zip files (build artifacts)
echo.
echo ========================================

pause

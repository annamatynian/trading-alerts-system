@echo off
REM Коммит всех файлов КРОМЕ мультипользовательских

echo ========================================
echo 📦 Commit: Project Files (Before Multiuser)
echo ========================================
echo.

cd /d "%~dp0"

echo Adding all files EXCEPT multiuser files...
echo.

git add .
git reset HEAD MULTIUSER_CHANGES.md
git reset HEAD TEST_MULTIUSER.md
git reset HEAD run_multiuser_test.bat
git reset HEAD GIT_COMMIT_GUIDE.md
git reset HEAD check_git_status.bat
git reset HEAD commit_multiuser.bat
git reset HEAD commit_multiuser_only.bat
git reset HEAD commit_all.bat
git reset HEAD full_git_diagnostic.bat
git reset HEAD quick_check.bat

echo.
echo 💾 Committing project files...
git commit -m "docs: Add complete project documentation and Lambda functions

Added:
- Lambda functions (lambda_function.py, lambda_worker.py, lambda_reader.py)
- Deployment guides (AWS Lambda, Hugging Face, general deploy)
- Architecture documentation (diagrams, summaries)
- Build and test scripts
- Configuration files (IAM policies, requirements)
- Project documentation (quickstarts, guides, checklists)

Infrastructure:
- Lambda package builder
- Test suite setup
- Proxy configuration
- Sheets integration scripts

This commit includes all project files created before multiuser feature."

if %errorlevel% equ 0 (
    echo.
    echo ✅ Project files committed!
    echo.
    echo Now multiuser files are still unstaged.
    echo Run commit_multiuser_only.bat next.
) else (
    echo ❌ Commit failed!
)

echo.
pause

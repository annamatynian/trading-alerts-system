"""
Скрипт для запуска тестов
"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_storage/test_dynamodb_storage.py", "-v"],
    cwd=r"C:\Users\annam\Documents\DeFi-RAG-Project\trading_alert_system",
    capture_output=True,
    text=True
)

print(result.stdout)
print(result.stderr)
sys.exit(result.returncode)

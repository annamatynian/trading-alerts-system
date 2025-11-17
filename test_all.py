#!/usr/bin/env python3
"""
Единый тест-раннер для всей системы аутентификации

Запуск:
  Linux/Mac:   python3 test_all.py
  Windows:     python test_all.py
               OR
               test_all.bat
"""
import sys
import os
import subprocess
import time
from datetime import datetime

# Цвета для вывода
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text):
    """Красивый заголовок"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_section(text):
    """Секция"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'-'*len(text)}{Colors.END}")


def run_test_file(filename, description):
    """
    Запускает тестовый файл и возвращает результат

    Returns:
        (success: bool, output: str, duration: float)
    """
    if not os.path.exists(filename):
        return False, f"❌ File not found: {filename}", 0.0

    print(f"\n{Colors.BOLD}Running: {description}{Colors.END}")
    print(f"File: {filename}")
    print(f"Started at: {datetime.now().strftime('%H:%M:%S')}")

    start_time = time.time()

    try:
        # Запускаем тест
        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            timeout=60
        )

        duration = time.time() - start_time

        # Проверяем результат
        success = result.returncode == 0
        output = result.stdout + result.stderr

        # Печатаем результат
        if success:
            print(f"{Colors.GREEN}✅ PASSED{Colors.END} (in {duration:.2f}s)")
        else:
            print(f"{Colors.RED}❌ FAILED{Colors.END} (in {duration:.2f}s)")
            print(f"\n{Colors.YELLOW}Output:{Colors.END}")
            print(output[:500])  # Первые 500 символов

        return success, output, duration

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"{Colors.RED}❌ TIMEOUT{Colors.END} (>60s)")
        return False, "Test timed out after 60 seconds", duration

    except Exception as e:
        duration = time.time() - start_time
        print(f"{Colors.RED}❌ ERROR: {e}{Colors.END}")
        return False, str(e), duration


def check_dependencies():
    """Проверка зависимостей"""
    print_section("📦 Checking Dependencies")

    required = ['jwt', 'bcrypt', 'boto3', 'pydantic']
    missing = []

    for module in required:
        try:
            __import__(module)
            print(f"  {Colors.GREEN}✓{Colors.END} {module}")
        except ImportError:
            print(f"  {Colors.RED}✗{Colors.END} {module}")
            missing.append(module)

    if missing:
        print(f"\n{Colors.YELLOW}⚠️  Missing dependencies: {', '.join(missing)}{Colors.END}")
        print(f"{Colors.YELLOW}Install with: pip install PyJWT bcrypt boto3 pydantic{Colors.END}")
        return False

    print(f"\n{Colors.GREEN}✅ All dependencies installed{Colors.END}")
    return True


def check_syntax():
    """Проверка синтаксиса Python файлов"""
    print_section("🔍 Syntax Checks")

    files_to_check = [
        'src/services/auth_service.py',
        'src/storage/session_storage.py',
        'test_unit_auth.py',
        'test_production_features.py',
        'demo_auth.py'
    ]

    all_ok = True

    for filepath in files_to_check:
        if not os.path.exists(filepath):
            print(f"  {Colors.YELLOW}⊘{Colors.END} {filepath} (not found, skipping)")
            continue

        try:
            with open(filepath, 'r') as f:
                compile(f.read(), filepath, 'exec')
            print(f"  {Colors.GREEN}✓{Colors.END} {filepath}")
        except SyntaxError as e:
            print(f"  {Colors.RED}✗{Colors.END} {filepath} - Line {e.lineno}: {e.msg}")
            all_ok = False

    return all_ok


def main():
    """Главная функция"""

    print_header("TESTING AUTHENTICATION SYSTEM")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Platform: {sys.platform}")
    print(f"Python: {sys.version.split()[0]}")

    # Проверка зависимостей
    if not check_dependencies():
        print(f"\n{Colors.RED}❌ Please install missing dependencies first{Colors.END}")
        return 1

    # Проверка синтаксиса
    if not check_syntax():
        print(f"\n{Colors.RED}❌ Syntax errors found{Colors.END}")
        return 1

    print(f"\n{Colors.GREEN}✅ All syntax checks passed{Colors.END}")

    # Запуск тестов
    print_section("🧪 Running Test Suites")

    test_files = [
        ('test_unit_auth.py', 'Unit Tests (JWT, sessions, auth flow)'),
        ('test_production_features.py', 'Production Features (bcrypt, rate limiting)'),
        ('demo_auth.py', 'Demo Script (interactive authentication flow)')
    ]

    results = []
    total_duration = 0

    for filename, description in test_files:
        success, output, duration = run_test_file(filename, description)
        results.append((filename, description, success, output))
        total_duration += duration

    # Итоговый отчет
    print_header("TEST SUMMARY")

    passed = sum(1 for _, _, success, _ in results if success)
    total = len(results)

    print(f"Total Tests:     {total}")
    print(f"Passed:          {Colors.GREEN}{passed}{Colors.END}")
    print(f"Failed:          {Colors.RED}{total - passed}{Colors.END}")
    print(f"Total Time:      {total_duration:.2f}s")
    print()

    # Детали
    for filename, description, success, output in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if success else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  [{status}] {description}")

    # Финальный вердикт
    print()
    if passed == total:
        print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}✅ ALL TESTS PASSED{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
        return 0
    else:
        print(f"{Colors.BOLD}{Colors.RED}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.RED}⚠️  {total - passed} TEST(S) FAILED{Colors.END}")
        print()
        print(f"{Colors.YELLOW}Please review the errors above and fix them.{Colors.END}")
        print()
        print(f"{Colors.BOLD}Common Issues:{Colors.END}")
        print(f"  1. AWS credentials not configured (expected for dev)")
        print(f"  2. Missing dependencies → run: pip install -r requirements.txt")
        print(f"  3. Syntax errors → check the files above")
        print(f"{Colors.BOLD}{Colors.RED}{'='*80}{Colors.END}")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Tests interrupted by user{Colors.END}")
        sys.exit(130)

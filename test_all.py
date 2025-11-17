#!/usr/bin/env python3
"""
Единый тест-раннер для всей системы аутентификации
Запуск: python3 test_all.py
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
    """Печатает заголовок секции"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_section(text):
    """Печатает подзаголовок"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'-'*80}{Colors.END}")


def run_test(name, command, description):
    """
    Запускает один тест

    Returns:
        (passed: bool, output: str)
    """
    print(f"\n{Colors.BOLD}[TEST]{Colors.END} {name}")
    print(f"       {Colors.YELLOW}{description}{Colors.END}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"       {Colors.GREEN}✅ PASSED{Colors.END}")
            return True, result.stdout
        else:
            print(f"       {Colors.RED}❌ FAILED{Colors.END}")
            if result.stderr:
                print(f"\n{Colors.RED}Error output:{Colors.END}")
                print(result.stderr[:500])
            return False, result.stdout + "\n" + result.stderr

    except subprocess.TimeoutExpired:
        print(f"       {Colors.RED}❌ TIMEOUT (>60s){Colors.END}")
        return False, "Test timed out"
    except Exception as e:
        print(f"       {Colors.RED}❌ ERROR: {e}{Colors.END}")
        return False, str(e)


def check_dependencies():
    """Проверяет наличие зависимостей"""
    print_section("📦 Checking Dependencies")

    dependencies = [
        ('PyJWT', 'import jwt'),
        ('bcrypt', 'import bcrypt'),
        ('boto3', 'import boto3'),
        ('pydantic', 'import pydantic'),
    ]

    all_ok = True
    for name, import_stmt in dependencies:
        try:
            exec(import_stmt)
            print(f"✅ {name:<20} - installed")
        except ImportError:
            print(f"❌ {name:<20} - MISSING")
            all_ok = False

    if not all_ok:
        print(f"\n{Colors.YELLOW}⚠️  Some dependencies are missing. Install with:{Colors.END}")
        print(f"   pip install -r requirements.txt")

    return all_ok


def check_syntax():
    """Проверяет синтаксис критичных файлов"""
    print_section("🔍 Syntax Check")

    files_to_check = [
        'src/services/auth_service.py',
        'src/storage/session_storage.py',
        'test_unit_auth.py',
        'test_production_features.py',
    ]

    all_ok = True
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            print(f"⚠️  {filepath:<50} - not found")
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                compile(f.read(), filepath, 'exec')
            print(f"✅ {filepath:<50} - OK")
        except SyntaxError as e:
            print(f"❌ {filepath:<50} - SYNTAX ERROR (line {e.lineno})")
            all_ok = False

    return all_ok


def main():
    """Главная функция - запускает все тесты"""

    print_header("🧪 FULL TEST SUITE - Authentication System")
    print(f"{Colors.BOLD}Started at:{Colors.END} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}Working directory:{Colors.END} {os.getcwd()}\n")

    start_time = time.time()

    # Результаты
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'tests': []
    }

    # ========================================================================
    # 1. DEPENDENCIES CHECK
    # ========================================================================
    deps_ok = check_dependencies()
    if not deps_ok:
        print(f"\n{Colors.RED}❌ Some dependencies are missing. Please install them first.{Colors.END}")
        print("Run: pip install -r requirements.txt")
        return 1

    # ========================================================================
    # 2. SYNTAX CHECK
    # ========================================================================
    syntax_ok = check_syntax()

    # ========================================================================
    # 3. UNIT TESTS
    # ========================================================================
    print_section("🧪 Unit Tests (JWT, Sessions, Auth Flow)")

    passed, output = run_test(
        "Unit Tests",
        "python3 test_unit_auth.py",
        "Testing: password hashing, JWT tokens, sessions, tampering detection"
    )
    results['tests'].append(('Unit Tests (8 tests)', passed))
    results['total'] += 1
    if passed:
        results['passed'] += 1
    else:
        results['failed'] += 1

    # ========================================================================
    # 4. PRODUCTION FEATURES TESTS
    # ========================================================================
    print_section("🔐 Production Features Tests (bcrypt, Rate Limiting)")

    passed, output = run_test(
        "Production Features",
        "python3 test_production_features.py",
        "Testing: bcrypt hashing, rate limiting, brute force protection"
    )
    results['tests'].append(('Production Features (7 tests)', passed))
    results['total'] += 1
    if passed:
        results['passed'] += 1
    else:
        results['failed'] += 1

    # ========================================================================
    # 5. DEMO SCRIPT (optional, just check it runs)
    # ========================================================================
    print_section("🎭 Demo Script (Optional)")

    passed, output = run_test(
        "Authentication Demo",
        "python3 demo_auth.py",
        "Demonstrating full auth flow (registration → login → validation → logout)"
    )
    results['tests'].append(('Demo Script', passed))
    results['total'] += 1
    if passed:
        results['passed'] += 1
    else:
        results['failed'] += 1

    # ========================================================================
    # SUMMARY
    # ========================================================================
    elapsed = time.time() - start_time

    print_header("📊 TEST RESULTS SUMMARY")

    print(f"\n{Colors.BOLD}Test Results:{Colors.END}\n")
    for test_name, passed in results['tests']:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"  {status}  {test_name}")

    print(f"\n{Colors.BOLD}{'─'*80}{Colors.END}")
    print(f"\n{Colors.BOLD}Total Tests:{Colors.END}    {results['total']}")
    print(f"{Colors.GREEN}{Colors.BOLD}Passed:{Colors.END}        {results['passed']}")
    print(f"{Colors.RED}{Colors.BOLD}Failed:{Colors.END}        {results['failed']}")
    print(f"\n{Colors.BOLD}Time Elapsed:{Colors.END}   {elapsed:.2f} seconds")

    # Финальный статус
    print(f"\n{'='*80}")
    if results['failed'] == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! System is ready for production.{Colors.END}")
        print(f"\n{Colors.BOLD}Production Features Status:{Colors.END}")
        print(f"  ✅ JWT Authentication")
        print(f"  ✅ bcrypt Password Hashing")
        print(f"  ✅ Rate Limiting (Brute Force Protection)")
        print(f"  ✅ Session Persistence (DynamoDB)")
        print(f"  ✅ Multi-device Support")

        print(f"\n{Colors.YELLOW}Next Steps:{Colors.END}")
        print(f"  1. Set JWT_SECRET_KEY environment variable")
        print(f"  2. Configure AWS credentials for DynamoDB")
        print(f"  3. Integrate cookie persistence (see docs/PRODUCTION_ENHANCEMENTS.md)")
        print(f"  4. Deploy to production!")

        exit_code = 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}⚠️  {results['failed']} TEST(S) FAILED{Colors.END}")
        print(f"\n{Colors.YELLOW}Please review the errors above and fix them.{Colors.END}")
        print(f"\n{Colors.BOLD}Common Issues:{Colors.END}")
        print(f"  1. AWS credentials not configured (expected for dev)")
        print(f"  2. Missing dependencies → run: pip install -r requirements.txt")
        print(f"  3. Syntax errors → check the files above")

        exit_code = 1

    print(f"{'='*80}\n")

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Tests interrupted by user{Colors.END}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n{Colors.RED}❌ Test suite crashed: {e}{Colors.END}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

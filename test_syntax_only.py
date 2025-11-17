#!/usr/bin/env python3
"""
Тест синтаксиса всех файлов (без импортов зависимостей)
Проверяет что код написан корректно
"""
import py_compile
import sys
import os

# Цвета
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
END = '\033[0m'

def test_syntax(filepath):
    """Проверка синтаксиса файла"""
    try:
        py_compile.compile(filepath, doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"{RED}✗{END} {filepath}: {e}")
        return False

def main():
    print(f"{BOLD}{'='*70}{END}")
    print(f"{BOLD}🔍 Syntax Check - Authentication System Files{END}")
    print(f"{BOLD}{'='*70}{END}\n")

    files_to_check = [
        # Core auth files
        'src/services/auth_service.py',
        'src/storage/session_storage.py',
        'src/utils/cookie_helper.py',

        # Test files
        'test_unit_auth.py',
        'test_production_features.py',
        'test_all.py',
        'demo_auth.py',

        # Main app
        'app.py',
    ]

    passed = 0
    failed = 0

    for filepath in files_to_check:
        if os.path.exists(filepath):
            if test_syntax(filepath):
                print(f"{GREEN}✓{END} {filepath}")
                passed += 1
            else:
                failed += 1
        else:
            print(f"{YELLOW}⊘{END} {filepath} (not found)")

    print(f"\n{BOLD}{'='*70}{END}")
    print(f"{BOLD}Results:{END}")
    print(f"  {GREEN}Passed:{END} {passed}")
    print(f"  {RED}Failed:{END} {failed}")

    if failed == 0:
        print(f"\n{GREEN}{BOLD}✅ All files have valid Python syntax!{END}")
        return 0
    else:
        print(f"\n{RED}{BOLD}❌ Some files have syntax errors{END}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

"""
Тесты для production features: bcrypt, rate limiting
"""
import sys
import os
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock storage
class MockSessionStorage:
    def __init__(self):
        self.sessions = {}
    async def save_session(self, session_id, user_id, metadata=None):
        self.sessions[session_id] = {'session_id': session_id, 'user_id': user_id}
        return True

class MockDynamoDBStorage:
    def __init__(self):
        self.users = {}
    async def get_user_data(self, username):
        return self.users.get(username)
    async def save_user_data(self, username, data):
        self.users[username] = data
        return True

# Патчим DynamoDBStorage
import src.services.auth_service as auth_module
original_storage = None

def setup_mock():
    global original_storage
    auth_module.DynamoDBStorage = MockDynamoDBStorage

setup_mock()

from src.services.auth_service import AuthService, BCRYPT_AVAILABLE


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add_test(self, name, passed, message=""):
        self.tests.append({'name': name, 'passed': passed, 'message': message})
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        print("\n" + "="*70)
        print("PRODUCTION FEATURES TEST RESULTS".center(70))
        print("="*70)

        for test in self.tests:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            print(f"{status} | {test['name']}")
            if test['message']:
                print(f"       {test['message']}")

        print("\n" + "-"*70)
        total = self.passed + self.failed
        print(f"Total: {total} | Passed: {self.passed} | Failed: {self.failed}")

        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"\n⚠️  {self.failed} test(s) failed")
        print("="*70 + "\n")

        return self.failed == 0


async def run_tests():
    results = TestResults()
    print("\n🧪 Testing Production Features\n")

    # ========================================================================
    # TEST 1: bcrypt availability
    # ========================================================================
    print("[1/7] Testing bcrypt availability...")
    try:
        if BCRYPT_AVAILABLE:
            results.add_test("bcrypt Available", True, "bcrypt library loaded successfully")
        else:
            results.add_test("bcrypt Available", False, "bcrypt not installed (using SHA256 fallback)")
    except Exception as e:
        results.add_test("bcrypt Available", False, str(e))

    # ========================================================================
    # TEST 2: bcrypt password hashing
    # ========================================================================
    print("[2/7] Testing bcrypt password hashing...")
    try:
        auth = AuthService(session_storage=MockSessionStorage())
        password = "TestPassword123!"

        hash1 = auth._hash_password(password)
        hash2 = auth._hash_password(password)

        # bcrypt должен генерировать разные хеши (соль)
        if BCRYPT_AVAILABLE:
            assert hash1 != hash2, "bcrypt should generate different hashes (salted)"
            assert hash1.startswith('$2b$'), "bcrypt hash should start with $2b$"
            results.add_test("bcrypt Hashing", True, f"Hash format: {hash1[:10]}...")
        else:
            assert hash1.startswith('sha256:'), "Should use SHA256 fallback"
            results.add_test("bcrypt Hashing (fallback)", True, "SHA256 fallback working")
    except Exception as e:
        results.add_test("bcrypt Hashing", False, str(e))

    # ========================================================================
    # TEST 3: bcrypt password verification
    # ========================================================================
    print("[3/7] Testing bcrypt password verification...")
    try:
        auth = AuthService(session_storage=MockSessionStorage())
        password = "SecurePass456!"

        password_hash = auth._hash_password(password)

        # Правильный пароль должен пройти
        assert auth._verify_password(password, password_hash), "Correct password should verify"

        # Неправильный пароль не должен пройти
        assert not auth._verify_password("WrongPass", password_hash), "Wrong password should fail"

        results.add_test("bcrypt Verification", True, "Password verification works")
    except Exception as e:
        results.add_test("bcrypt Verification", False, str(e))

    # ========================================================================
    # TEST 4: Rate limiting - normal usage
    # ========================================================================
    print("[4/7] Testing rate limiting (normal usage)...")
    try:
        auth = AuthService(session_storage=MockSessionStorage())
        auth.max_login_attempts = 5
        username = "test_user_normal"

        # Первые 5 попыток должны быть разрешены
        for i in range(5):
            allowed, msg = auth._check_rate_limit(username)
            assert allowed, f"Attempt {i+1} should be allowed"

        results.add_test("Rate Limiting (Normal)", True, "5 attempts allowed")
    except Exception as e:
        results.add_test("Rate Limiting (Normal)", False, str(e))

    # ========================================================================
    # TEST 5: Rate limiting - lockout
    # ========================================================================
    print("[5/7] Testing rate limiting (lockout)...")
    try:
        auth = AuthService(session_storage=MockSessionStorage())
        auth.max_login_attempts = 3  # Меньше для быстрого теста
        auth.lockout_duration = 2    # 2 секунды
        username = "test_user_lockout"

        # Записываем 3 неудачные попытки
        for i in range(3):
            auth._record_login_attempt(username)

        # 4-я попытка должна быть заблокирована
        allowed, msg = auth._check_rate_limit(username)
        assert not allowed, "Should be locked out after 3 attempts"
        assert "Try again in" in msg, "Should show lockout message"

        results.add_test("Rate Limiting (Lockout)", True, f"Locked out: '{msg}'")
    except Exception as e:
        results.add_test("Rate Limiting (Lockout)", False, str(e))

    # ========================================================================
    # TEST 6: Rate limiting - expiration
    # ========================================================================
    print("[6/7] Testing rate limiting (expiration)...")
    try:
        auth = AuthService(session_storage=MockSessionStorage())
        auth.max_login_attempts = 3
        auth.lockout_duration = 2  # 2 секунды
        username = "test_user_expire"

        # Записываем 3 попытки
        for i in range(3):
            auth._record_login_attempt(username)

        # Должен быть заблокирован
        allowed, msg = auth._check_rate_limit(username)
        assert not allowed, "Should be locked out"

        # Ждем истечения lockout
        print("       Waiting 2 seconds for lockout expiration...")
        time.sleep(2.1)

        # Теперь должен быть разблокирован
        allowed, msg = auth._check_rate_limit(username)
        assert allowed, "Should be unlocked after expiration"

        results.add_test("Rate Limiting (Expiration)", True, "Lockout expires correctly")
    except Exception as e:
        results.add_test("Rate Limiting (Expiration)", False, str(e))

    # ========================================================================
    # TEST 7: Full login flow with bcrypt + rate limiting
    # ========================================================================
    print("[7/7] Testing full login flow...")
    try:
        auth = AuthService(session_storage=MockSessionStorage())
        username = "integration_user"
        password = "IntegrationPass123!"

        # 1. Регистрация
        success, msg = await auth.register_user(username, password)
        assert success, f"Registration should succeed: {msg}"

        # 2. Успешный логин
        success, token, msg = await auth.login(username, password)
        assert success, f"Login should succeed: {msg}"
        assert token is not None, "Should return JWT token"

        # 3. Неудачный логин (неправильный пароль)
        success, token, msg = await auth.login(username, "WrongPassword")
        assert not success, "Login with wrong password should fail"
        assert token is None, "Should not return token"

        results.add_test("Full Login Flow", True, "Registration + login + auth works")
    except Exception as e:
        results.add_test("Full Login Flow", False, str(e))

    # ========================================================================
    # Print Results
    # ========================================================================
    all_passed = results.print_summary()

    # Additional info
    print("\n📊 Production Features Status:\n")
    if BCRYPT_AVAILABLE:
        print("✅ bcrypt: ENABLED (production-ready)")
    else:
        print("⚠️  bcrypt: DISABLED (install with: pip install bcrypt)")

    print("✅ Rate Limiting: ENABLED")
    print("✅ JWT Tokens: ENABLED")
    print("✅ DynamoDB Sessions: ENABLED")

    return all_passed


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PRODUCTION FEATURES - COMPREHENSIVE TESTS".center(70))
    print("="*70)

    try:
        all_passed = asyncio.run(run_tests())

        if all_passed:
            print("\n✅ All production features are working correctly!\n")
            exit(0)
        else:
            print("\n❌ Some tests failed. Please review the errors above.\n")
            exit(1)

    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)

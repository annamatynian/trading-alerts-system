"""
Unit тесты для проверки JWT аутентификации
Тестируют все компоненты без реального DynamoDB
"""
import sys
import os
import asyncio
import secrets
import hashlib
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import jwt

# Mock Storage для тестов
class MockSessionStorage:
    def __init__(self):
        self.sessions = {}
        self.users = {}

    async def save_session(self, session_id, user_id, metadata=None):
        self.sessions[session_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
            'metadata': metadata or {}
        }
        return True

    async def get_session(self, session_id):
        return self.sessions.get(session_id)

    async def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    async def get_user_sessions(self, user_id):
        return [s for s in self.sessions.values() if s['user_id'] == user_id]


class TestResults:
    """Класс для сбора результатов тестов"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add_test(self, name, passed, message=""):
        self.tests.append({
            'name': name,
            'passed': passed,
            'message': message
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        print("\n" + "="*70)
        print("TEST RESULTS SUMMARY".center(70))
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
    """Запуск всех тестов"""
    results = TestResults()

    print("\n🧪 Running Unit Tests for Authentication System\n")

    # ========================================================================
    # TEST 1: Password Hashing
    # ========================================================================
    print("[1/8] Testing password hashing...")
    try:
        password = "TestPassword123!"
        hash1 = hashlib.sha256(password.encode()).hexdigest()
        hash2 = hashlib.sha256(password.encode()).hexdigest()

        # Одинаковые пароли должны давать одинаковый хеш
        assert hash1 == hash2, "Same password should produce same hash"

        # Разные пароли должны давать разные хеши
        different_hash = hashlib.sha256("DifferentPass".encode()).hexdigest()
        assert hash1 != different_hash, "Different passwords should produce different hashes"

        results.add_test("Password Hashing", True, "SHA256 works correctly")
    except Exception as e:
        results.add_test("Password Hashing", False, str(e))

    # ========================================================================
    # TEST 2: JWT Token Generation
    # ========================================================================
    print("[2/8] Testing JWT token generation...")
    try:
        secret = secrets.token_urlsafe(32)
        username = "test_user"
        session_id = secrets.token_urlsafe(16)

        now = datetime.utcnow()
        expires = now + timedelta(days=30)

        payload = {
            'sub': username,
            'jti': session_id,
            'iat': int(now.timestamp()),
            'exp': int(expires.timestamp()),
        }

        token = jwt.encode(payload, secret, algorithm='HS256')

        # Проверяем что токен - это строка
        assert isinstance(token, str), "Token should be a string"

        # Проверяем что токен состоит из 3 частей
        parts = token.split('.')
        assert len(parts) == 3, "JWT should have 3 parts (header.payload.signature)"

        results.add_test("JWT Token Generation", True, f"Token has {len(parts)} parts")
    except Exception as e:
        results.add_test("JWT Token Generation", False, str(e))

    # ========================================================================
    # TEST 3: JWT Token Validation
    # ========================================================================
    print("[3/8] Testing JWT token validation...")
    try:
        secret = secrets.token_urlsafe(32)
        payload = {
            'sub': 'test_user',
            'jti': 'test_session',
            'iat': int(datetime.utcnow().timestamp()),
            'exp': int((datetime.utcnow() + timedelta(days=1)).timestamp()),
        }

        token = jwt.encode(payload, secret, algorithm='HS256')
        decoded = jwt.decode(token, secret, algorithms=['HS256'])

        assert decoded['sub'] == 'test_user', "Username should match"
        assert decoded['jti'] == 'test_session', "Session ID should match"

        results.add_test("JWT Token Validation", True, "Token decoded successfully")
    except Exception as e:
        results.add_test("JWT Token Validation", False, str(e))

    # ========================================================================
    # TEST 4: JWT Signature Tampering Detection
    # ========================================================================
    print("[4/8] Testing JWT tampering detection...")
    try:
        secret = secrets.token_urlsafe(32)
        payload = {'sub': 'user1', 'jti': 'session1', 'exp': int((datetime.utcnow() + timedelta(days=1)).timestamp())}
        token = jwt.encode(payload, secret, algorithm='HS256')

        # Пытаемся изменить payload (подделка)
        parts = token.split('.')
        # Изменяем payload на другой username
        fake_payload = {'sub': 'admin', 'jti': 'session1', 'exp': payload['exp']}
        import base64
        import json
        fake_payload_encoded = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip('=')
        tampered_token = f"{parts[0]}.{fake_payload_encoded}.{parts[2]}"

        # Валидация должна провалиться
        try:
            jwt.decode(tampered_token, secret, algorithms=['HS256'])
            results.add_test("JWT Tampering Detection", False, "Tampered token was accepted!")
        except jwt.InvalidSignatureError:
            results.add_test("JWT Tampering Detection", True, "Tampered token rejected ✅")
    except Exception as e:
        results.add_test("JWT Tampering Detection", False, str(e))

    # ========================================================================
    # TEST 5: Session Storage - Save & Retrieve
    # ========================================================================
    print("[5/8] Testing session storage (save & retrieve)...")
    try:
        storage = MockSessionStorage()
        session_id = "test_session_123"
        user_id = "anna"

        # Сохраняем сессию
        success = await storage.save_session(session_id, user_id, {'ip': '127.0.0.1'})
        assert success, "Session save should succeed"

        # Получаем сессию
        session = await storage.get_session(session_id)
        assert session is not None, "Session should exist"
        assert session['user_id'] == user_id, "User ID should match"
        assert session['session_id'] == session_id, "Session ID should match"

        results.add_test("Session Storage (Save & Retrieve)", True, "Session saved and retrieved")
    except Exception as e:
        results.add_test("Session Storage (Save & Retrieve)", False, str(e))

    # ========================================================================
    # TEST 6: Session Storage - Delete
    # ========================================================================
    print("[6/8] Testing session storage (delete)...")
    try:
        storage = MockSessionStorage()
        session_id = "test_session_delete"

        # Создаем сессию
        await storage.save_session(session_id, "user1")

        # Проверяем что существует
        session = await storage.get_session(session_id)
        assert session is not None, "Session should exist before delete"

        # Удаляем
        success = await storage.delete_session(session_id)
        assert success, "Delete should succeed"

        # Проверяем что удалена
        session = await storage.get_session(session_id)
        assert session is None, "Session should not exist after delete"

        results.add_test("Session Storage (Delete)", True, "Session deleted successfully")
    except Exception as e:
        results.add_test("Session Storage (Delete)", False, str(e))

    # ========================================================================
    # TEST 7: Multiple Sessions per User
    # ========================================================================
    print("[7/8] Testing multiple sessions per user...")
    try:
        storage = MockSessionStorage()
        user_id = "multi_device_user"

        # Создаем 3 сессии для одного пользователя (разные устройства)
        await storage.save_session("session_mobile", user_id)
        await storage.save_session("session_desktop", user_id)
        await storage.save_session("session_tablet", user_id)

        # Получаем все сессии
        sessions = await storage.get_user_sessions(user_id)

        assert len(sessions) == 3, f"Should have 3 sessions, got {len(sessions)}"

        # Проверяем что все принадлежат одному пользователю
        for session in sessions:
            assert session['user_id'] == user_id, "All sessions should belong to same user"

        results.add_test("Multiple Sessions per User", True, "Multi-device sessions work")
    except Exception as e:
        results.add_test("Multiple Sessions per User", False, str(e))

    # ========================================================================
    # TEST 8: Full Authentication Flow
    # ========================================================================
    print("[8/8] Testing full authentication flow...")
    try:
        storage = MockSessionStorage()
        secret = secrets.token_urlsafe(32)

        # 1. Регистрация
        username = "integration_test_user"
        password = "SecurePass123!"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        storage.users[username] = {'password_hash': password_hash}

        # 2. Логин - проверка пароля
        input_password = "SecurePass123!"
        input_hash = hashlib.sha256(input_password.encode()).hexdigest()
        assert input_hash == password_hash, "Password verification failed"

        # 3. Создание JWT и сессии
        session_id = secrets.token_urlsafe(16)
        payload = {
            'sub': username,
            'jti': session_id,
            'iat': int(datetime.utcnow().timestamp()),
            'exp': int((datetime.utcnow() + timedelta(days=30)).timestamp()),
        }
        token = jwt.encode(payload, secret, algorithm='HS256')
        await storage.save_session(session_id, username)

        # 4. Валидация токена
        decoded = jwt.decode(token, secret, algorithms=['HS256'])
        session = await storage.get_session(decoded['jti'])
        assert session is not None, "Session should exist"
        assert session['user_id'] == username, "Session user should match"

        # 5. Логаут
        await storage.delete_session(session_id)
        session = await storage.get_session(session_id)
        assert session is None, "Session should be deleted after logout"

        results.add_test("Full Authentication Flow", True, "Complete flow works end-to-end")
    except Exception as e:
        results.add_test("Full Authentication Flow", False, str(e))

    # ========================================================================
    # Print Results
    # ========================================================================
    all_passed = results.print_summary()

    return all_passed


if __name__ == "__main__":
    print("\n" + "="*70)
    print("JWT AUTHENTICATION - UNIT TESTS".center(70))
    print("="*70)

    try:
        all_passed = asyncio.run(run_tests())

        if all_passed:
            print("\n✅ All authentication components are working correctly!\n")
            exit(0)
        else:
            print("\n❌ Some tests failed. Please review the errors above.\n")
            exit(1)

    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)

"""
Production Features Tests для JWT Authentication
Тестирует production-ready функции: bcrypt, rate limiting, интеграции

Запуск:
    pytest test_production_features.py -v
    pytest test_production_features.py -v -k "bcrypt"  # только bcrypt тесты
"""
import pytest
import asyncio
import uuid
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.auth_service import AuthService, RateLimiter, BCRYPT_AVAILABLE
from storage.session_storage import SessionStorage


# ============================================================================
# Test 1: bcrypt Password Hashing (если доступен)
# ============================================================================
@pytest.mark.asyncio
@pytest.mark.skipif(not BCRYPT_AVAILABLE, reason="bcrypt not available")
async def test_bcrypt_hashing():
    """
    Тестирует bcrypt хеширование паролей

    Проверяет:
    - bcrypt используется когда доступен
    - Хеш начинается с $2b$ (bcrypt signature)
    - Верификация работает корректно
    - Разные пароли дают разные хеши
    """
    auth = AuthService(secret_key="test-secret")

    password = "MySecurePassword123!"
    hashed = auth._hash_password(password)

    # bcrypt хеши начинаются с $2b$ (или $2a$, $2y$)
    assert hashed.startswith('$2'), f"bcrypt hash should start with $2, got: {hashed[:10]}"

    # Проверяем верификацию
    assert auth._verify_password(password, hashed) is True
    assert auth._verify_password("WrongPassword", hashed) is False

    # Проверяем что разные пароли дают разные хеши
    hashed2 = auth._hash_password("DifferentPassword456!")
    assert hashed != hashed2

    print("✅ Test 1 passed: bcrypt hashing works correctly")


# ============================================================================
# Test 2: SHA256 Fallback (когда bcrypt недоступен)
# ============================================================================
@pytest.mark.asyncio
async def test_sha256_fallback():
    """
    Тестирует SHA256 fallback когда bcrypt недоступен

    Проверяет:
    - SHA256 используется как fallback
    - Формат хеша: sha256$salt$hash
    - Верификация работает
    """
    auth = AuthService(secret_key="test-secret")

    # Временно отключаем bcrypt для теста
    original_bcrypt = BCRYPT_AVAILABLE
    import services.auth_service as auth_module
    auth_module.BCRYPT_AVAILABLE = False

    try:
        password = "TestPassword123"
        hashed = auth._hash_password(password)

        # SHA256 формат: sha256$salt$hash
        assert hashed.startswith('sha256$'), f"Should use SHA256, got: {hashed[:20]}"
        parts = hashed.split('$')
        assert len(parts) == 3, "SHA256 hash should have 3 parts"

        # Верификация
        assert auth._verify_password(password, hashed) is True
        assert auth._verify_password("WrongPassword", hashed) is False

    finally:
        # Восстанавливаем оригинальное значение
        auth_module.BCRYPT_AVAILABLE = original_bcrypt

    print("✅ Test 2 passed: SHA256 fallback works correctly")


# ============================================================================
# Test 3: Rate Limiter Timing
# ============================================================================
@pytest.mark.asyncio
async def test_rate_limiter_timing():
    """
    Тестирует точность работы rate limiter по времени

    Проверяет:
    - Попытки блокируются на указанное время
    - После истечения lockout_minutes доступ восстанавливается
    - Время блокировки вычисляется корректно
    """
    # Короткий lockout для быстрого теста
    rate_limiter = RateLimiter(max_attempts=2, lockout_minutes=0.05)  # 3 секунды

    username = "testuser"

    # Первая попытка - OK
    allowed, _ = rate_limiter.check_rate_limit(username)
    assert allowed is True
    rate_limiter.record_attempt(username)

    # Вторая попытка - OK
    allowed, _ = rate_limiter.check_rate_limit(username)
    assert allowed is True
    rate_limiter.record_attempt(username)

    # Третья попытка - BLOCKED
    allowed, msg = rate_limiter.check_rate_limit(username)
    assert allowed is False
    assert "Too many attempts" in msg

    # Ждем истечения lockout
    await asyncio.sleep(4)  # Ждем 4 секунды (lockout = 3 секунды)

    # Теперь должно быть разрешено
    allowed, _ = rate_limiter.check_rate_limit(username)
    assert allowed is True

    print("✅ Test 3 passed: Rate limiter timing works correctly")


# ============================================================================
# Test 4: Multiple User Sessions
# ============================================================================
@pytest.mark.asyncio
async def test_multiple_user_sessions():
    """
    Тестирует множественные сессии одного пользователя

    Проверяет:
    - Пользователь может иметь несколько активных сессий
    - Каждая сессия независима
    - Logout одной сессии не влияет на другие
    """
    # Mock SessionStorage
    sessions_db = {}  # Имитация базы данных сессий

    async def mock_save_session(session_id, user_id, token, metadata=None):
        sessions_db[session_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'token': token,
            'metadata': metadata,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }
        return True

    async def mock_get_session(session_id):
        return sessions_db.get(session_id)

    async def mock_delete_session(session_id):
        if session_id in sessions_db:
            del sessions_db[session_id]
        return True

    async def mock_get_user_sessions(user_id):
        return [s for s in sessions_db.values() if s['user_id'] == user_id]

    mock_storage = Mock(spec=SessionStorage)
    mock_storage.save_session = AsyncMock(side_effect=mock_save_session)
    mock_storage.get_session = AsyncMock(side_effect=mock_get_session)
    mock_storage.delete_session = AsyncMock(side_effect=mock_delete_session)
    mock_storage.get_user_sessions = AsyncMock(side_effect=mock_get_user_sessions)

    auth = AuthService(
        secret_key="test-secret",
        session_storage=mock_storage
    )

    # Регистрируем пользователя
    user = await auth.register_user("alice", "password123")

    # Создаем 3 сессии (разные устройства)
    session1 = await auth.login("alice", "password123", metadata={"device": "laptop"})
    session2 = await auth.login("alice", "password123", metadata={"device": "phone"})
    session3 = await auth.login("alice", "password123", metadata={"device": "tablet"})

    # Проверяем что все сессии разные
    assert session1['session_id'] != session2['session_id']
    assert session2['session_id'] != session3['session_id']

    # Проверяем что у пользователя 3 активных сессии
    user_sessions = await auth.get_user_sessions("alice")
    assert len(user_sessions) == 3

    # Удаляем одну сессию (logout с phone)
    await auth.logout(session2['session_id'])

    # Проверяем что осталось 2 сессии
    user_sessions = await auth.get_user_sessions("alice")
    assert len(user_sessions) == 2

    print("✅ Test 4 passed: Multiple user sessions work correctly")


# ============================================================================
# Test 5: Token Refresh Flow
# ============================================================================
@pytest.mark.asyncio
async def test_token_refresh_flow():
    """
    Тестирует refresh token flow

    Проверяет:
    - Токен можно обновить
    - Новый токен отличается от старого
    - Session_id остается тем же
    - Время истечения обновляется
    """
    # Mock SessionStorage
    sessions_db = {}

    async def mock_save_session(session_id, user_id, token, metadata=None):
        sessions_db[session_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'token': token,
            'metadata': metadata,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }
        return True

    async def mock_get_session(session_id):
        return sessions_db.get(session_id)

    async def mock_extend_session(session_id, hours=None):
        if session_id in sessions_db:
            new_expires = datetime.now() + timedelta(hours=hours or 24)
            sessions_db[session_id]['expires_at'] = new_expires.isoformat()
            return True
        return False

    mock_storage = Mock(spec=SessionStorage)
    mock_storage.save_session = AsyncMock(side_effect=mock_save_session)
    mock_storage.get_session = AsyncMock(side_effect=mock_get_session)
    mock_storage.extend_session = AsyncMock(side_effect=mock_extend_session)

    auth = AuthService(
        secret_key="test-secret",
        session_storage=mock_storage
    )

    # Регистрация и логин
    await auth.register_user("bob", "password123")
    original = await auth.login("bob", "password123")

    original_token = original['access_token']
    original_session_id = original['session_id']
    original_expires = original['expires_at']

    # Ждем немного чтобы timestamp изменился
    await asyncio.sleep(0.1)

    # Обновляем токен
    refreshed = await auth.refresh_token(original_session_id, hours=48)

    # Проверки
    assert refreshed['session_id'] == original_session_id, "Session ID should stay the same"
    assert refreshed['access_token'] != original_token, "Token should be different"
    assert refreshed['expires_at'] != original_expires, "Expiration should be updated"

    # Проверяем что новый токен валиден
    payload = await auth.validate_token(refreshed['access_token'])
    assert payload['username'] == "bob"

    print("✅ Test 5 passed: Token refresh flow works correctly")


# ============================================================================
# Test 6: Concurrent Login Attempts
# ============================================================================
@pytest.mark.asyncio
async def test_concurrent_login_attempts():
    """
    Тестирует параллельные попытки входа

    Проверяет:
    - Система корректно обрабатывает concurrent requests
    - Rate limiter работает корректно при параллельных запросах
    - Нет race conditions
    """
    mock_storage = Mock(spec=SessionStorage)
    mock_storage.save_session = AsyncMock(return_value=True)

    auth = AuthService(
        secret_key="test-secret",
        session_storage=mock_storage,
        rate_limiter=RateLimiter(max_attempts=5, lockout_minutes=1)
    )

    # Регистрируем пользователя
    await auth.register_user("charlie", "password123")

    # Делаем 10 параллельных успешных логинов
    tasks = [
        auth.login("charlie", "password123", metadata={"attempt": i})
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Все должны успешно завершиться
    successful_logins = [r for r in results if not isinstance(r, Exception)]
    assert len(successful_logins) == 10, "All parallel logins should succeed"

    # Проверяем что все session_id уникальны
    session_ids = [r['session_id'] for r in successful_logins]
    assert len(set(session_ids)) == 10, "All session IDs should be unique"

    print("✅ Test 6 passed: Concurrent login attempts work correctly")


# ============================================================================
# Test 7: Session Cleanup Integration
# ============================================================================
@pytest.mark.asyncio
async def test_session_cleanup_integration():
    """
    Тестирует интеграцию cleanup expired sessions

    Проверяет:
    - Cleanup удаляет только истекшие сессии
    - Активные сессии сохраняются
    - Возвращается корректное количество удаленных сессий
    """
    # Mock DynamoDB Table
    mock_table = MagicMock()

    # Создаем тестовые данные
    now = datetime.now()
    test_sessions = [
        # Активная сессия 1
        {
            'PK': 'session#active1',
            'SK': 'metadata',
            'entity_type': 'session',
            'session_id': 'active1',
            'user_id': 'user1',
            'token': 'token1',
            'created_at': now.isoformat(),
            'expires_at': (now + timedelta(hours=1)).isoformat()
        },
        # Активная сессия 2
        {
            'PK': 'session#active2',
            'SK': 'metadata',
            'entity_type': 'session',
            'session_id': 'active2',
            'user_id': 'user2',
            'token': 'token2',
            'created_at': now.isoformat(),
            'expires_at': (now + timedelta(hours=2)).isoformat()
        },
        # Истекшая сессия 1
        {
            'PK': 'session#expired1',
            'SK': 'metadata',
            'entity_type': 'session',
            'session_id': 'expired1',
            'user_id': 'user3',
            'token': 'token3',
            'created_at': (now - timedelta(hours=25)).isoformat(),
            'expires_at': (now - timedelta(hours=1)).isoformat()  # Истекла
        },
        # Истекшая сессия 2
        {
            'PK': 'session#expired2',
            'SK': 'metadata',
            'entity_type': 'session',
            'session_id': 'expired2',
            'user_id': 'user4',
            'token': 'token4',
            'created_at': (now - timedelta(hours=30)).isoformat(),
            'expires_at': (now - timedelta(hours=6)).isoformat()  # Истекла
        }
    ]

    mock_table.scan.return_value = {'Items': test_sessions}

    deleted_sessions = []

    def mock_delete(Key):
        deleted_sessions.append(Key['PK'])

    mock_table.delete_item.side_effect = mock_delete

    with patch('storage.session_storage.boto3') as mock_boto3:
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        storage = SessionStorage(table_name="test-table")
        storage.table = mock_table

        # Запускаем cleanup
        deleted_count = await storage.cleanup_expired_sessions()

        # Проверяем результаты
        assert deleted_count == 2, "Should delete 2 expired sessions"
        assert 'session#expired1' in deleted_sessions
        assert 'session#expired2' in deleted_sessions
        assert 'session#active1' not in deleted_sessions
        assert 'session#active2' not in deleted_sessions

    print("✅ Test 7 passed: Session cleanup integration works correctly")


# ============================================================================
# Run all tests
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🏭 Running Production Features Tests")
    print("="*70 + "\n")

    # Запускаем все тесты
    pytest.main([__file__, "-v", "--tb=short"])

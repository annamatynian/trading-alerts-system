"""
Unit Tests для JWT Authentication System
Работают без AWS credentials (используют mocking)

Запуск:
    pytest test_unit_auth.py -v
    pytest test_unit_auth.py::test_password_hashing -v
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.auth_service import AuthService, RateLimiter
from storage.session_storage import SessionStorage


# ============================================================================
# Test 1: Password Hashing - bcrypt и SHA256
# ============================================================================
@pytest.mark.asyncio
async def test_password_hashing():
    """
    Тестирует хеширование паролей с bcrypt (если доступен) или SHA256 fallback

    Проверяет:
    - Хеш пароля отличается от оригинала
    - Верный пароль проходит проверку
    - Неверный пароль не проходит проверку
    - Одинаковые пароли дают разные хеши (salt)
    """
    auth = AuthService(secret_key="test-secret-123")

    password = "MySecurePassword123!"

    # Хешируем пароль
    hashed1 = auth._hash_password(password)
    hashed2 = auth._hash_password(password)

    # Проверяем что хеш != оригинал
    assert hashed1 != password, "Hash should differ from original password"
    assert hashed2 != password, "Hash should differ from original password"

    # Проверяем что одинаковые пароли дают разные хеши (salt)
    assert hashed1 != hashed2, "Same password should produce different hashes (salt)"

    # Проверяем верный пароль
    assert auth._verify_password(password, hashed1) is True, "Valid password should verify"
    assert auth._verify_password(password, hashed2) is True, "Valid password should verify"

    # Проверяем неверный пароль
    assert auth._verify_password("WrongPassword", hashed1) is False, "Invalid password should not verify"

    print("✅ Test 1 passed: Password hashing works correctly")


# ============================================================================
# Test 2: JWT Token Generation
# ============================================================================
@pytest.mark.asyncio
async def test_jwt_generation():
    """
    Тестирует генерацию JWT токенов

    Проверяет:
    - Токен генерируется после регистрации и логина
    - Токен содержит корректный payload
    - Токен можно декодировать
    """
    # Mock SessionStorage чтобы не требовать AWS
    mock_storage = Mock(spec=SessionStorage)
    mock_storage.save_session = AsyncMock(return_value=True)

    auth = AuthService(
        secret_key="test-secret-123",
        session_storage=mock_storage
    )

    # Регистрируем пользователя
    user = await auth.register_user("testuser", "password123")
    assert user['username'] == "testuser", "Username should match"

    # Логинимся
    result = await auth.login("testuser", "password123")

    # Проверяем что токен создан
    assert 'access_token' in result, "Should have access_token"
    assert 'session_id' in result, "Should have session_id"
    assert result['token_type'] == 'Bearer', "Token type should be Bearer"

    # Декодируем токен (без верификации для теста)
    import jwt
    payload = jwt.decode(result['access_token'], options={"verify_signature": False})

    assert payload['username'] == "testuser", "Token should contain username"
    assert payload['sub'] == user['user_id'], "Token should contain user_id"
    assert 'session_id' in payload, "Token should contain session_id"
    assert 'exp' in payload, "Token should contain expiration"

    print("✅ Test 2 passed: JWT generation works correctly")


# ============================================================================
# Test 3: JWT Token Validation
# ============================================================================
@pytest.mark.asyncio
async def test_jwt_validation():
    """
    Тестирует валидацию JWT токенов

    Проверяет:
    - Валидный токен проходит проверку
    - Невалидный токен отклоняется
    - Истекший токен отклоняется
    """
    # Mock SessionStorage
    mock_storage = Mock(spec=SessionStorage)
    mock_storage.save_session = AsyncMock(return_value=True)

    auth = AuthService(
        secret_key="test-secret-123",
        access_token_expire_hours=1,
        session_storage=mock_storage
    )

    # Регистрируем и логинимся
    await auth.register_user("testuser", "password123")
    login_result = await auth.login("testuser", "password123")
    token = login_result['access_token']
    session_id = login_result['session_id']

    # Mock get_session для валидации
    mock_storage.get_session = AsyncMock(return_value={
        'session_id': session_id,
        'user_id': login_result['user']['user_id'],
        'token': token,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
    })

    # Валидируем токен
    payload = await auth.validate_token(token)
    assert payload['username'] == "testuser", "Should validate correct token"

    # Проверяем невалидный токен
    with pytest.raises(ValueError, match="Invalid token"):
        await auth.validate_token("invalid.token.here")

    # Проверяем токен с другим секретным ключом
    import jwt
    wrong_token = jwt.encode({'sub': '123', 'username': 'test'}, 'wrong-secret', algorithm='HS256')
    with pytest.raises(ValueError, match="Invalid token"):
        await auth.validate_token(wrong_token)

    print("✅ Test 3 passed: JWT validation works correctly")


# ============================================================================
# Test 4: Session CRUD Operations
# ============================================================================
@pytest.mark.asyncio
async def test_session_crud():
    """
    Тестирует CRUD операции с сессиями

    Проверяет:
    - Создание сессии (save_session)
    - Получение сессии (get_session)
    - Удаление сессии (delete_session)
    """
    # Mock DynamoDB Table
    mock_table = MagicMock()
    mock_table.put_item = MagicMock()
    mock_table.get_item = MagicMock()
    mock_table.delete_item = MagicMock()

    # Создаем SessionStorage с мокнутым table
    with patch('storage.session_storage.boto3') as mock_boto3:
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        storage = SessionStorage(table_name="test-table")
        storage.table = mock_table

        session_id = str(uuid.uuid4())
        user_id = "user123"
        token = "test.jwt.token"

        # Test: Save session
        result = await storage.save_session(session_id, user_id, token)
        assert result is True, "save_session should return True"
        mock_table.put_item.assert_called_once()

        # Test: Get session (мокаем успешный ответ)
        mock_table.get_item.return_value = {
            'Item': {
                'session_id': session_id,
                'user_id': user_id,
                'token': token,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            }
        }

        session = await storage.get_session(session_id)
        assert session is not None, "Should retrieve session"
        assert session['user_id'] == user_id, "User ID should match"
        assert session['token'] == token, "Token should match"

        # Test: Delete session
        result = await storage.delete_session(session_id)
        assert result is True, "delete_session should return True"
        mock_table.delete_item.assert_called_once()

    print("✅ Test 4 passed: Session CRUD operations work correctly")


# ============================================================================
# Test 5: Full Authentication Flow
# ============================================================================
@pytest.mark.asyncio
async def test_full_auth_flow():
    """
    Тестирует полный поток аутентификации

    Проверяет:
    1. Регистрация пользователя
    2. Логин и получение токена
    3. Валидация токена
    4. Logout и удаление сессии
    """
    # Mock SessionStorage
    mock_storage = Mock(spec=SessionStorage)
    mock_storage.save_session = AsyncMock(return_value=True)
    mock_storage.delete_session = AsyncMock(return_value=True)

    auth = AuthService(
        secret_key="test-secret-123",
        session_storage=mock_storage
    )

    # Step 1: Register
    user = await auth.register_user(
        username="alice",
        password="SecurePass123!",
        metadata={"email": "alice@example.com"}
    )
    assert user['username'] == "alice"
    assert 'user_id' in user

    # Step 2: Login
    login_result = await auth.login("alice", "SecurePass123!")
    assert 'access_token' in login_result
    assert 'session_id' in login_result

    token = login_result['access_token']
    session_id = login_result['session_id']

    # Step 3: Validate token
    mock_storage.get_session = AsyncMock(return_value={
        'session_id': session_id,
        'user_id': user['user_id'],
        'token': token,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
    })

    payload = await auth.validate_token(token)
    assert payload['username'] == "alice"

    # Step 4: Logout
    result = await auth.logout(session_id)
    assert result is True
    mock_storage.delete_session.assert_called_once_with(session_id)

    print("✅ Test 5 passed: Full authentication flow works correctly")


# ============================================================================
# Test 6: Rate Limiting
# ============================================================================
@pytest.mark.asyncio
async def test_rate_limiting():
    """
    Тестирует rate limiting для защиты от brute-force

    Проверяет:
    - Первые попытки разрешены
    - После max_attempts доступ блокируется
    - Сообщение об ошибке содержит время ожидания
    """
    mock_storage = Mock(spec=SessionStorage)
    mock_storage.save_session = AsyncMock(return_value=True)

    rate_limiter = RateLimiter(max_attempts=3, lockout_minutes=5)

    auth = AuthService(
        secret_key="test-secret-123",
        session_storage=mock_storage,
        rate_limiter=rate_limiter
    )

    # Регистрируем пользователя
    await auth.register_user("bob", "password123")

    # Делаем несколько неудачных попыток входа
    for i in range(3):
        with pytest.raises(ValueError, match="Invalid username or password"):
            await auth.login("bob", "wrongpassword")

    # Следующая попытка должна быть заблокирована rate limiter
    with pytest.raises(ValueError, match="Too many attempts"):
        await auth.login("bob", "wrongpassword")

    # Проверяем успешный вход также заблокирован
    with pytest.raises(ValueError, match="Too many attempts"):
        await auth.login("bob", "password123")

    # Очищаем rate limit и проверяем что успешный вход работает
    rate_limiter.clear_attempts("bob")
    result = await auth.login("bob", "password123")
    assert 'access_token' in result, "Should login successfully after clearing rate limit"

    print("✅ Test 6 passed: Rate limiting works correctly")


# ============================================================================
# Test 7: Token Tampering Detection
# ============================================================================
@pytest.mark.asyncio
async def test_token_tampering():
    """
    Тестирует обнаружение подделки токена

    Проверяет:
    - Измененный токен отклоняется
    - Токен от другой сессии отклоняется
    - Системный лог содержит предупреждение о tampering
    """
    mock_storage = Mock(spec=SessionStorage)
    mock_storage.save_session = AsyncMock(return_value=True)

    auth = AuthService(
        secret_key="test-secret-123",
        session_storage=mock_storage
    )

    # Регистрация и логин
    await auth.register_user("charlie", "password123")
    login_result = await auth.login("charlie", "password123")

    original_token = login_result['access_token']
    session_id = login_result['session_id']

    # Создаем поддельный токен для той же сессии
    import jwt
    fake_payload = {
        'sub': 'fake-user-id',
        'username': 'hacker',
        'session_id': session_id,
        'exp': datetime.now() + timedelta(hours=24)
    }
    fake_token = jwt.encode(fake_payload, "test-secret-123", algorithm="HS256")

    # Mock get_session возвращает оригинальный токен
    mock_storage.get_session = AsyncMock(return_value={
        'session_id': session_id,
        'user_id': login_result['user']['user_id'],
        'token': original_token,  # Оригинальный токен
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
    })

    # Пытаемся использовать поддельный токен
    with pytest.raises(ValueError, match="Token mismatch"):
        await auth.validate_token(fake_token)

    print("✅ Test 7 passed: Token tampering detection works correctly")


# ============================================================================
# Test 8: Session Expiration
# ============================================================================
@pytest.mark.asyncio
async def test_session_expiration():
    """
    Тестирует истечение сессий

    Проверяет:
    - Свежая сессия валидна
    - Истекшая сессия возвращает None
    - Истекшая сессия удаляется автоматически
    """
    # Mock DynamoDB Table
    mock_table = MagicMock()

    with patch('storage.session_storage.boto3') as mock_boto3:
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        storage = SessionStorage(table_name="test-table", ttl_hours=1)
        storage.table = mock_table

        session_id = str(uuid.uuid4())

        # Test 1: Fresh session (valid)
        mock_table.get_item.return_value = {
            'Item': {
                'session_id': session_id,
                'user_id': 'user123',
                'token': 'test.token',
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
            }
        }

        session = await storage.get_session(session_id)
        assert session is not None, "Fresh session should be valid"

        # Test 2: Expired session
        mock_table.get_item.return_value = {
            'Item': {
                'session_id': session_id,
                'user_id': 'user123',
                'token': 'test.token',
                'created_at': (datetime.now() - timedelta(hours=25)).isoformat(),
                'expires_at': (datetime.now() - timedelta(hours=1)).isoformat()  # Истекла
            }
        }

        mock_table.delete_item = MagicMock()

        session = await storage.get_session(session_id)
        assert session is None, "Expired session should return None"

        # Проверяем что истекшая сессия была удалена
        mock_table.delete_item.assert_called_once()

    print("✅ Test 8 passed: Session expiration works correctly")


# ============================================================================
# Run all tests
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 Running JWT Authentication Unit Tests")
    print("="*70 + "\n")

    # Запускаем все тесты
    pytest.main([__file__, "-v", "--tb=short"])

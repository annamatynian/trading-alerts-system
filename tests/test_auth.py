"""
Тесты для системы аутентификации
Проверяем регистрацию, вход, смену пароля и управление сессиями
"""
import pytest
import asyncio
from datetime import datetime, timedelta

from moto import mock_aws
import boto3

from models.user import User, UserCreate, UserLogin
from services.auth_service import AuthService
from storage.dynamodb_storage import DynamoDBStorage


@pytest.fixture
def aws_credentials(monkeypatch):
    """Мокируем AWS credentials для тестов"""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Создает мок DynamoDB таблицу для тестов"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='trading-signals',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield table


@pytest.fixture
def storage(dynamodb_table):
    """Создает DynamoDBStorage с мок-таблицей"""
    return DynamoDBStorage(table_name='trading-signals')


@pytest.fixture
def auth_service(storage):
    """Создает AuthService"""
    return AuthService(storage)


# ============================================================================
# ТЕСТЫ РЕГИСТРАЦИИ
# ============================================================================

@pytest.mark.asyncio
async def test_register_user(auth_service):
    """Тест: регистрация нового пользователя"""
    user_create = UserCreate(
        username="testuser",
        password="SecurePass123",
        email="test@example.com"
    )

    user = await auth_service.register_user(user_create)

    assert user is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.password_hash != "SecurePass123"  # Пароль должен быть хеширован
    assert user.is_active is True


@pytest.mark.asyncio
async def test_register_duplicate_username(auth_service):
    """Тест: нельзя зарегистрировать пользователя с существующим username"""
    user_create = UserCreate(
        username="testuser",
        password="SecurePass123"
    )

    # Первая регистрация успешна
    user1 = await auth_service.register_user(user_create)
    assert user1 is not None

    # Вторая регистрация с тем же username должна провалиться
    user2 = await auth_service.register_user(user_create)
    assert user2 is None


@pytest.mark.asyncio
async def test_register_weak_password(auth_service):
    """Тест: слабый пароль не принимается"""
    with pytest.raises(ValueError):
        UserCreate(
            username="testuser",
            password="weak"  # Слишком короткий, нет uppercase/digit
        )


# ============================================================================
# ТЕСТЫ ВХОДА
# ============================================================================

@pytest.mark.asyncio
async def test_login_success(auth_service):
    """Тест: успешный вход"""
    # Регистрируем пользователя
    user_create = UserCreate(
        username="testuser",
        password="SecurePass123"
    )
    await auth_service.register_user(user_create)

    # Логин
    user_login = UserLogin(username="testuser", password="SecurePass123")
    session = await auth_service.login(user_login)

    assert session is not None
    assert session.username == "testuser"
    assert session.session_id is not None
    assert session.expires_at is not None


@pytest.mark.asyncio
async def test_login_wrong_password(auth_service):
    """Тест: вход с неверным паролем"""
    # Регистрируем пользователя
    user_create = UserCreate(
        username="testuser",
        password="SecurePass123"
    )
    await auth_service.register_user(user_create)

    # Логин с неверным паролем
    user_login = UserLogin(username="testuser", password="WrongPassword123")
    session = await auth_service.login(user_login)

    assert session is None


@pytest.mark.asyncio
async def test_login_nonexistent_user(auth_service):
    """Тест: вход несуществующего пользователя"""
    user_login = UserLogin(username="nonexistent", password="SecurePass123")
    session = await auth_service.login(user_login)

    assert session is None


# ============================================================================
# ТЕСТЫ СЕССИЙ
# ============================================================================

@pytest.mark.asyncio
async def test_session_validation(auth_service):
    """Тест: валидация сессии"""
    # Регистрируем и логинимся
    user_create = UserCreate(username="testuser", password="SecurePass123")
    await auth_service.register_user(user_create)

    user_login = UserLogin(username="testuser", password="SecurePass123")
    session = await auth_service.login(user_login)

    # Валидируем сессию
    username = auth_service.validate_session(session.session_id)
    assert username == "testuser"


@pytest.mark.asyncio
async def test_session_logout(auth_service):
    """Тест: выход из системы"""
    # Регистрируем и логинимся
    user_create = UserCreate(username="testuser", password="SecurePass123")
    await auth_service.register_user(user_create)

    user_login = UserLogin(username="testuser", password="SecurePass123")
    session = await auth_service.login(user_login)

    # Выходим
    result = auth_service.logout(session.session_id)
    assert result is True

    # Сессия больше не валидна
    username = auth_service.validate_session(session.session_id)
    assert username is None


@pytest.mark.asyncio
async def test_session_expiration(auth_service):
    """Тест: истечение сессии"""
    # Регистрируем и логинимся
    user_create = UserCreate(username="testuser", password="SecurePass123")
    await auth_service.register_user(user_create)

    user_login = UserLogin(username="testuser", password="SecurePass123")
    session = await auth_service.login(user_login)

    # Принудительно делаем сессию истекшей
    session.expires_at = datetime.now() - timedelta(hours=1)
    auth_service.sessions[session.session_id] = session

    # Проверяем что сессия невалидна
    username = auth_service.validate_session(session.session_id)
    assert username is None


# ============================================================================
# ТЕСТЫ СМЕНЫ ПАРОЛЯ
# ============================================================================

@pytest.mark.asyncio
async def test_change_password_success(auth_service):
    """Тест: успешная смена пароля"""
    # Регистрируем пользователя
    user_create = UserCreate(username="testuser", password="OldPass123")
    await auth_service.register_user(user_create)

    # Меняем пароль
    result = await auth_service.change_password(
        username="testuser",
        old_password="OldPass123",
        new_password="NewPass456"
    )
    assert result is True

    # Проверяем что старый пароль не работает
    old_login = UserLogin(username="testuser", password="OldPass123")
    session = await auth_service.login(old_login)
    assert session is None

    # Проверяем что новый пароль работает
    new_login = UserLogin(username="testuser", password="NewPass456")
    session = await auth_service.login(new_login)
    assert session is not None


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(auth_service):
    """Тест: смена пароля с неверным старым паролем"""
    # Регистрируем пользователя
    user_create = UserCreate(username="testuser", password="OldPass123")
    await auth_service.register_user(user_create)

    # Пытаемся сменить пароль с неверным старым паролем
    result = await auth_service.change_password(
        username="testuser",
        old_password="WrongPass123",
        new_password="NewPass456"
    )
    assert result is False


# ============================================================================
# ТЕСТЫ ХЕШИРОВАНИЯ ПАРОЛЕЙ
# ============================================================================

def test_password_hashing(auth_service):
    """Тест: хеширование паролей"""
    password = "SecurePass123"

    # Хешируем
    password_hash = auth_service.hash_password(password)

    # Проверяем что хеш не равен оригинальному паролю
    assert password_hash != password

    # Проверяем что можем верифицировать
    assert auth_service.verify_password(password, password_hash) is True

    # Проверяем что неверный пароль не проходит
    assert auth_service.verify_password("WrongPass", password_hash) is False


def test_password_salt_randomness(auth_service):
    """Тест: каждый хеш использует уникальную соль"""
    password = "SecurePass123"

    hash1 = auth_service.hash_password(password)
    hash2 = auth_service.hash_password(password)

    # Хеши должны быть разными (разная соль)
    assert hash1 != hash2

    # Но оба должны верифицироваться
    assert auth_service.verify_password(password, hash1) is True
    assert auth_service.verify_password(password, hash2) is True


# ============================================================================
# ТЕСТЫ ИЗОЛЯЦИИ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

@pytest.mark.asyncio
async def test_user_isolation(auth_service):
    """Тест: пользователи изолированы друг от друга"""
    # Регистрируем двух пользователей
    user1_create = UserCreate(username="alice", password="AlicePass123")
    user2_create = UserCreate(username="bob", password="BobPass123")

    await auth_service.register_user(user1_create)
    await auth_service.register_user(user2_create)

    # Логинимся обоими
    alice_login = UserLogin(username="alice", password="AlicePass123")
    bob_login = UserLogin(username="bob", password="BobPass123")

    alice_session = await auth_service.login(alice_login)
    bob_session = await auth_service.login(bob_login)

    # Проверяем что сессии разные
    assert alice_session.session_id != bob_session.session_id
    assert alice_session.username == "alice"
    assert bob_session.username == "bob"

    # Проверяем что Alice не может использовать сессию Bob
    alice_username = auth_service.validate_session(alice_session.session_id)
    assert alice_username == "alice"

    bob_username = auth_service.validate_session(bob_session.session_id)
    assert bob_username == "bob"


# ============================================================================
# ТЕСТЫ ОБНОВЛЕНИЯ ПРОФИЛЯ
# ============================================================================

@pytest.mark.asyncio
async def test_update_user_profile(auth_service):
    """Тест: обновление профиля пользователя"""
    # Регистрируем пользователя
    user_create = UserCreate(username="testuser", password="SecurePass123")
    await auth_service.register_user(user_create)

    # Обновляем профиль
    updates = {
        'email': 'newemail@example.com',
        'full_name': 'Test User',
        'pushover_key': 'test_pushover_key'
    }

    result = await auth_service.update_user_profile("testuser", updates)
    assert result is True

    # Проверяем что обновления сохранены
    user = await auth_service.storage.get_user("testuser")
    assert user.email == "newemail@example.com"
    assert user.full_name == "Test User"
    assert user.pushover_key == "test_pushover_key"


# ============================================================================
# ТЕСТЫ ОЧИСТКИ СЕССИЙ
# ============================================================================

@pytest.mark.asyncio
async def test_cleanup_expired_sessions(auth_service):
    """Тест: очистка истекших сессий"""
    # Создаем несколько пользователей и логиним
    for i in range(3):
        user_create = UserCreate(username=f"user{i}", password="SecurePass123")
        await auth_service.register_user(user_create)

        user_login = UserLogin(username=f"user{i}", password="SecurePass123")
        session = await auth_service.login(user_login)

        # Делаем 2 сессии истекшими
        if i < 2:
            session.expires_at = datetime.now() - timedelta(hours=1)
            auth_service.sessions[session.session_id] = session

    # Очищаем истекшие сессии
    cleaned = auth_service.cleanup_expired_sessions()

    # Должно быть очищено 2 сессии
    assert cleaned == 2

    # Должна остаться 1 активная сессия
    assert len(auth_service.sessions) == 1

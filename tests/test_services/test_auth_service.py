"""
Юнит-тесты для AuthService
Проверяем управление Pushover ключами пользователей
"""
import pytest
import asyncio
from moto import mock_aws
import boto3

from services.auth_service import AuthService
from storage.dynamodb_storage import DynamoDBStorage
from storage.session_storage import SessionStorage


@pytest.fixture(scope='function')
def aws_credentials(monkeypatch):
    """Мокируем AWS credentials для тестов"""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


@pytest.fixture(scope='function')
def mock_dynamodb(aws_credentials):
    """Активирует mock_aws для каждого теста"""
    with mock_aws():
        yield


@pytest.fixture
def dynamodb_table(mock_dynamodb):
    """Создает мок DynamoDB таблицу для тестов"""
    # Создаем таблицу внутри активного mock_aws context
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='auth-test',
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
    """Создает DynamoDBStorage"""
    return DynamoDBStorage(table_name='auth-test', region='us-east-1')


@pytest.fixture
def session_storage(dynamodb_table):
    """Создает SessionStorage"""
    return SessionStorage(table_name='auth-test', region='us-east-1')


@pytest.fixture
async def auth_service(session_storage, storage):
    """Создает AuthService"""
    service = AuthService(
        session_storage=session_storage,
        secret_key='test-secret-key',
        user_storage=storage
    )
    await service.load_users_from_storage()
    return service


@pytest.mark.asyncio
async def test_register_user_and_set_pushover_key(auth_service):
    """Тест: регистрация пользователя и установка Pushover ключа"""
    # 1. Регистрируем пользователя
    user = await auth_service.register_user('testuser', 'password123')
    assert user is not None
    assert user.username == 'testuser'
    assert user.pushover_key is None  # Изначально ключа нет

    # 2. Устанавливаем Pushover ключ
    success = await auth_service.update_pushover_key('testuser', 'user-pushover-key-abc')
    assert success is True

    # 3. Проверяем что ключ сохранился
    pushover_key = auth_service.get_pushover_key('testuser')
    assert pushover_key == 'user-pushover-key-abc'


@pytest.mark.asyncio
async def test_update_existing_pushover_key(auth_service):
    """Тест: обновление существующего Pushover ключа"""
    # Регистрируем и устанавливаем начальный ключ
    await auth_service.register_user('testuser', 'password123')
    await auth_service.update_pushover_key('testuser', 'old-key-111')

    # Проверяем начальный ключ
    assert auth_service.get_pushover_key('testuser') == 'old-key-111'

    # Обновляем ключ
    success = await auth_service.update_pushover_key('testuser', 'new-key-222')
    assert success is True

    # Проверяем что ключ обновился
    assert auth_service.get_pushover_key('testuser') == 'new-key-222'


@pytest.mark.asyncio
async def test_get_pushover_key_nonexistent_user(auth_service):
    """Тест: получение ключа для несуществующего пользователя"""
    pushover_key = auth_service.get_pushover_key('nonexistent-user')
    assert pushover_key is None


@pytest.mark.asyncio
async def test_update_pushover_key_nonexistent_user(auth_service):
    """Тест: попытка обновить ключ для несуществующего пользователя"""
    success = await auth_service.update_pushover_key('nonexistent-user', 'some-key')
    assert success is False


@pytest.mark.asyncio
async def test_pushover_key_persistence(auth_service, storage):
    """Тест: Pushover ключ сохраняется в DynamoDB и загружается обратно"""
    # 1. Создаем пользователя и устанавливаем ключ
    await auth_service.register_user('persistuser', 'password123')
    await auth_service.update_pushover_key('persistuser', 'persist-key-789')

    # 2. Проверяем что ключ в памяти
    assert auth_service.get_pushover_key('persistuser') == 'persist-key-789'

    # 3. Создаем новый AuthService и загружаем пользователей из DynamoDB
    new_auth_service = AuthService(
        session_storage=auth_service.session_storage,
        secret_key='test-secret-key',
        user_storage=storage
    )
    await new_auth_service.load_users_from_storage()

    # 4. Проверяем что ключ загрузился из DynamoDB
    assert new_auth_service.get_pushover_key('persistuser') == 'persist-key-789'


@pytest.mark.asyncio
async def test_delete_user_removes_pushover_key(auth_service):
    """Тест: удаление пользователя удаляет и Pushover ключ"""
    # 1. Создаем пользователя с ключом
    await auth_service.register_user('deleteuser', 'password123')
    await auth_service.update_pushover_key('deleteuser', 'delete-key-456')

    # 2. Проверяем что ключ существует
    assert auth_service.get_pushover_key('deleteuser') == 'delete-key-456'

    # 3. Удаляем пользователя
    success = await auth_service.delete_user('deleteuser')
    assert success is True

    # 4. Проверяем что ключ больше не доступен
    assert auth_service.get_pushover_key('deleteuser') is None


@pytest.mark.asyncio
async def test_multiple_users_different_keys(auth_service):
    """Тест: разные пользователи имеют разные Pushover ключи"""
    # Создаем трех пользователей с разными ключами
    await auth_service.register_user('alice', 'password1')
    await auth_service.register_user('bob', 'password2')
    await auth_service.register_user('charlie', 'password3')

    await auth_service.update_pushover_key('alice', 'alice-key-111')
    await auth_service.update_pushover_key('bob', 'bob-key-222')
    await auth_service.update_pushover_key('charlie', 'charlie-key-333')

    # Проверяем что каждый пользователь имеет свой ключ
    assert auth_service.get_pushover_key('alice') == 'alice-key-111'
    assert auth_service.get_pushover_key('bob') == 'bob-key-222'
    assert auth_service.get_pushover_key('charlie') == 'charlie-key-333'

    # Проверяем изоляцию ключей
    assert auth_service.get_pushover_key('alice') != auth_service.get_pushover_key('bob')
    assert auth_service.get_pushover_key('bob') != auth_service.get_pushover_key('charlie')


@pytest.mark.asyncio
async def test_empty_pushover_key(auth_service):
    """Тест: пустой Pushover ключ обрабатывается корректно"""
    await auth_service.register_user('emptyuser', 'password123')

    # Пользователь без ключа
    assert auth_service.get_pushover_key('emptyuser') is None

    # Устанавливаем пустую строку
    await auth_service.update_pushover_key('emptyuser', '')

    # Пустая строка считается как отсутствие ключа
    key = auth_service.get_pushover_key('emptyuser')
    assert key == '' or key is None


@pytest.mark.asyncio
async def test_pushover_key_in_user_data_storage(auth_service, storage):
    """
    Тест: Pushover ключ доступен через storage.get_user_data()
    Это критично для NotificationService
    """
    # Создаем пользователя и устанавливаем ключ
    await auth_service.register_user('storageuser', 'password123')
    await auth_service.update_pushover_key('storageuser', 'storage-key-555')

    # Получаем данные пользователя через storage
    user_data = await storage.get_user_data('storageuser')

    # Проверяем что pushover_key присутствует в данных
    assert 'pushover_key' in user_data
    assert user_data['pushover_key'] == 'storage-key-555'

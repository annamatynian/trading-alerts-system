"""
Интеграционные тесты для полного flow Pushover
Проверяем: DynamoDB Storage → NotificationService → Pushover API
"""
import pytest
import asyncio
from moto import mock_aws
import boto3
from aioresponses import aioresponses

from models.signal import SignalTarget, SignalResult, ExchangeType, SignalCondition
from storage.dynamodb_storage import DynamoDBStorage
from services.notification import NotificationService
from utils.config import NotificationConfig


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
        # Создаем таблицу
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='trading-alerts-test',
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
    return DynamoDBStorage(table_name='trading-alerts-test')


@pytest.fixture
def notification_config():
    """Конфигурация для NotificationService"""
    return NotificationConfig(
        pushover_enabled=True,
        pushover_api_token='test-app-token-integration'
    )


@pytest.fixture
async def notification_service(notification_config, storage):
    """Создает NotificationService с реальным storage"""
    service = NotificationService(notification_config, storage)
    await service.initialize()
    yield service
    await service.close()


@pytest.mark.asyncio
async def test_full_pushover_flow_with_storage(storage, notification_service):
    """
    Интеграционный тест: полный flow от сохранения ключа до отправки уведомления
    1. Сохраняем Pushover ключ пользователя в DynamoDB
    2. Создаем сигнал для этого пользователя
    3. Отправляем уведомление (сервис загружает ключ из DynamoDB)
    4. Проверяем что Pushover API был вызван с правильными данными
    """
    # 1. Сохраняем данные пользователя с Pushover ключом
    user_id = 'integration-test-user'
    user_data = {
        'pushover_key': 'integration-user-key-789',
        'username': 'integrationuser',
        'email': 'test@integration.com'
    }

    save_result = await storage.save_user_data(user_id, user_data)
    assert save_result is True

    # 2. Проверяем что данные сохранились
    loaded_data = await storage.get_user_data(user_id)
    assert loaded_data['pushover_key'] == 'integration-user-key-789'

    # 3. Создаем сигнал для этого пользователя
    signal = SignalTarget(
        id='integration-signal-1',
        name='Integration Test Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id=user_id
    )

    result = SignalResult(
        signal=signal,
        current_price=101000.0,
        triggered=True
    )

    # 4. Мокируем Pushover API и отправляем уведомление
    with aioresponses() as mocked:
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 1, 'request': 'integration-test-request'},
            status=200
        )

        # Отправляем уведомление (должен автоматически загрузить ключ из storage)
        await notification_service.send_alert_notification(result)

        # 5. Проверяем что запрос был сделан
        assert len(mocked.requests) == 1

        # 6. Проверяем payload запроса
        request_data = list(mocked.requests.values())[0][0].kwargs['data']

        assert request_data['token'] == 'test-app-token-integration'
        assert request_data['user'] == 'integration-user-key-789'  # Ключ из DynamoDB
        assert 'Integration Test Alert' in request_data['title']
        assert 'BTCUSDT' in request_data['message']
        assert '101,000.0000' in request_data['message']


@pytest.mark.asyncio
async def test_multiple_users_isolated_notifications(storage, notification_service):
    """
    Интеграционный тест: изоляция пользователей
    Проверяем что каждый пользователь получает уведомления только на свой ключ
    """
    # Создаем двух пользователей с разными ключами
    await storage.save_user_data('alice', {'pushover_key': 'alice-key-123'})
    await storage.save_user_data('bob', {'pushover_key': 'bob-key-456'})

    # Создаем сигналы для обоих пользователей
    alice_signal = SignalTarget(
        id='alice-signal',
        name='Alice BTC Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id='alice'
    )

    bob_signal = SignalTarget(
        id='bob-signal',
        name='Bob ETH Alert',
        exchange=ExchangeType.BYBIT,
        symbol='ETHUSDT',
        condition=SignalCondition.BELOW,
        target_price=5000.0,
        active=True,
        user_id='bob'
    )

    alice_result = SignalResult(signal=alice_signal, current_price=101000.0, triggered=True)
    bob_result = SignalResult(signal=bob_signal, current_price=4900.0, triggered=True)

    # Мокируем Pushover API
    with aioresponses() as mocked:
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 1},
            status=200,
            repeat=True
        )

        # Отправляем уведомления
        await notification_service.send_alert_notification(alice_result)
        await notification_service.send_alert_notification(bob_result)

        # Проверяем что были 2 запроса
        assert len(mocked.requests) == 2

        # Проверяем изоляцию ключей
        requests = list(mocked.requests.values())

        alice_request = requests[0][0].kwargs['data']
        bob_request = requests[1][0].kwargs['data']

        # Alice получает уведомление на свой ключ
        assert alice_request['user'] == 'alice-key-123'
        assert 'Alice BTC Alert' in alice_request['title']

        # Bob получает уведомление на свой ключ
        assert bob_request['user'] == 'bob-key-456'
        assert 'Bob ETH Alert' in bob_request['title']


@pytest.mark.asyncio
async def test_update_user_pushover_key(storage, notification_service):
    """
    Интеграционный тест: обновление Pushover ключа пользователя
    Проверяем что после обновления используется новый ключ
    """
    user_id = 'changeable-user'

    # 1. Сохраняем начальный ключ
    await storage.save_user_data(user_id, {'pushover_key': 'old-key-111'})

    # 2. Создаем сигнал
    signal = SignalTarget(
        id='test-signal',
        name='Test Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id=user_id
    )
    result = SignalResult(signal=signal, current_price=101000.0, triggered=True)

    # 3. Отправляем уведомление со старым ключом
    with aioresponses() as mocked:
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 1},
            status=200
        )

        await notification_service.send_alert_notification(result)

        old_request = list(mocked.requests.values())[0][0].kwargs['data']
        assert old_request['user'] == 'old-key-111'

    # 4. Обновляем ключ пользователя
    await storage.save_user_data(user_id, {'pushover_key': 'new-key-222'})

    # 5. Проверяем что ключ обновился
    updated_data = await storage.get_user_data(user_id)
    assert updated_data['pushover_key'] == 'new-key-222'

    # 6. Отправляем уведомление с новым ключом
    with aioresponses() as mocked:
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 1},
            status=200
        )

        await notification_service.send_alert_notification(result)

        new_request = list(mocked.requests.values())[0][0].kwargs['data']
        assert new_request['user'] == 'new-key-222'  # Теперь используется новый ключ


@pytest.mark.asyncio
async def test_user_without_pushover_key_gets_no_notification(storage, notification_service):
    """
    Интеграционный тест: пользователь без Pushover ключа не получает уведомления
    """
    user_id = 'no-key-user'

    # Сохраняем пользователя БЕЗ pushover_key
    await storage.save_user_data(user_id, {
        'username': 'nokeyuser',
        'email': 'nokey@test.com'
        # pushover_key отсутствует
    })

    # Создаем сигнал для этого пользователя
    signal = SignalTarget(
        id='test-signal',
        name='Test Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id=user_id
    )
    result = SignalResult(signal=signal, current_price=101000.0, triggered=True)

    # Пытаемся отправить уведомление
    with aioresponses() as mocked:
        await notification_service.send_alert_notification(result)

        # Проверяем что запрос к Pushover НЕ был сделан
        assert len(mocked.requests) == 0


@pytest.mark.asyncio
async def test_signal_save_and_notification_flow(storage, notification_service):
    """
    Интеграционный тест: полный flow с сохранением сигнала в DynamoDB
    1. Сохраняем пользователя с ключом
    2. Сохраняем сигнал в DynamoDB
    3. Загружаем сигнал
    4. Отправляем уведомление
    """
    user_id = 'full-flow-user'

    # 1. Сохраняем пользователя
    await storage.save_user_data(user_id, {'pushover_key': 'full-flow-key-999'})

    # 2. Создаем и сохраняем сигнал
    signal = SignalTarget(
        id='full-flow-signal',
        name='Full Flow Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id=user_id
    )

    save_result = await storage.save_signal(signal)
    assert save_result is True

    # 3. Загружаем сигналы из DynamoDB
    signals = await storage.load_signals()
    assert len(signals) == 1
    loaded_signal = signals[0]
    assert loaded_signal.user_id == user_id

    # 4. Создаем результат и отправляем уведомление
    result = SignalResult(signal=loaded_signal, current_price=101000.0, triggered=True)

    with aioresponses() as mocked:
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 1},
            status=200
        )

        await notification_service.send_alert_notification(result)

        # Проверяем что уведомление отправлено
        assert len(mocked.requests) == 1

        request_data = list(mocked.requests.values())[0][0].kwargs['data']
        assert request_data['user'] == 'full-flow-key-999'
        assert 'Full Flow Alert' in request_data['title']

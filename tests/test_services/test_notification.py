"""
Юнит-тесты для NotificationService
Проверяем работу с Pushover API
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from aioresponses import aioresponses

from models.signal import SignalTarget, SignalResult, ExchangeType, SignalCondition
from services.notification import NotificationService
from utils.config import NotificationConfig


@pytest.fixture
def notification_config():
    """Создаем конфигурацию для уведомлений"""
    return NotificationConfig(
        pushover_enabled=True,
        pushover_api_token='test-app-token-123'
    )


@pytest.fixture
def mock_storage():
    """Мокируем storage"""
    storage = AsyncMock()
    storage.get_user_data = AsyncMock(return_value={
        'pushover_key': 'test-user-key-456',
        'username': 'testuser'
    })
    return storage


@pytest.fixture
async def notification_service(notification_config, mock_storage):
    """Создаем NotificationService"""
    service = NotificationService(notification_config, mock_storage)
    await service.initialize()
    yield service
    await service.close()


@pytest.fixture
def sample_signal_result():
    """Создаем тестовый SignalResult"""
    signal = SignalTarget(
        id='signal-123',
        name='BTC Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id='testuser'
    )

    return SignalResult(
        signal=signal,
        current_price=100500.0,
        triggered=True,
        timestamp=None
    )


@pytest.mark.asyncio
async def test_notification_service_initialization(notification_config, mock_storage):
    """Тест: инициализация сервиса с Pushover token"""
    service = NotificationService(notification_config, mock_storage)
    await service.initialize()

    assert service.pushover_api_token == 'test-app-token-123'
    assert service._session is not None

    await service.close()


@pytest.mark.asyncio
async def test_send_pushover_alert_success(notification_service, sample_signal_result):
    """Тест: успешная отправка уведомления через Pushover"""
    with aioresponses() as mocked:
        # Мокируем успешный ответ от Pushover API
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 1, 'request': 'test-request-id'},
            status=200
        )

        # Отправляем уведомление
        await notification_service.send_pushover_alert(
            sample_signal_result,
            'test-user-key-456'
        )

        # Проверяем что запрос был сделан
        assert len(mocked.requests) == 1

        # Получаем данные запроса
        request_data = list(mocked.requests.values())[0][0].kwargs['data']

        # Проверяем payload
        assert request_data['token'] == 'test-app-token-123'
        assert request_data['user'] == 'test-user-key-456'
        assert 'BTC Alert' in request_data['title']
        assert 'BTCUSDT' in request_data['message']
        assert '100,500.0000' in request_data['message']
        assert request_data['priority'] == 2  # Emergency priority


@pytest.mark.asyncio
async def test_send_pushover_alert_api_error(notification_service, sample_signal_result):
    """Тест: обработка ошибки от Pushover API"""
    with aioresponses() as mocked:
        # Мокируем ошибку от Pushover API
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 0, 'errors': ['invalid user key']},
            status=400
        )

        # Отправляем уведомление (не должно упасть)
        await notification_service.send_pushover_alert(
            sample_signal_result,
            'invalid-key'
        )

        # Проверяем что запрос был сделан
        assert len(mocked.requests) == 1


@pytest.mark.asyncio
async def test_send_alert_notification_fetches_user_key(notification_service, sample_signal_result, mock_storage):
    """Тест: получение Pushover ключа пользователя из storage"""
    with aioresponses() as mocked:
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 1},
            status=200
        )

        # Отправляем уведомление (должен загрузить ключ из storage)
        await notification_service.send_alert_notification(sample_signal_result)

        # Проверяем что get_user_data был вызван
        mock_storage.get_user_data.assert_called_once_with('testuser')

        # Проверяем что запрос к Pushover был сделан с правильным ключом
        request_data = list(mocked.requests.values())[0][0].kwargs['data']
        assert request_data['user'] == 'test-user-key-456'


@pytest.mark.asyncio
async def test_send_alert_notification_no_user_key(notification_service, sample_signal_result, mock_storage):
    """Тест: обработка случая когда у пользователя нет Pushover ключа"""
    # Мокируем storage без pushover_key
    mock_storage.get_user_data = AsyncMock(return_value={
        'username': 'testuser'
        # pushover_key отсутствует
    })

    with aioresponses() as mocked:
        # Отправляем уведомление
        await notification_service.send_alert_notification(sample_signal_result)

        # Проверяем что запрос к Pushover НЕ был сделан
        assert len(mocked.requests) == 0


@pytest.mark.asyncio
async def test_send_alert_notification_no_user_id(notification_service):
    """Тест: обработка сигнала без user_id"""
    signal = SignalTarget(
        id='signal-123',
        name='BTC Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id=None  # Нет user_id
    )

    result = SignalResult(
        signal=signal,
        current_price=100500.0,
        triggered=True,
        timestamp=None
    )

    with aioresponses() as mocked:
        # Отправляем уведомление
        await notification_service.send_alert_notification(result)

        # Проверяем что запрос к Pushover НЕ был сделан
        assert len(mocked.requests) == 0


@pytest.mark.asyncio
async def test_notification_service_disabled(mock_storage):
    """Тест: сервис с отключенным Pushover"""
    disabled_config = NotificationConfig(
        pushover_enabled=False,
        pushover_api_token=None
    )

    service = NotificationService(disabled_config, mock_storage)
    await service.initialize()

    assert service.pushover_api_token is None
    assert service._session is None

    await service.close()


@pytest.mark.asyncio
async def test_multiple_users_get_different_notifications(notification_service):
    """Тест: разные пользователи получают уведомления на свои ключи"""
    # Создаем двух пользователей
    user1_signal = SignalTarget(
        id='signal-1',
        name='User1 Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id='user1'
    )

    user2_signal = SignalTarget(
        id='signal-2',
        name='User2 Alert',
        exchange=ExchangeType.BYBIT,
        symbol='ETHUSDT',
        condition=SignalCondition.BELOW,
        target_price=5000.0,
        active=True,
        user_id='user2'
    )

    result1 = SignalResult(signal=user1_signal, current_price=100500.0, triggered=True)
    result2 = SignalResult(signal=user2_signal, current_price=4900.0, triggered=True)

    # Мокируем разные ключи для разных пользователей
    async def mock_get_user_data(user_id):
        if user_id == 'user1':
            return {'pushover_key': 'user1-key-abc'}
        elif user_id == 'user2':
            return {'pushover_key': 'user2-key-xyz'}
        return {}

    notification_service.storage.get_user_data = mock_get_user_data

    with aioresponses() as mocked:
        # Мокируем успешные ответы
        mocked.post(
            NotificationService.PUSHOVER_API_URL,
            payload={'status': 1},
            status=200,
            repeat=True
        )

        # Отправляем уведомления обоим пользователям
        await notification_service.send_alert_notification(result1)
        await notification_service.send_alert_notification(result2)

        # Проверяем что были 2 запроса
        assert len(mocked.requests) == 2

        # Проверяем что запросы использовали разные ключи
        requests = list(mocked.requests.values())
        user1_request_data = requests[0][0].kwargs['data']
        user2_request_data = requests[1][0].kwargs['data']

        assert user1_request_data['user'] == 'user1-key-abc'
        assert user2_request_data['user'] == 'user2-key-xyz'

        # Проверяем что уведомления содержат правильные данные
        assert 'User1 Alert' in user1_request_data['title']
        assert 'User2 Alert' in user2_request_data['title']
        assert 'BTCUSDT' in user1_request_data['message']
        assert 'ETHUSDT' in user2_request_data['message']

"""
Тесты для Pushover Notification Service
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.notification import NotificationService
from models.signal import SignalTarget, SignalResult, ExchangeType, SignalCondition
from utils.config import NotificationConfig


@pytest.fixture
def notification_config_enabled():
    """Config with Pushover enabled"""
    return NotificationConfig(
        pushover_enabled=True,
        pushover_api_token='test-api-token-123'
    )


@pytest.fixture
def notification_config_disabled():
    """Config with Pushover disabled"""
    return NotificationConfig(
        pushover_enabled=False
    )


@pytest.fixture
def mock_storage():
    """Mock storage with user data"""
    storage = AsyncMock()
    storage.get_user_data = AsyncMock(return_value={
        'pushover_key': 'test-user-key-456',
        'email': 'test@example.com'
    })
    return storage


@pytest.fixture
def sample_signal():
    """Sample signal for testing"""
    return SignalTarget(
        id='test-signal-1',
        name='BTC Alert',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id='test-user'
    )


@pytest.fixture
def sample_signal_result(sample_signal):
    """Sample signal result for testing"""
    return SignalResult(
        signal=sample_signal,
        current_price=101000.0,
        triggered=True,
        trigger_reason='Price above target'
    )


@pytest.mark.asyncio
async def test_initialize_with_pushover_enabled(notification_config_enabled, mock_storage):
    """Test: инициализация с включенным Pushover"""
    service = NotificationService(notification_config_enabled, mock_storage)

    await service.initialize()

    assert service.pushover_api_token == 'test-api-token-123'
    assert service._session is not None

    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_initialize_without_pushover(notification_config_disabled, mock_storage):
    """Test: инициализация с выключенным Pushover"""
    service = NotificationService(notification_config_disabled, mock_storage)

    await service.initialize()

    assert service.pushover_api_token is None
    assert service._session is None


@pytest.mark.asyncio
async def test_send_alert_notification_success(notification_config_enabled, mock_storage, sample_signal_result):
    """Test: успешная отправка уведомления"""
    service = NotificationService(notification_config_enabled, mock_storage)
    await service.initialize()

    # Mock the send_pushover_alert method
    service.send_pushover_alert = AsyncMock()

    await service.send_alert_notification(sample_signal_result)

    # Verify storage was queried for user data
    mock_storage.get_user_data.assert_called_once_with('test-user')

    # Verify Pushover alert was sent
    service.send_pushover_alert.assert_called_once()
    call_args = service.send_pushover_alert.call_args
    assert call_args[0][0] == sample_signal_result  # First arg is result
    assert call_args[0][1] == 'test-user-key-456'   # Second arg is user_key

    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_send_alert_notification_no_user_id(notification_config_enabled, mock_storage, sample_signal):
    """Test: отправка уведомления без user_id"""
    # Create signal without user_id
    signal_no_user = SignalTarget(
        id='test-signal-2',
        name='BTC Alert No User',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id=None
    )

    result = SignalResult(
        signal=signal_no_user,
        current_price=101000.0,
        triggered=True
    )

    service = NotificationService(notification_config_enabled, mock_storage)
    await service.initialize()

    service.send_pushover_alert = AsyncMock()

    await service.send_alert_notification(result)

    # Verify storage was NOT queried
    mock_storage.get_user_data.assert_not_called()

    # Verify Pushover alert was NOT sent
    service.send_pushover_alert.assert_not_called()

    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_send_alert_notification_no_pushover_key(notification_config_enabled, sample_signal_result):
    """Test: отправка уведомления когда у пользователя нет pushover_key"""
    # Create storage that returns empty user data
    storage = AsyncMock()
    storage.get_user_data = AsyncMock(return_value={})

    service = NotificationService(notification_config_enabled, storage)
    await service.initialize()

    service.send_pushover_alert = AsyncMock()

    await service.send_alert_notification(sample_signal_result)

    # Verify storage was queried
    storage.get_user_data.assert_called_once_with('test-user')

    # Verify Pushover alert was NOT sent (no user key)
    service.send_pushover_alert.assert_not_called()

    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_send_pushover_alert_success(notification_config_enabled, mock_storage, sample_signal_result):
    """Test: успешная отправка через Pushover API"""
    service = NotificationService(notification_config_enabled, mock_storage)
    await service.initialize()

    # Mock aiohttp session response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={'status': 1})

    # Patch the session.post method
    with patch.object(service._session, 'post') as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_response

        await service.send_pushover_alert(sample_signal_result, 'test-user-key-456')

        # Verify API was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Verify URL
        assert call_args[0][0] == NotificationService.PUSHOVER_API_URL

        # Verify payload
        payload = call_args[1]['data']
        assert payload['token'] == 'test-api-token-123'
        assert payload['user'] == 'test-user-key-456'
        assert 'BTC Alert' in payload['title']
        assert 'BTCUSDT' in payload['message']
        assert '$101,000.0000' in payload['message']
        assert payload['priority'] == 2  # Emergency priority
        assert payload['sound'] == 'persistent'

    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_send_pushover_alert_api_error(notification_config_enabled, mock_storage, sample_signal_result):
    """Test: ошибка Pushover API"""
    service = NotificationService(notification_config_enabled, mock_storage)
    await service.initialize()

    # Mock aiohttp session response with error
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.json = AsyncMock(return_value={'status': 0, 'errors': ['invalid user key']})

    with patch.object(service._session, 'post') as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_response

        # Should not raise exception, just log error
        await service.send_pushover_alert(sample_signal_result, 'invalid-key')

        mock_post.assert_called_once()

    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_send_pushover_alert_network_error(notification_config_enabled, mock_storage, sample_signal_result):
    """Test: сетевая ошибка при отправке"""
    service = NotificationService(notification_config_enabled, mock_storage)
    await service.initialize()

    # Mock network error
    with patch.object(service._session, 'post') as mock_post:
        mock_post.side_effect = Exception('Network error')

        # Should not raise exception, just log error
        await service.send_pushover_alert(sample_signal_result, 'test-user-key-456')

        mock_post.assert_called_once()

    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_close_session(notification_config_enabled, mock_storage):
    """Test: закрытие aiohttp session"""
    service = NotificationService(notification_config_enabled, mock_storage)
    await service.initialize()

    assert service._session is not None

    await service.close()

    # Session should be closed (we can't easily verify this without mocking)
    # But at least verify close() doesn't raise exceptions


@pytest.mark.asyncio
async def test_send_alert_without_initialization(notification_config_enabled, mock_storage, sample_signal_result):
    """Test: попытка отправки без инициализации"""
    service = NotificationService(notification_config_enabled, mock_storage)
    # Don't call initialize()

    # Should handle gracefully (token is None)
    await service.send_alert_notification(sample_signal_result)

    # Verify storage was queried
    mock_storage.get_user_data.assert_called_once()


@pytest.mark.asyncio
async def test_message_formatting(notification_config_enabled, mock_storage, sample_signal_result):
    """Test: проверка форматирования сообщения"""
    service = NotificationService(notification_config_enabled, mock_storage)
    await service.initialize()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={'status': 1})

    with patch.object(service._session, 'post') as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_response

        await service.send_pushover_alert(sample_signal_result, 'test-user-key')

        payload = mock_post.call_args[1]['data']

        # Verify message contains all required info
        assert 'Symbol: BTCUSDT' in payload['message']
        assert 'Exchange: BINANCE' in payload['message']
        assert 'Current Price:' in payload['message']
        assert 'Target:' in payload['message']

        # Verify title format
        assert '🚨 Alert: BTC Alert' in payload['title']

    # Cleanup
    await service.close()

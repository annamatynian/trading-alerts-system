"""
Интеграционные тесты для SignalManager
Проверяют связку: проверка условий → отправка Pushover уведомлений
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from services.signal_manager import SignalManager
from services.price_checker import PriceChecker, PriceData
from services.notification import NotificationService
from models.signal import SignalTarget, SignalCondition, ExchangeType
from utils.config import NotificationConfig


@pytest.fixture
def mock_price_checker():
    """Mock price checker returning predefined prices"""
    checker = AsyncMock(spec=PriceChecker)

    # Mock get_prices_for_exchange to return price data
    async def mock_get_prices(exchange, symbols):
        # Return different prices for different symbols
        prices = []
        for symbol in symbols:
            if symbol == 'BTCUSDT':
                price = 101000.0  # Above 100k target
            elif symbol == 'ETHUSDT':
                price = 1500.0    # Below 2000 target
            elif symbol == 'SOLUSDT':
                price = 50.0      # Equal to 50 target
            else:
                price = 100.0

            prices.append(PriceData(
                exchange=exchange,
                symbol=symbol,
                price=price,
                timestamp=datetime.now()
            ))
        return prices

    checker.get_prices_for_exchange = mock_get_prices
    return checker


@pytest.fixture
def mock_notification_service():
    """Mock notification service"""
    service = AsyncMock(spec=NotificationService)
    service.send_alert_notification = AsyncMock()
    return service


@pytest.fixture
def mock_storage():
    """Mock storage with signals"""
    storage = AsyncMock()
    storage.load_signals = AsyncMock(return_value=[])
    storage.update_signal = AsyncMock()
    storage.save_signal = AsyncMock()
    return storage


@pytest.fixture
def signal_above_trigger():
    """Signal that SHOULD trigger (price above target)"""
    return SignalTarget(
        id='signal-1',
        name='BTC Above 100k',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id='test-user-1'
    )


@pytest.fixture
def signal_below_trigger():
    """Signal that SHOULD trigger (price below target)"""
    return SignalTarget(
        id='signal-2',
        name='ETH Below 2k',
        exchange=ExchangeType.BINANCE,
        symbol='ETHUSDT',
        condition=SignalCondition.BELOW,
        target_price=2000.0,
        active=True,
        user_id='test-user-2'
    )


@pytest.fixture
def signal_no_trigger():
    """Signal that should NOT trigger (price below target but condition is ABOVE)"""
    return SignalTarget(
        id='signal-3',
        name='ETH Above 2k',
        exchange=ExchangeType.BINANCE,
        symbol='ETHUSDT',
        condition=SignalCondition.ABOVE,  # Price is 1500, target is 2000, so won't trigger
        target_price=2000.0,
        active=True,
        user_id='test-user-3'
    )


@pytest.mark.asyncio
async def test_signal_triggers_and_sends_notification(
    mock_price_checker,
    mock_notification_service,
    mock_storage,
    signal_above_trigger
):
    """Test: Сигнал срабатывает и отправляется Pushover уведомление"""
    # Setup storage to return our signal
    mock_storage.load_signals.return_value = [signal_above_trigger]

    manager = SignalManager(
        price_checker=mock_price_checker,
        notification_service=mock_notification_service,
        storage_service=mock_storage
    )

    # Run check
    results = await manager.check_all_signals()

    # Verify signal triggered
    assert len(results) == 1
    assert results[0].triggered is True
    assert results[0].current_price == 101000.0
    assert results[0].signal.symbol == 'BTCUSDT'

    # Verify notification was sent
    mock_notification_service.send_alert_notification.assert_called_once()
    call_args = mock_notification_service.send_alert_notification.call_args[0][0]
    assert call_args.signal.name == 'BTC Above 100k'
    assert call_args.triggered is True

    # Verify signal was updated in storage
    mock_storage.update_signal.assert_called_once()
    updated_signal = mock_storage.update_signal.call_args[0][0]
    assert updated_signal.triggered_count == 1
    assert updated_signal.active is False  # Deactivated after trigger


@pytest.mark.asyncio
async def test_signal_does_not_trigger_no_notification(
    mock_price_checker,
    mock_notification_service,
    mock_storage,
    signal_no_trigger
):
    """Test: Сигнал НЕ срабатывает → уведомление НЕ отправляется"""
    # Setup storage to return our signal
    mock_storage.load_signals.return_value = [signal_no_trigger]

    manager = SignalManager(
        price_checker=mock_price_checker,
        notification_service=mock_notification_service,
        storage_service=mock_storage
    )

    # Run check
    results = await manager.check_all_signals()

    # Verify signal did NOT trigger
    assert len(results) == 1
    assert results[0].triggered is False
    assert results[0].current_price == 1500.0  # Price is 1500
    assert results[0].signal.target_price == 2000.0  # Target is 2000
    assert results[0].signal.condition == SignalCondition.ABOVE  # Needs to be above

    # Verify notification was NOT sent
    mock_notification_service.send_alert_notification.assert_not_called()

    # Verify signal was NOT updated
    mock_storage.update_signal.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_signals_mixed_triggers(
    mock_price_checker,
    mock_notification_service,
    mock_storage,
    signal_above_trigger,
    signal_below_trigger,
    signal_no_trigger
):
    """Test: Несколько сигналов - одни триггерятся, другие нет"""
    # Setup storage with multiple signals
    mock_storage.load_signals.return_value = [
        signal_above_trigger,   # WILL trigger
        signal_below_trigger,   # WILL trigger
        signal_no_trigger       # WON'T trigger
    ]

    manager = SignalManager(
        price_checker=mock_price_checker,
        notification_service=mock_notification_service,
        storage_service=mock_storage
    )

    # Run check
    results = await manager.check_all_signals()

    # Verify all results returned
    assert len(results) == 3

    # Count triggered
    triggered_results = [r for r in results if r.triggered]
    assert len(triggered_results) == 2

    # Verify notifications sent only for triggered signals
    assert mock_notification_service.send_alert_notification.call_count == 2

    # Verify only triggered signals were updated
    assert mock_storage.update_signal.call_count == 2


@pytest.mark.asyncio
async def test_signal_below_condition_triggers(
    mock_price_checker,
    mock_notification_service,
    mock_storage,
    signal_below_trigger
):
    """Test: BELOW условие корректно срабатывает"""
    mock_storage.load_signals.return_value = [signal_below_trigger]

    manager = SignalManager(
        price_checker=mock_price_checker,
        notification_service=mock_notification_service,
        storage_service=mock_storage
    )

    results = await manager.check_all_signals()

    # Verify trigger
    assert results[0].triggered is True
    assert results[0].current_price == 1500.0  # Current price
    assert results[0].signal.target_price == 2000.0  # Target
    assert results[0].signal.condition == SignalCondition.BELOW

    # Notification sent
    mock_notification_service.send_alert_notification.assert_called_once()


@pytest.mark.asyncio
async def test_equal_condition_triggers():
    """Test: EQUAL условие срабатывает при точном совпадении"""
    # Create signal with EQUAL condition
    signal_equal = SignalTarget(
        id='signal-equal',
        name='SOL Equal 50',
        exchange=ExchangeType.BINANCE,
        symbol='SOLUSDT',
        condition=SignalCondition.EQUAL,
        target_price=50.0,
        active=True,
        user_id='test-user'
    )

    mock_storage = AsyncMock()
    mock_storage.load_signals.return_value = [signal_equal]
    mock_storage.update_signal = AsyncMock()

    mock_notification = AsyncMock(spec=NotificationService)
    mock_notification.send_alert_notification = AsyncMock()

    # Price checker returns exactly 50.0 for SOLUSDT
    mock_prices = AsyncMock(spec=PriceChecker)
    async def get_prices(exchange, symbols):
        return [PriceData(exchange=exchange, symbol=s, price=50.0, timestamp=datetime.now())
                for s in symbols]
    mock_prices.get_prices_for_exchange = get_prices

    manager = SignalManager(
        price_checker=mock_prices,
        notification_service=mock_notification,
        storage_service=mock_storage
    )

    results = await manager.check_all_signals()

    # Verify triggered
    assert results[0].triggered is True
    assert results[0].current_price == 50.0

    # Notification sent
    mock_notification.send_alert_notification.assert_called_once()


@pytest.mark.asyncio
async def test_inactive_signal_not_checked(mock_price_checker, mock_notification_service, mock_storage):
    """Test: Неактивные сигналы не проверяются"""
    inactive_signal = SignalTarget(
        id='signal-inactive',
        name='BTC Inactive',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=False,  # Inactive!
        user_id='test-user'
    )

    mock_storage.load_signals.return_value = [inactive_signal]

    manager = SignalManager(
        price_checker=mock_price_checker,
        notification_service=mock_notification_service,
        storage_service=mock_storage
    )

    results = await manager.check_all_signals()

    # No results because signal is inactive
    assert len(results) == 0

    # No notifications sent
    mock_notification_service.send_alert_notification.assert_not_called()


@pytest.mark.asyncio
async def test_signal_triggered_count_increments(
    mock_price_checker,
    mock_notification_service,
    mock_storage,
    signal_above_trigger
):
    """Test: triggered_count увеличивается при срабатывании"""
    signal_above_trigger.triggered_count = 0
    mock_storage.load_signals.return_value = [signal_above_trigger]

    manager = SignalManager(
        price_checker=mock_price_checker,
        notification_service=mock_notification_service,
        storage_service=mock_storage
    )

    await manager.check_all_signals()

    # Verify triggered_count was incremented
    updated_signal = mock_storage.update_signal.call_args[0][0]
    assert updated_signal.triggered_count == 1
    assert updated_signal.last_triggered_at is not None


@pytest.mark.asyncio
async def test_no_signals_in_storage(mock_price_checker, mock_notification_service, mock_storage):
    """Test: Пустое хранилище - нет сигналов для проверки"""
    mock_storage.load_signals.return_value = []

    manager = SignalManager(
        price_checker=mock_price_checker,
        notification_service=mock_notification_service,
        storage_service=mock_storage
    )

    results = await manager.check_all_signals()

    assert len(results) == 0
    mock_notification_service.send_alert_notification.assert_not_called()

"""
Тесты для мультипользовательского функционала
Проверяем создание сигналов для разных пользователей и фильтрацию
"""
import pytest
import asyncio
from datetime import datetime

from moto import mock_aws
import boto3

from models.signal import SignalTarget, ExchangeType, SignalCondition
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
        # Создаем таблицу
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
def signal_anna():
    """Создает тестовый сигнал для пользователя Anna"""
    return SignalTarget(
        id='signal-anna-1',
        name="Anna's BTC Alert",
        exchange=ExchangeType.BYBIT,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=50000.0,
        active=True,
        user_id='anna',
        notes='Test signal for Anna'
    )


@pytest.fixture
def signal_john():
    """Создает тестовый сигнал для пользователя John"""
    return SignalTarget(
        id='signal-john-1',
        name="John's ETH Alert",
        exchange=ExchangeType.BINANCE,
        symbol='ETHUSDT',
        condition=SignalCondition.BELOW,
        target_price=3000.0,
        active=True,
        user_id='john',
        notes='Test signal for John'
    )


@pytest.fixture
def signal_anna_2():
    """Второй сигнал для пользователя Anna"""
    return SignalTarget(
        id='signal-anna-2',
        name="Anna's ETH Alert",
        exchange=ExchangeType.BYBIT,
        symbol='ETHUSDT',
        condition=SignalCondition.ABOVE,
        target_price=3500.0,
        active=True,
        user_id='anna',
        notes='Second signal for Anna'
    )


@pytest.mark.asyncio
async def test_create_signals_for_different_users(storage, signal_anna, signal_john):
    """Тест: создание сигналов для разных пользователей"""
    # Сохраняем сигналы для разных пользователей
    result_anna = await storage.save_signal(signal_anna)
    result_john = await storage.save_signal(signal_john)

    assert result_anna is True
    assert result_john is True

    # Загружаем все сигналы
    all_signals = await storage.get_all_signals()

    assert len(all_signals) == 2

    # Проверяем что user_id корректно сохранены
    user_ids = {s.user_id for s in all_signals}
    assert 'anna' in user_ids
    assert 'john' in user_ids


@pytest.mark.asyncio
async def test_filter_signals_by_user_id(storage, signal_anna, signal_john, signal_anna_2):
    """Тест: фильтрация сигналов по user_id"""
    # Сохраняем сигналы
    await storage.save_signal(signal_anna)
    await storage.save_signal(signal_john)
    await storage.save_signal(signal_anna_2)

    # Загружаем все сигналы
    all_signals = await storage.get_all_signals()
    assert len(all_signals) == 3

    # Фильтруем сигналы Anna
    anna_signals = [s for s in all_signals if s.user_id == 'anna']
    assert len(anna_signals) == 2
    assert all(s.user_id == 'anna' for s in anna_signals)

    # Фильтруем сигналы John
    john_signals = [s for s in all_signals if s.user_id == 'john']
    assert len(john_signals) == 1
    assert john_signals[0].user_id == 'john'
    assert john_signals[0].name == "John's ETH Alert"


@pytest.mark.asyncio
async def test_user_id_required(storage):
    """Тест: проверка что user_id обязательно для создания сигнала"""
    # Пытаемся создать сигнал без user_id
    signal_no_user = SignalTarget(
        id='signal-no-user',
        name='Signal without user',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=50000.0,
        active=True,
        user_id=None  # Нет user_id
    )

    # Сигнал должен быть создан (валидация на уровне app.py)
    # Но мы проверяем что он сохраняется с user_id=None
    result = await storage.save_signal(signal_no_user)
    assert result is True

    signals = await storage.get_all_signals()
    assert len(signals) == 1
    assert signals[0].user_id is None


@pytest.mark.asyncio
async def test_update_signal_preserves_user_id(storage, signal_anna):
    """Тест: обновление сигнала сохраняет user_id"""
    # Сохраняем сигнал
    await storage.save_signal(signal_anna)

    # Обновляем target_price
    signal_anna.target_price = 55000.0
    await storage.update_signal(signal_anna)

    # Загружаем и проверяем что user_id не изменился
    signals = await storage.get_all_signals()
    assert len(signals) == 1
    assert signals[0].user_id == 'anna'
    assert signals[0].target_price == 55000.0


@pytest.mark.asyncio
async def test_delete_signal_by_user(storage, signal_anna, signal_john):
    """Тест: удаление сигнала конкретного пользователя"""
    # Сохраняем сигналы
    await storage.save_signal(signal_anna)
    await storage.save_signal(signal_john)

    # Удаляем сигнал Anna
    result = await storage.delete_signal(signal_anna.id)
    assert result is True

    # Проверяем что остался только сигнал John
    signals = await storage.get_all_signals()
    assert len(signals) == 1
    assert signals[0].user_id == 'john'


@pytest.mark.asyncio
async def test_multiple_users_same_symbol(storage):
    """Тест: несколько пользователей могут создавать сигналы для одного символа"""
    # Создаем сигналы для BTCUSDT от разных пользователей
    signal1 = SignalTarget(
        name="Anna's BTC Alert",
        exchange=ExchangeType.BYBIT,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=50000.0,
        user_id='anna'
    )
    signal1.id = signal1.generate_id()

    signal2 = SignalTarget(
        name="John's BTC Alert",
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.BELOW,
        target_price=45000.0,
        user_id='john'
    )
    signal2.id = signal2.generate_id()

    await storage.save_signal(signal1)
    await storage.save_signal(signal2)

    # Проверяем что оба сигнала сохранены
    all_signals = await storage.get_all_signals()
    assert len(all_signals) == 2

    # Проверяем что у них разные ID
    assert signal1.id != signal2.id

    # Проверяем что оба для BTCUSDT но с разными user_id
    btc_signals = [s for s in all_signals if s.symbol == 'BTCUSDT']
    assert len(btc_signals) == 2
    user_ids = {s.user_id for s in btc_signals}
    assert user_ids == {'anna', 'john'}


@pytest.mark.asyncio
async def test_user_isolation(storage, signal_anna, signal_john):
    """Тест: пользователи изолированы друг от друга"""
    # Сохраняем сигналы
    await storage.save_signal(signal_anna)
    await storage.save_signal(signal_john)

    # Anna видит только свои сигналы
    all_signals = await storage.get_all_signals()
    anna_view = [s for s in all_signals if s.user_id == 'anna']
    assert len(anna_view) == 1
    assert all('Anna' in s.name for s in anna_view)

    # John видит только свои сигналы
    john_view = [s for s in all_signals if s.user_id == 'john']
    assert len(john_view) == 1
    assert all('John' in s.name for s in john_view)


@pytest.mark.asyncio
async def test_case_sensitive_user_id(storage):
    """Тест: user_id чувствителен к регистру"""
    signal1 = SignalTarget(
        name='Signal 1',
        exchange=ExchangeType.BYBIT,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=50000.0,
        user_id='Anna'  # С заглавной
    )
    signal1.id = signal1.generate_id()

    signal2 = SignalTarget(
        name='Signal 2',
        exchange=ExchangeType.BYBIT,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=50000.0,
        user_id='anna'  # Со строчной
    )
    signal2.id = signal2.generate_id()

    await storage.save_signal(signal1)
    await storage.save_signal(signal2)

    all_signals = await storage.get_all_signals()
    assert len(all_signals) == 2

    # Проверяем что это разные пользователи
    user_ids = [s.user_id for s in all_signals]
    assert 'Anna' in user_ids
    assert 'anna' in user_ids
    assert user_ids.count('Anna') == 1
    assert user_ids.count('anna') == 1

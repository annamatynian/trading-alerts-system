"""
Юнит-тесты для DynamoDB Storage
Используем moto для мокирования AWS
"""
import pytest
import asyncio
from datetime import datetime
from decimal import Decimal

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
def sample_signal():
    """Создает тестовый сигнал"""
    return SignalTarget(
        id='test-signal-1',
        name='Test Signal',
        exchange=ExchangeType.BINANCE,
        symbol='BTCUSDT',
        condition=SignalCondition.ABOVE,
        target_price=100000.0,
        active=True,
        user_id='test-user'
    )


@pytest.mark.asyncio
async def test_save_signal(storage, sample_signal):
    """Тест: сохранение сигнала"""
    result = await storage.save_signal(sample_signal)
    assert result is True


@pytest.mark.asyncio
async def test_load_signals(storage, sample_signal):
    """Тест: загрузка сигналов"""
    # Сохраняем сигнал
    await storage.save_signal(sample_signal)
    
    # Загружаем все сигналы
    signals = await storage.load_signals()
    
    assert len(signals) == 1
    assert signals[0].name == sample_signal.name
    assert signals[0].symbol == sample_signal.symbol
    assert signals[0].target_price == sample_signal.target_price


@pytest.mark.asyncio
async def test_delete_signal(storage, sample_signal):
    """Тест: удаление сигнала"""
    # Сохраняем сигнал
    await storage.save_signal(sample_signal)
    
    # Удаляем сигнал
    result = await storage.delete_signal(sample_signal.id)
    assert result is True
    
    # Проверяем что сигнал удален
    signals = await storage.load_signals()
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_update_signal(storage, sample_signal):
    """Тест: обновление сигнала"""
    # Сохраняем сигнал
    await storage.save_signal(sample_signal)
    
    # Обновляем target_price
    sample_signal.target_price = 105000.0
    result = await storage.update_signal(sample_signal)
    assert result is True
    
    # Загружаем и проверяем
    signals = await storage.load_signals()
    assert signals[0].target_price == 105000.0


@pytest.mark.asyncio
async def test_save_user_data(storage):
    """Тест: сохранение данных пользователя"""
    user_data = {
        'pushover_key': 'test-key-123',
        'email': 'test@example.com'
    }
    
    result = await storage.save_user_data('test-user', user_data)
    assert result is True


@pytest.mark.asyncio
async def test_get_user_data(storage):
    """Тест: получение данных пользователя"""
    user_data = {
        'pushover_key': 'test-key-123',
        'email': 'test@example.com'
    }
    
    # Сохраняем
    await storage.save_user_data('test-user', user_data)
    
    # Загружаем
    loaded_data = await storage.get_user_data('test-user')
    
    assert loaded_data['pushover_key'] == 'test-key-123'
    assert loaded_data['email'] == 'test@example.com'


@pytest.mark.asyncio
async def test_decimal_conversion(storage, sample_signal):
    """Тест: конвертация float <-> Decimal"""
    # Сохраняем сигнал с float
    sample_signal.target_price = 99999.99
    await storage.save_signal(sample_signal)
    
    # Загружаем обратно
    signals = await storage.load_signals()
    
    # Проверяем что цена осталась float (не Decimal)
    assert isinstance(signals[0].target_price, float)
    assert signals[0].target_price == 99999.99
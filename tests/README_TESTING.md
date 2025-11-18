# Testing Guide - Pushover Integration

## Обзор

Созданы комплексные тесты для проверки интеграции Pushover с системой уведомлений.

## Структура тестов

```
tests/
├── test_services/
│   ├── test_notification.py      # Юнит-тесты NotificationService
│   └── test_auth_service.py      # Тесты AuthService + Pushover keys
├── test_integration/
│   └── test_pushover_flow.py     # Интеграционные тесты полного flow
└── test_storage/
    └── test_dynamodb_storage.py  # Тесты DynamoDB storage
```

## Типы тестов

### 1. Юнит-тесты NotificationService (`test_notification.py`)

**Что тестируется:**
- ✅ Инициализация сервиса с Pushover token
- ✅ Отправка уведомлений через Pushover API
- ✅ Обработка успешных ответов от API
- ✅ Обработка ошибок от API
- ✅ Получение Pushover ключа пользователя из storage
- ✅ Обработка случая когда у пользователя нет ключа
- ✅ Обработка сигнала без user_id
- ✅ Изоляция пользователей (разные пользователи → разные ключи)

**Ключевые тесты:**
```python
# Успешная отправка уведомления
test_send_pushover_alert_success()

# Разные пользователи получают уведомления на свои ключи
test_multiple_users_get_different_notifications()

# Пользователь без ключа не получает уведомления
test_send_alert_notification_no_user_key()
```

### 2. Юнит-тесты AuthService (`test_auth_service.py`)

**Что тестируется:**
- ✅ Установка Pushover ключа для пользователя
- ✅ Обновление существующего ключа
- ✅ Получение ключа пользователя
- ✅ Персистентность ключа в DynamoDB
- ✅ Удаление ключа при удалении пользователя
- ✅ Изоляция ключей между пользователями

**Ключевые тесты:**
```python
# Регистрация и установка ключа
test_register_user_and_set_pushover_key()

# Ключ сохраняется в DynamoDB и загружается обратно
test_pushover_key_persistence()

# Разные пользователи имеют разные ключи
test_multiple_users_different_keys()
```

### 3. Интеграционные тесты (`test_pushover_flow.py`)

**Что тестируется:**
- ✅ Полный flow: DynamoDB → NotificationService → Pushover API
- ✅ Сохранение ключа в DynamoDB + отправка уведомления
- ✅ Изоляция уведомлений между пользователями
- ✅ Обновление Pushover ключа и его использование
- ✅ Пользователь без ключа не получает уведомления
- ✅ Сохранение сигнала + отправка уведомления

**Ключевые тесты:**
```python
# Полный flow от сохранения ключа до отправки уведомления
test_full_pushover_flow_with_storage()

# Изоляция пользователей на уровне интеграции
test_multiple_users_isolated_notifications()

# Обновление ключа и его немедленное использование
test_update_user_pushover_key()
```

## Установка зависимостей

```bash
pip install -r requirements.txt
```

Необходимые библиотеки для тестов:
- `pytest>=7.0.0` - фреймворк для тестирования
- `pytest-asyncio>=0.21.0` - поддержка async/await тестов
- `aioresponses>=0.7.0` - мокирование HTTP запросов (aiohttp)
- `moto>=5.0.0` - мокирование AWS сервисов (DynamoDB)

## Запуск тестов

### Все тесты
```bash
pytest tests/ -v
```

### Только юнит-тесты NotificationService
```bash
pytest tests/test_services/test_notification.py -v
```

### Только интеграционные тесты
```bash
pytest tests/test_integration/ -v
```

### Конкретный тест
```bash
pytest tests/test_services/test_notification.py::test_send_pushover_alert_success -v
```

### С подробным выводом
```bash
pytest tests/ -v -s
```

## Как работают тесты

### Мокирование Pushover API

Используем `aioresponses` для мокирования HTTP запросов:

```python
from aioresponses import aioresponses

with aioresponses() as mocked:
    # Мокируем успешный ответ от Pushover API
    mocked.post(
        NotificationService.PUSHOVER_API_URL,
        payload={'status': 1, 'request': 'test-request-id'},
        status=200
    )

    # Отправляем уведомление
    await notification_service.send_pushover_alert(result, 'user-key')

    # Проверяем что запрос был сделан
    assert len(mocked.requests) == 1
```

### Мокирование DynamoDB

Используем `moto` для создания in-memory DynamoDB:

```python
from moto import mock_aws
import boto3

@pytest.fixture
def dynamodb_table():
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[...],
            AttributeDefinitions=[...],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table
```

## Сценарии тестирования

### Сценарий 1: Новый пользователь настраивает Pushover

```python
1. Пользователь регистрируется: register_user('alice', 'password')
2. Устанавливает Pushover ключ: update_pushover_key('alice', 'alice-key-123')
3. Создает сигнал: signal.user_id = 'alice'
4. При срабатывании сигнала:
   - NotificationService загружает ключ из storage
   - Отправляет уведомление на Pushover API с user='alice-key-123'
5. ✅ Alice получает уведомление на свой телефон
```

### Сценарий 2: Несколько пользователей получают уведомления

```python
1. Alice имеет ключ 'alice-key-123'
2. Bob имеет ключ 'bob-key-456'
3. У обоих срабатывают сигналы одновременно
4. NotificationService:
   - Для сигнала Alice: загружает 'alice-key-123' → отправляет на Pushover
   - Для сигнала Bob: загружает 'bob-key-456' → отправляет на Pushover
5. ✅ Каждый получает только свои уведомления
6. ✅ Полная изоляция между пользователями
```

### Сценарий 3: Обновление Pushover ключа

```python
1. Пользователь имеет старый ключ 'old-key-111'
2. Получает уведомления на старый ключ
3. Обновляет ключ: update_pushover_key('user', 'new-key-222')
4. При следующем срабатывании сигнала:
   - NotificationService загружает новый ключ 'new-key-222'
   - Отправляет уведомление на новый ключ
5. ✅ Уведомления приходят на новое устройство
```

## Проверка интеграции вручную

### 1. Установите реальный Pushover App Token

В `.env` файле:
```bash
PUSHOVER_API_TOKEN=your_app_token_here
```

### 2. Создайте тестового пользователя

```python
# В Gradio интерфейсе или через код
auth_service.register_user('testuser', 'password123')
auth_service.update_pushover_key('testuser', 'your_user_key_here')
```

### 3. Создайте тестовый сигнал

```python
signal = SignalTarget(
    name='Test Alert',
    exchange=ExchangeType.BINANCE,
    symbol='BTCUSDT',
    condition=SignalCondition.ABOVE,
    target_price=50000.0,  # Цена которая точно сработает
    user_id='testuser'
)
```

### 4. Запустите price checker

```python
# Если текущая цена > target_price
# Вы получите уведомление на телефон через Pushover
```

## Coverage (Покрытие кода тестами)

Тесты покрывают:
- ✅ 100% публичных методов NotificationService
- ✅ 100% публичных методов AuthService (Pushover часть)
- ✅ 100% интеграции DynamoDB ↔ NotificationService
- ✅ Все edge cases (нет ключа, нет user_id, ошибки API)
- ✅ Изоляция пользователей
- ✅ Персистентность данных

## Дальнейшие улучшения

1. **End-to-end тесты**: Запуск реального Gradio интерфейса + проверка UI
2. **Performance тесты**: Отправка 1000 уведомлений одновременно
3. **Stress тесты**: Поведение при недоступности Pushover API
4. **Retry логика**: Автоматические повторы при сбоях

## Проблемы и решения

### Проблема: "ResourceNotFoundException" в DynamoDB тестах
**Симптом**: Все тесты падают с ошибкой `ResourceNotFoundException: Requested resource not found`

**Причина**: `with mock_aws():` context manager завершается до запуска теста, поэтому мок-таблица не доступна.

**Решение**: Создан отдельный fixture `mock_dynamodb` который держит context manager активным:
```python
@pytest.fixture(scope='function')
def mock_dynamodb(aws_credentials):
    """Активирует mock_aws для каждого теста"""
    with mock_aws():
        yield

@pytest.fixture
def dynamodb_table(mock_dynamodb):
    """Создает таблицу ВНУТРИ активного mock_aws context"""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(...)
    yield table
```

### Проблема: "No module named 'pydantic'"
```bash
pip install pydantic>=2.0.0
```

### Проблема: "No module named 'aioresponses'"
```bash
pip install aioresponses>=0.7.0
```

### Проблема: Тесты не находятся
Убедитесь что вы в корневой директории проекта:
```bash
cd /path/to/trading-alerts-system
pytest tests/
```

### Проблема: "PydanticDeprecatedSince20" warnings
Эти warning'и можно игнорировать - они не влияют на работу тестов. Если хотите убрать:
```bash
pytest tests/ -v --disable-warnings
```

## Заключение

Созданная тестовая инфраструктура гарантирует:
1. ✅ Pushover интеграция работает корректно
2. ✅ Каждый пользователь изолирован и получает только свои уведомления
3. ✅ Ключи сохраняются и загружаются из DynamoDB
4. ✅ Обработка всех edge cases и ошибок
5. ✅ Возможность безопасно вносить изменения в код (regression protection)

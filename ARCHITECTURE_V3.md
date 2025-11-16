# 🎯 Trading Alert System - Архитектура Вариант 3

## 📐 Общая Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRADING ALERT SYSTEM                          │
│                    Вариант 3: Максимальная Гибкость             │
└─────────────────────────────────────────────────────────────────┘

                          ┌──────────────┐
                          │  DynamoDB    │◄────┐
                          │  (Master DB) │     │
                          └──────────────┘     │
                                 ▲             │
                                 │             │
                    ┌────────────┼────────────┐│
                    │            │            ││
                    ▼            ▼            ▼│
          ┌─────────────┐  ┌─────────┐  ┌────────────┐
          │   Lambda    │  │ Gradio  │  │   Sheets   │
          │  (Cron Job) │  │   UI    │  │ (Admin UI) │
          └─────────────┘  └─────────┘  └────────────┘
                 │              │              │
                 │              │              │
                 ▼              ▼              ▼
          [Автопроверка]  [Интерактив]  [Быстрые правки]
          
          ┌──────────────────────────────────────────┐
          │   Exchanges: Binance | Bybit | Coinbase  │
          └──────────────────────────────────────────┘
```

## 🔄 Потоки данных

### Поток 1: Создание сигналов
```
Админ создает сигнал
    ↓
Выбор интерфейса:
    ├─► Google Sheets → ручное редактирование → Sync to DynamoDB
    ├─► Gradio UI → форма → прямая запись в DynamoDB (+ опционально Sheets)
    └─► API → JSON → прямая запись в DynamoDB
    
Результат: сигнал в DynamoDB (единый источник истины)
```

### Поток 2: Автоматическая проверка (Lambda Cron)
```
CloudWatch EventBridge (каждый час)
    ↓
Запуск Lambda Function
    ↓
1. Читаем сигналы из DynamoDB
2. Проверяем цены на биржах (Binance/Bybit/Coinbase)
3. Сравниваем с условиями
4. Если триггер сработал:
    - Обновляем счетчик в DynamoDB
    - Отправляем Pushover уведомление
    - Логируем в S3 CSV (история)
5. Возвращаем статус
```

### Поток 3: Интерактивное управление (Gradio)
```
Пользователь открывает http://localhost:7860
    ↓
Выбирает действие:
    ├─► Create Signal → DynamoDB (+ опционально Sheets)
    ├─► View Signals → читает из DynamoDB
    ├─► Delete Signal → удаляет из DynamoDB
    ├─► Check Price → запрос к бирже в реальном времени
    └─► Sync from Sheets → массовая загрузка Sheets → DynamoDB
```

### Поток 4: Быстрое редактирование (Google Sheets)
```
Админ редактирует Google Sheets
    ↓
Изменяет цены, условия, добавляет новые сигналы
    ↓
Синхронизация (2 способа):
    ├─► Вручную через Gradio (кнопка "Sync from Sheets")
    └─► Автоматически через Lambda (читает Sheets → upsert в DynamoDB)
```

## 🗄️ Структура DynamoDB

### Таблица: `trading-alerts`

```
Partition Key: user_id (String)
Sort Key: signal_id (String)

Attributes:
├─ signal_id          (S)  "signal#abc123def456"
├─ user_id            (S)  "default" или Pushover user key
├─ name               (S)  "BYBIT BTCUSDT above $50000"
├─ exchange           (S)  "binance" | "bybit" | "coinbase"
├─ symbol             (S)  "BTCUSDT"
├─ condition          (S)  "above" | "below"
├─ target_price       (N)  50000.00
├─ active             (BOOL) true
├─ created_at         (S)  "2025-11-14T10:30:00"
├─ updated_at         (S)  "2025-11-14T10:30:00"
├─ triggered_count    (N)  0
├─ last_triggered_at  (S)  "2025-11-14T11:00:00"
├─ max_triggers       (N)  null (опционально)
└─ notes              (S)  "Important signal" (опционально)
```

### Индексы

```
GSI: signal_id-index
  - Partition Key: signal_id
  - Для быстрого поиска по ID
```

## 📊 Google Sheets Структура

### Лист: "Trading Signals"

| symbol   | condition | target_price | exchange | active | pushover_user_key | notes           |
|----------|-----------|--------------|----------|--------|-------------------|-----------------|
| BTCUSDT  | above     | 50000        | bybit    | TRUE   | user_key_123      | Main BTC alert  |
| ETHUSDT  | below     | 3000         | binance  | TRUE   | user_key_123      | ETH dip alert   |
| SOLUSDT  | above     | 150          | coinbase | FALSE  |                   | Paused for now  |

**Примечания:**
- `active` = TRUE/FALSE (включен ли сигнал)
- `pushover_user_key` опционально (для персональных уведомлений)
- `exchange` опционально (используется первая доступная биржа если пусто)

## 🔧 Компоненты системы

### 1. Lambda Function (`lambda_function.py`)
**Назначение:** Автоматическая проверка сигналов по расписанию

**Триггер:** CloudWatch EventBridge (каждый час)

**Логика:**
```python
1. init_exchanges() → Подключение к Binance/Bybit/Coinbase
2. read_signals_from_dynamodb() → Загрузка активных сигналов
3. check_each_signal():
   - get_current_price(exchange, symbol)
   - compare_with_condition(price, target, condition)
   - if triggered:
       - send_pushover_notification()
       - update_triggered_count()
       - save_to_csv_s3()
4. return status
```

**Environment Variables:**
```bash
DYNAMODB_TABLE_NAME=trading-alerts
DYNAMODB_REGION=us-east-2
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
BINANCE_API_KEY=...
BYBIT_API_KEY=...
COINBASE_API_KEY=...
PUSHOVER_APP_TOKEN=...
```

### 2. Gradio UI (`gradio_app.py`)
**Назначение:** Веб-интерфейс для интерактивного управления

**Порт:** 7860

**Возможности:**
- ✅ Создание сигналов (форма)
- ✅ Просмотр всех сигналов (таблица)
- ✅ Удаление сигналов
- ✅ Проверка цен в реальном времени
- ✅ Синхронизация из Google Sheets

**Запуск:**
```bash
python gradio_app.py
# или
run_gradio.bat
```

### 3. Google Sheets Integration (`SheetsReader`)
**Назначение:** Быстрое редактирование сигналов администраторами

**Файл:** `src/services/sheets_reader.py`

**Методы:**
- `read_signals()` - читает все сигналы из листа
- `test_connection()` - проверка подключения
- `append_signal()` - добавление нового сигнала (TODO)

**Credentials:** `secret-medium-476300-m9-c141e07c30ad.json`

### 4. DynamoDB Storage (`DynamoDBStorage`)
**Назначение:** Основное хранилище данных

**Файл:** `src/storage/dynamodb_storage.py`

**Методы:**
- `save_signal(signal)` - сохранение/обновление (upsert)
- `get_all_signals()` - получение всех активных сигналов
- `delete_signal(signal_id)` - удаление сигнала
- `get_signal_by_id(signal_id)` - поиск по ID
- `save_user_data(user_id, data)` - сохранение данных пользователя

## 🎛️ Интерфейсы и их назначение

| Интерфейс        | Кто использует | Для чего | Преимущества |
|------------------|----------------|----------|--------------|
| **Google Sheets** | Админы | Быстрое редактирование, массовые правки | Знакомый интерфейс, Excel-like |
| **Gradio UI** | Пользователи, Админы | Создание, просмотр, удаление сигналов | Красивый UI, интерактивность |
| **Lambda** | Система (авто) | Фоновая проверка по расписанию | Автоматизация, масштабируемость |
| **API/CLI** | Разработчики | Интеграция, автоматизация | Программный доступ |

## 🔄 Сценарии использования

### Сценарий 1: Админ создает новые сигналы
```
Путь 1 (Google Sheets):
Админ → открывает Sheets → добавляет строки → сохраняет
       → Gradio "Sync from Sheets" → DynamoDB обновляется

Путь 2 (Gradio):
Админ → открывает Gradio → форма "Create Signal" → DynamoDB сохраняет
       → опционально дублирует в Sheets
```

### Сценарий 2: Автоматическая проверка
```
Каждый час:
CloudWatch → Lambda запускается → читает DynamoDB
          → проверяет цены на биржах
          → если условие выполнено:
              → отправляет Pushover уведомление
              → обновляет triggered_count
              → сохраняет в S3 CSV
```

### Сценарий 3: Пользователь хочет узнать текущую цену
```
Пользователь → Gradio → вкладка "Check Price"
            → выбирает биржу + символ
            → получает данные в реальном времени
```

### Сценарий 4: Удаление старого сигнала
```
Путь 1 (Gradio):
Пользователь → Gradio → "Delete Signal" → вводит ID → удаляется из DynamoDB

Путь 2 (Google Sheets):
Админ → удаляет строку в Sheets → Sync from Sheets → удаляется из DynamoDB
```

## 🚀 Преимущества Варианта 3

### ✅ Гибкость
- Выбор интерфейса по ситуации
- Google Sheets для админов
- Gradio для пользователей
- Lambda для автоматизации

### ✅ Единый источник истины
- DynamoDB как master database
- Все интерфейсы работают с одними данными
- Нет конфликтов и рассинхронизации

### ✅ Масштабируемость
- Lambda обрабатывает любое количество сигналов
- DynamoDB автоматически масштабируется
- Gradio можно задеплоить на Hugging Face/Render

### ✅ Отказоустойчивость
- Если Sheets недоступен → работает Gradio + Lambda
- Если Gradio недоступен → работает Sheets + Lambda
- Lambda всегда работает по расписанию

### ✅ Удобство
- Админы привычно работают в Sheets
- Пользователи получают красивый UI
- Система автоматически проверяет сигналы

## 📝 TODO / Улучшения

### Краткосрочные
- [ ] Добавить аутентификацию в Gradio
- [ ] Реализовать `append_signal()` в SheetsReader
- [ ] Добавить фильтры в Gradio (по биржам, статусу)
- [ ] History view (логи срабатывания)

### Среднесрочные
- [ ] Telegram Bot интеграция
- [ ] Webhooks для уведомлений
- [ ] Dashboard с графиками
- [ ] Mobile app (React Native)

### Долгосрочные
- [ ] Стратегии (комбинации сигналов)
- [ ] Backtesting
- [ ] Machine Learning предсказания
- [ ] Multi-user support с ролями

## 🎯 Заключение

**Вариант 3 дает максимальную гибкость:**

```
Google Sheets ← Админы могут быстро редактировать
     ↓
DynamoDB ← Единый источник истины
     ↓
Lambda ← Автоматическая проверка
Gradio ← Красивый UI для пользователей
```

Все компоненты работают вместе, дополняя друг друга! 🚀

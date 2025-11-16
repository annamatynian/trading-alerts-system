# 🚀 Fan-Out Architecture с SQS (Масштабируемая)

## Преимущества этой архитектуры

### ✅ **Бесконечная масштабируемость**
- 1 сигнал = 1 Lambda Worker
- 1000 сигналов = 1000 Lambda Workers параллельно
- AWS автоматически масштабирует

### ✅ **Высокая надежность**
- Если 1 Worker падает → остальные 999 продолжают работать
- SQS гарантирует доставку сообщений
- Retry логика встроена

### ✅ **Оптимальная стоимость**
- Платите только за то что используете
- Параллельная обработка = быстрее = дешевле

---

## Архитектура

```
CloudWatch Events (каждый час)
        ↓
Lambda READER (читает Google Sheets)
        ↓
    Amazon SQS Queue
    (1000 сообщений)
        ↓
Lambda WORKER × 1000
(обрабатывают параллельно)
        ↓
  Pushover уведомления
```

---

## Часть 1: Создание SQS очереди (5 минут)

### Шаг 1: Откройте Amazon SQS

1. В AWS Console найдите **"SQS"**
2. Нажмите **"Create queue"**

### Шаг 2: Настройте очередь

1. **Type**: Standard (не FIFO)
2. **Name**: `trading-signals-queue`
3. **Configuration**:
   - Visibility timeout: `5 minutes` (время на обработку 1 сигнала)
   - Message retention: `4 days`
   - Receive message wait time: `0 seconds`
4. Нажмите **"Create queue"**

### Шаг 3: Скопируйте URL очереди

1. Откройте созданную очередь
2. Скопируйте **Queue URL** (например: `https://sqs.us-east-1.amazonaws.com/123456789/trading-signals-queue`)
3. Сохраните его - понадобится для Lambda

---

## Часть 2: Создание Lambda READER (10 минут)

### Шаг 1: Создайте deployment package

```bash
cd C:\Users\annam\Documents\DeFi-RAG-Project\trading_alert_system

# Создайте папку для Reader
mkdir lambda_reader_package
cd lambda_reader_package

# Установите зависимости
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib boto3 -t .

# Скопируйте код
xcopy /E /I ..\src\services services
xcopy /E /I ..\src\utils utils
copy ..\lambda_reader.py .

# Создайте ZIP
# Выделите ВСЕ файлы → Правый клик → Отправить → Сжатая ZIP-папка
# Назовите: lambda_reader.zip
```

### Шаг 2: Создайте Lambda функцию

1. AWS Console → Lambda → **"Create function"**
2. **Function name**: `trading-signals-reader`
3. **Runtime**: Python 3.11
4. Нажмите **"Create function"**

### Шаг 3: Загрузите код

1. **"Upload from"** → **".zip file"**
2. Загрузите `lambda_reader.zip`
3. **Handler**: `lambda_reader.lambda_handler`

### Шаг 4: Настройте переменные окружения

**Configuration** → **Environment variables** → **Edit**:

| Key | Value |
|-----|-------|
| `SQS_QUEUE_URL` | URL вашей SQS очереди |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID вашей таблицы |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON ключ сервисного аккаунта |

### Шаг 5: Добавьте права доступа к SQS

1. **Configuration** → **Permissions**
2. Кликните на роль (откроется IAM)
3. **Add permissions** → **Attach policies**
4. Найдите `AmazonSQSFullAccess`
5. Нажмите **"Attach policy"**

### Шаг 6: Настройте таймаут

**Configuration** → **General configuration** → **Edit**:
- **Memory**: 256 MB
- **Timeout**: 1 min

### Шаг 7: Создайте триггер CloudWatch

**Add trigger** → **EventBridge (CloudWatch Events)**:
- **Rule**: Create new rule
- **Rule name**: `trading-signals-hourly`
- **Schedule expression**: `rate(1 hour)`

---

## Часть 3: Создание Lambda WORKER (10 минут)

### Шаг 1: Создайте deployment package

```bash
cd C:\Users\annam\Documents\DeFi-RAG-Project\trading_alert_system

# Создайте папку для Worker
mkdir lambda_worker_package
cd lambda_worker_package

# Установите ВСЕ зависимости
pip install -r ..\requirements_lambda.txt -t .

# Скопируйте весь код
xcopy /E /I ..\src src
copy ..\lambda_worker.py .

# Создайте ZIP
# Выделите ВСЕ файлы → Правый клик → Отправить → Сжатая ZIP-папка
# Назовите: lambda_worker.zip
```

### Шаг 2: Создайте Lambda функцию

1. AWS Console → Lambda → **"Create function"**
2. **Function name**: `trading-signals-worker`
3. **Runtime**: Python 3.11
4. Нажмите **"Create function"**

### Шаг 3: Загрузите код

1. **"Upload from"** → **".zip file"**
2. Загрузите `lambda_worker.zip`
3. **Handler**: `lambda_worker.lambda_handler`

### Шаг 4: Настройте переменные окружения

**Configuration** → **Environment variables** → **Edit**:

| Key | Value |
|-----|-------|
| `DYNAMODB_TABLE_NAME` | `trading-signals` |
| `TRADING_ALERT_PUSHOVER_API_TOKEN` | Ваш Pushover API token |
| `BINANCE_API_KEY` | (если используете) |
| `BINANCE_API_SECRET` | (если используете) |
| `COINBASE_API_KEY` | (если используете) |
| `COINBASE_API_SECRET` | (если используете) |

### Шаг 5: Добавьте права доступа

**Configuration** → **Permissions** → роль → **Add permissions**:

Добавьте политики:
1. `AmazonDynamoDBFullAccess`
2. `AWSLambdaSQSQueueExecutionRole`

### Шаг 6: Настройте ресурсы

**Configuration** → **General configuration** → **Edit**:
- **Memory**: 512 MB
- **Timeout**: 1 min

### Шаг 7: Подключите SQS триггер

**Add trigger** → **SQS**:
- **SQS queue**: `trading-signals-queue`
- **Batch size**: `1` (обрабатывать по 1 сообщению)
- **Enable trigger**: ✅

---

## Часть 4: Создание DynamoDB таблицы (5 минут)

### Шаг 1: Откройте DynamoDB

1. AWS Console → **DynamoDB**
2. **Create table**

### Шаг 2: Настройте таблицу

- **Table name**: `trading-signals`
- **Partition key**: `PK` (String)
- **Sort key**: `SK` (String)
- **Table settings**: Default settings
- Нажмите **"Create table"**

---

## Часть 5: Тестирование (5 минут)

### Тест Lambda Reader

1. Откройте Lambda Reader
2. **Test** → Create test event: `{}`
3. Нажмите **"Test"**
4. Проверьте логи - должны появиться сообщения в SQS

### Проверка SQS

1. Откройте SQS очередь
2. **Send and receive messages**
3. **Poll for messages**
4. Должны появиться сообщения от Reader

### Тест Lambda Worker

Workers запускаются автоматически когда в SQS появляются сообщения!

1. Откройте Lambda Worker
2. **Monitor** → **View CloudWatch logs**
3. Должны быть логи обработки сигналов

---

## Мониторинг

### CloudWatch Dashboards

**Reader метрики:**
- Invocations (сколько раз запускался)
- Duration (время выполнения)
- Errors (ошибки)

**Worker метрики:**
- Concurrent executions (сколько Workers работают одновременно)
- Throttles (если слишком много Workers)

### SQS метрики

- Messages available (сколько в очереди)
- Messages in flight (сколько обрабатываются)
- Age of oldest message (как долго сообщение ждет)

---

## Стоимость

**Пример: 100 сигналов в час**

### Lambda Reader:
- 720 вызовов/месяц × 0.3 сек = **$0.00**

### Lambda Workers:
- 72,000 вызовов/месяц × 0.5 сек = **$0.00**
  (в пределах бесплатного лимита 1M запросов)

### SQS:
- 72,000 сообщений/месяц = **$0.00**
  (первый 1M сообщений бесплатно)

### DynamoDB:
- On-Demand режим
- ~72,000 записей/месяц = **$0.09**

**Итого: ~$0.09/месяц** 🎉

---

## Сравнение архитектур

| Фича | Монолит | Fan-Out |
|------|---------|---------|
| Масштабируемость | 1 Lambda | 1000+ Lambda параллельно |
| Надежность | Если падает → все падает | Изоляция ошибок |
| Скорость | Последовательно | Параллельно |
| Таймаут риск | Высокий | Низкий |
| Стоимость | $0.00 | $0.09/мес |

---

## Troubleshooting

### Reader не отправляет в SQS
- Проверьте `SQS_QUEUE_URL`
- Проверьте права IAM (AmazonSQSFullAccess)

### Worker не запускается
- Проверьте SQS trigger настроен
- Проверьте права IAM (AWSLambdaSQSQueueExecutionRole)

### Слишком много Workers
- Уменьшите `Batch size` в SQS trigger
- Настройте `Reserved concurrent executions`

---

## Готово! 🎉

Теперь у вас:
- ✅ Масштабируемая архитектура
- ✅ Параллельная обработка 1000+ сигналов
- ✅ Высокая надежность
- ✅ Оптимальная стоимость ($0.09/мес)

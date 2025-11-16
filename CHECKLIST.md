# ✅ CHECKLIST - Проверка работоспособности системы

## 🎯 Используйте этот чеклист чтобы убедиться что всё работает!

---

## 📋 ЧАСТЬ 1: Базовая установка (5 минут)

### 1.1 Проверка .env файла

```bash
□ Файл .env существует в корне проекта
□ AWS_ACCESS_KEY_ID установлен
□ AWS_SECRET_ACCESS_KEY установлен
□ DYNAMODB_TABLE_NAME=trading-alerts
□ DYNAMODB_REGION=us-east-2
□ Хотя бы один Exchange API key настроен (Binance/Bybit/Coinbase)
□ PUSHOVER_APP_TOKEN установлен (для уведомлений)
□ PUSHOVER_USER_KEY установлен
```

**Команда для проверки:**
```bash
# Windows
type .env | findstr "AWS_ACCESS_KEY_ID DYNAMODB_TABLE_NAME BYBIT_API_KEY PUSHOVER_APP_TOKEN"

# Linux/Mac
cat .env | grep -E "AWS_ACCESS_KEY_ID|DYNAMODB_TABLE_NAME|BYBIT_API_KEY|PUSHOVER_APP_TOKEN"
```

### 1.2 Проверка AWS Credentials

```bash
□ AWS CLI установлен
□ AWS credentials настроены
□ Доступ к DynamoDB работает
```

**Команда для проверки:**
```bash
aws configure list
aws dynamodb list-tables --region us-east-2
```

**Ожидаемый результат:**
```
TableNames: [
    "trading-alerts",
    ...
]
```

### 1.3 Проверка зависимостей Python

```bash
□ Python 3.11+ установлен
□ Virtual environment создан (venv/)
□ requirements.txt установлен
□ gradio установлен
□ boto3 установлен
```

**Команда для проверки:**
```bash
python --version
pip list | findstr gradio
pip list | findstr boto3
pip list | findstr pydantic
```

---

## 📋 ЧАСТЬ 2: Gradio UI (3 минуты)

### 2.1 Запуск Gradio

```bash
□ run_gradio.bat запускается без ошибок
□ Консоль показывает "✅ DynamoDB initialized"
□ Консоль показывает "✅ Bybit initialized" (или другая биржа)
□ Gradio стартует на http://localhost:7860
```

**Команда:**
```bash
run_gradio.bat
```

**Ожидаемый вывод:**
```
✅ DynamoDB initialized: trading-alerts in us-east-2
✅ Bybit initialized
Running on local URL:  http://127.0.0.1:7860
```

### 2.2 Проверка UI в браузере

Откройте: `http://localhost:7860`

```bash
□ Gradio UI загружается
□ Видны 5 вкладок: Create Signal, View Signals, Delete Signal, Check Price, Sync from Sheets
□ Tab "Create Signal" работает (форма видна)
□ Tab "View Signals" работает (таблица видна)
```

### 2.3 Тест: Create Signal

На вкладке **"Create Signal"**:

```bash
□ Signal Name: "Test BTC Alert"
□ Exchange: "bybit"
□ Symbol: "BTCUSDT"
□ Condition: "above"
□ Target Price: 50000
□ User ID: (оставьте пустым или ваш Pushover key)
□ Notes: "Test signal"
□ Галочка "Also save to Google Sheets": СНЯТА
□ Нажмите "Create Signal"
```

**Ожидаемый результат:**
```
✅ Signal created: Test BTC Alert (ID: xxxxxxxx...)
```

**Таблица обновилась с новым сигналом** ✅

### 2.4 Тест: View Signals

На вкладке **"View Signals"**:

```bash
□ Нажмите "🔄 Refresh"
□ Таблица показывает ваш созданный сигнал
□ Видны столбцы: ID, Name, Exchange, Symbol, Condition, Target Price, Status
□ Status = "Active"
```

### 2.5 Тест: Check Price

На вкладке **"Check Price"**:

```bash
□ Exchange: "bybit"
□ Symbol: "BTCUSDT"
□ Нажмите "Check Price"
```

**Ожидаемый результат:**
```
✅ Current Price Data:
📊 Symbol: BTCUSDT
💱 Exchange: bybit
💰 Price: $XXXXX.XX
📈 24h Volume: $X,XXX,XXX,XXX
⏰ Time: 2025-11-14 XX:XX:XX
```

### 2.6 Тест: Delete Signal (опционально)

На вкладке **"Delete Signal"**:

```bash
□ Скопируйте ID из View Signals (например: "a1b2c3d4...")
□ Вставьте в поле Signal ID
□ Нажмите "Delete Signal"
```

**Ожидаемый результат:**
```
✅ Signal deleted: Test BTC Alert
```

**Таблица обновилась - сигнал удален** ✅

---

## 📋 ЧАСТЬ 3: AWS Lambda (5 минут)

### 3.1 Проверка Lambda функции

В AWS Console:

```bash
□ Lambda функция "trading-alerts-checker" существует
□ Region: us-east-2 (или другой не-US регион)
□ Runtime: Python 3.11
□ Handler: lambda_function.handler
□ Memory: 512 MB
□ Timeout: 60 seconds
```

**Или через CLI:**
```bash
aws lambda get-function --function-name trading-alerts-checker --region us-east-2
```

### 3.2 Проверка EventBridge Rule

```bash
□ EventBridge Rule существует
□ Schedule expression: rate(1 hour)
□ Target: trading-alerts-checker Lambda
□ Rule enabled
```

**Команда:**
```bash
aws events list-rules --region us-east-2 | findstr trading
```

### 3.3 Проверка IAM Permissions

```bash
□ Lambda Execution Role существует
□ Политика для DynamoDB (Read/Write)
□ Политика для Secrets Manager (Read)
□ Политика для CloudWatch Logs (Write)
```

### 3.4 Проверка Secrets Manager

```bash
□ Secret "trading-alerts/binance" существует (если используете)
□ Secret "trading-alerts/bybit" существует
□ Secret "trading-alerts/pushover" существует
```

**Команда:**
```bash
aws secretsmanager list-secrets --region us-east-2 | findstr trading-alerts
```

### 3.5 Тест Lambda функции

В AWS Console → Lambda → trading-alerts-checker:

```bash
□ Нажмите "Test"
□ Создайте тестовое событие (пустой JSON: {})
□ Выполните тест
□ Проверьте CloudWatch Logs
```

**Ожидаемые логи:**
```
INFO: Checking 1 active signals...
INFO: Checking signal: Test BTC Alert
INFO: Current price for BTCUSDT: $XXXXX
INFO: Signal not triggered (current: $XXXXX, target: $50000, condition: above)
```

### 3.6 Проверка CloudWatch Logs

```bash
□ Log group "/aws/lambda/trading-alerts-checker" существует
□ Логи пишутся
□ Нет ERROR логов
```

**Команда:**
```bash
aws logs tail /aws/lambda/trading-alerts-checker --region us-east-2 --follow
```

---

## 📋 ЧАСТЬ 4: DynamoDB (2 минуты)

### 4.1 Проверка таблицы

```bash
□ Таблица "trading-alerts" существует
□ Region: us-east-2
□ Partition key: "id" (String)
□ Billing mode: On-Demand или Provisioned
```

**Команда:**
```bash
aws dynamodb describe-table --table-name trading-alerts --region us-east-2
```

### 4.2 Проверка данных

```bash
□ В таблице есть созданные сигналы (если создали через Gradio)
□ Attributes: id, name, exchange, symbol, condition, target_price, active, etc.
```

**Команда:**
```bash
aws dynamodb scan --table-name trading-alerts --region us-east-2 --max-items 5
```

---

## 📋 ЧАСТЬ 5: Интеграция Exchange APIs (3 минуты)

### 5.1 Тест Bybit API

```python
# Запустите в Python консоли
from src.exchanges.bybit import BybitExchange
import asyncio

async def test():
    exchange = BybitExchange(api_key="your_key", api_secret="your_secret")
    await exchange.connect()
    price = await exchange.get_price("BTCUSDT")
    print(f"BTC Price: ${price.price}")

asyncio.run(test())
```

```bash
□ Bybit API подключается
□ Получает текущую цену BTC
□ Нет ошибок аутентификации
```

### 5.2 Тест Binance API (если используете)

```python
from src.exchanges.binance import BinanceExchange
import asyncio

async def test():
    exchange = BinanceExchange(api_key="your_key", api_secret="your_secret")
    await exchange.connect()
    price = await exchange.get_price("BTCUSDT")
    print(f"BTC Price: ${price.price}")

asyncio.run(test())
```

```bash
□ Binance API подключается
□ Получает текущую цену
```

### 5.3 Тест Coinbase API (если используете)

```python
from src.exchanges.coinbase import CoinbaseExchange
import asyncio

async def test():
    exchange = CoinbaseExchange(api_key="your_key", api_secret="your_secret")
    await exchange.connect()
    price = await exchange.get_price("BTCUSDT")  # преобразуется в BTC-USD
    print(f"BTC Price: ${price.price}")

asyncio.run(test())
```

```bash
□ Coinbase API подключается
□ Symbol conversion работает (BTCUSDT → BTC-USD)
```

---

## 📋 ЧАСТЬ 6: Pushover Notifications (2 минуты)

### 6.1 Тест Pushover

```python
# Запустите в Python консоли
from src.services.notifier import PushoverNotifier
import asyncio

async def test():
    notifier = PushoverNotifier(
        app_token="your_app_token",
        user_key="your_user_key"
    )
    
    success = await notifier.send_notification(
        title="Test Alert",
        message="This is a test from Trading Alert System",
        priority=0
    )
    
    print(f"Notification sent: {success}")

asyncio.run(test())
```

```bash
□ Pushover notification отправляется
□ Получаете уведомление на телефон 📱
```

---

## 📋 ЧАСТЬ 7: Google Sheets (опционально)

### 7.1 Настройка credentials

```bash
□ Google Cloud Project создан
□ Google Sheets API включен
□ Service Account создан
□ JSON credentials скачан
□ Файл credentials в проекте: secret-medium-476300-m9-c141e07c30ad.json
□ Service Account имеет доступ к вашей Google Sheets таблице
```

### 7.2 Тест чтения из Sheets

```python
from src.services.sheets_reader import SheetsReader

reader = SheetsReader()
if reader.test_connection():
    signals = reader.read_signals()
    print(f"Loaded {len(signals)} signals from Google Sheets")
```

```bash
□ Подключение к Google Sheets работает
□ Читает данные из таблицы
```

### 7.3 Тест синхронизации в Gradio

На вкладке **"Sync from Sheets"**:

```bash
□ Добавьте строку в Google Sheets вручную
□ В Gradio нажмите "Sync from Google Sheets"
□ Сигнал появился в DynamoDB
□ Видно в "View Signals"
```

---

## 📋 ЧАСТЬ 8: End-to-End Тест (10 минут)

### 8.1 Полный workflow

```bash
□ Создайте сигнал через Gradio UI:
  - Symbol: BTCUSDT
  - Condition: above
  - Target: [текущая цена BTC - 100]  (чтобы сразу сработал)
  - Exchange: bybit
  - User ID: ваш Pushover user key

□ Сигнал сохранен в DynamoDB ✅

□ Запустите Lambda тест вручную:
  - AWS Console → Lambda → Test
  - Или подождите следующий час (EventBridge)

□ Lambda обработал сигнал ✅

□ Проверьте CloudWatch Logs - должно быть:
  "INFO: Signal triggered: ..."

□ Получили Pushover уведомление на телефон 📱

□ Проверьте DynamoDB - triggered_count увеличился

□ Проверьте Gradio "View Signals" - Triggered Count = 1
```

**Если всё сработало → СИСТЕМА РАБОТАЕТ ПОЛНОСТЬЮ!** 🎉

---

## 📋 ЧАСТЬ 9: Deployment на облако (опционально)

### 9.1 Hugging Face Spaces

```bash
□ Space создан на huggingface.co
□ Код залит в HF Space
□ Secrets настроены в HF UI
□ Application запускается
□ Публичный URL работает
□ UI доступен через интернет
```

### 9.2 Render.com (альтернатива)

```bash
□ Web Service создан на Render
□ GitHub repo подключен
□ Environment variables настроены
□ Деплой успешен
□ URL работает
```

---

## 🎉 ФИНАЛЬНАЯ ПРОВЕРКА

### Все компоненты работают:

```bash
✅ Gradio UI запускается локально
✅ DynamoDB подключен
✅ Lambda функция работает
✅ EventBridge запускает Lambda по расписанию
✅ Exchange APIs возвращают цены
✅ Pushover отправляет уведомления
✅ Google Sheets синхронизация (опционально)
✅ End-to-End workflow работает
```

---

## 🐛 Troubleshooting

Если что-то не работает:

1. **DynamoDB connection failed**
   → Проверьте AWS credentials в .env
   → `aws configure list`

2. **Exchange API errors**
   → Проверьте API keys в .env
   → Проверьте что region не US (для Lambda)

3. **Lambda timeout**
   → Увеличьте timeout до 60 секунд
   → Проверьте CloudWatch Logs

4. **Pushover не отправляет**
   → Проверьте PUSHOVER_APP_TOKEN и PUSHOVER_USER_KEY
   → Тест через Python консоль

5. **Gradio не запускается**
   → `pip install gradio --upgrade`
   → Проверьте порт 7860 свободен

**Подробнее:** [FINAL_COMPLETE_GUIDE.md](FINAL_COMPLETE_GUIDE.md) (раздел Troubleshooting)

---

## 📊 Статус системы

После прохождения всех чеков:

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| Gradio UI | ☐ ✅ ❌ | localhost:7860 |
| DynamoDB | ☐ ✅ ❌ | us-east-2 |
| Lambda | ☐ ✅ ❌ | Auto-check hourly |
| EventBridge | ☐ ✅ ❌ | Cron schedule |
| Bybit API | ☐ ✅ ❌ | Price data |
| Binance API | ☐ ✅ ❌ | Optional |
| Coinbase API | ☐ ✅ ❌ | Optional |
| Pushover | ☐ ✅ ❌ | Notifications |
| Google Sheets | ☐ ✅ ❌ | Optional |
| E2E Workflow | ☐ ✅ ❌ | Full test |

---

## 🎯 Next Steps

После успешной проверки:

1. **Создайте реальные сигналы** для мониторинга
2. **Настройте уведомления** с вашим Pushover user key
3. **Деплойте Gradio** на облако (HF Spaces)
4. **Мониторьте CloudWatch Logs** для Lambda
5. **Добавьте больше бирж** если нужно

---

## 📚 Документация

- **[README.md](README.md)** - главная страница
- **[QUICKSTART_5MIN.md](QUICKSTART_5MIN.md)** - быстрый старт
- **[FINAL_COMPLETE_GUIDE.md](FINAL_COMPLETE_GUIDE.md)** - полный гайд
- **[INDEX.md](INDEX.md)** - навигация

---

**Удачи!** 🚀

*Последнее обновление: 14 ноября 2025*

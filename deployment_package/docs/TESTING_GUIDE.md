# 🧪 Testing Guide - Price Alert → Pushover Notifications

Подробная инструкция по тестированию системы уведомлений.

---

## 📋 Предварительная подготовка

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```

### 2. Настройте .env файл

Скопируйте `.env.example` → `.env` и заполните:

```bash
# Pushover (обязательно для тестов)
PUSHOVER_APP_TOKEN=your_app_token_here
PUSHOVER_USER_KEY=your_user_key_here

# AWS DynamoDB (опционально для некоторых тестов)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
DYNAMODB_TABLE_NAME=trading-alerts
DYNAMODB_REGION=eu-west-1

# JWT Secret
JWT_SECRET_KEY=your-secret-key-here
```

### 3. Установите Pushover на телефон

- **iOS**: [App Store](https://apps.apple.com/app/pushover-notifications/id506088175)
- **Android**: [Google Play](https://play.google.com/store/apps/details?id=net.superblock.pushover)

Login с вашим Pushover аккаунтом.

---

## 🎯 Тест 1: Простая отправка Pushover (самый простой)

**Что тестируется**: Только отправка уведомления через Pushover API

**Время**: ~30 секунд

**Команда**:
```bash
python test_pushover_simple.py
```

**Что должно произойти**:
1. Скрипт прочитает credentials из `.env`
2. Отправит тестовое уведомление на Pushover
3. Вы получите **EMERGENCY** notification на телефон
4. Notification требует подтверждения (acknowledgment)

**Ожидаемый вывод**:
```
============================================================
🧪 Testing Pushover Notification
============================================================
App Token: azGDORePK8...
User Key: uQiRzpo4DX...

📤 Sending test notification...

Response Status: 200
Response Data: {'status': 1, 'request': '...'}

============================================================
✅ SUCCESS! Pushover notification sent!
============================================================
📱 Check your Pushover app on your phone/device
   You should receive an EMERGENCY notification
   (requires acknowledgment)
```

**Что проверить**:
- ✅ Уведомление пришло на телефон
- ✅ Приоритет: Emergency (Priority 2)
- ✅ Требует подтверждения (кнопка "Acknowledge")
- ✅ Текст содержит: "Test Alert from Trading System"

**Если ошибка**:
- ❌ "PUSHOVER_APP_TOKEN not found" → Проверьте `.env`
- ❌ "PUSHOVER_USER_KEY not found" → Проверьте `.env`
- ❌ "Pushover API error" → Проверьте корректность токенов

---

## 🎯 Тест 2: Полный Flow с Mock ценой (средний)

**Что тестируется**: Весь flow от создания сигнала до отправки уведомления (с mock ценой)

**Время**: ~1 минута

**Команда**:
```bash
python test_full_flow.py
```

**Что происходит**:
1. Создаётся тестовый сигнал: `BTCUSDT > 95000`
2. Инициализируется storage (JSON)
3. Инициализируется Notification Service
4. Симулируется достижение цены (mock: $95,234.50)
5. Отправляется Pushover уведомление

**Ожидаемый вывод**:
```
================================================================================
🧪 FULL FLOW TEST: Price Alert → Pushover Notification
================================================================================

✅ Pushover credentials found

📊 Creating test signal...
   Signal: TEST BTCUSDT > 95000
   Exchange: binance
   Symbol: BTCUSDT
   Condition: above
   Target Price: $95,000.00

💾 Initializing storage...
   ✅ Storage initialized

📨 Initializing Notification Service...
   ✅ Notification Service initialized

🎯 MOCK: Simulating price trigger...
   Current Price: $95,234.50 (MOCKED)
   Target Price: $95,000.00
   Condition: above

✅ Signal triggered! Current price $95,234.50 is ABOVE target $95,000.00

📤 Sending Pushover notification...
✅ Pushover alert sent successfully for 'TEST BTCUSDT > 95000'

================================================================================
✅ TEST COMPLETED SUCCESSFULLY!
================================================================================
📱 Check your Pushover app - you should receive an EMERGENCY notification
   (Priority 2 - requires acknowledgment)
```

**Что проверить**:
- ✅ Уведомление пришло
- ✅ Содержит: Symbol, Exchange, Current Price, Target Price
- ✅ Title: "🚨 Alert: TEST BTCUSDT > 95000"

**Если ошибка**:
- ❌ "Missing Pushover credentials" → Проверьте `.env`
- ❌ Import errors → Проверьте `pip install -r requirements.txt`

---

## 🎯 Тест 3: Реальная цена BTC (продвинутый)

**Что тестируется**: Полный реальный flow с настоящей ценой Binance

**Время**: 1-10 минут (зависит от колебания цены)

**Команда**:
```bash
python test_real_price_alert.py
```

**Что происходит**:
1. Подключается к Binance
2. Получает **текущую цену BTC**
3. Создаёт сигнал чуть выше/ниже текущей цены (+$50 или -$50)
4. Запускает мониторинг каждые 10 секунд
5. Когда цена достигает target → отправляет Pushover

**Ожидаемый вывод**:
```
================================================================================
🧪 REAL PRICE ALERT TEST
================================================================================

✅ Pushover credentials found

🔌 Connecting to Binance...
   ✅ Connected

📊 Getting current BTC price...
   Current BTC Price: $94,567.23

📝 Creating test signal...
   Symbol: BTCUSDT
   Current Price: $94,567.23
   Target Price: $94,617.23
   Condition: above
   Difference: $50.00

💾 Initializing storage...
   ✅ Signal saved

📨 Initializing Notification Service...
   ✅ Notification Service ready

================================================================================
🔄 Starting price monitoring...
================================================================================
⏱️  Will check every 10 seconds
🎯 Waiting for price to reach $94,617.23
📱 Notification will be sent when triggered

Press Ctrl+C to stop

--- Check #1 ---
🔍 Checking prices for 1 signals...
📊 Binance BTCUSDT: current=$94,580.12, target=$94,617.23 (above)
ℹ️  Signal 'TEST BTCUSDT above 94617.23' not triggered yet

--- Check #2 ---
🔍 Checking prices for 1 signals...
📊 Binance BTCUSDT: current=$94,625.45, target=$94,617.23 (above)
🚨 SIGNAL TRIGGERED! 'TEST BTCUSDT above 94617.23'
✅ Pushover alert sent successfully

================================================================================
🎉 SIGNAL TRIGGERED!
================================================================================
✅ Notification sent!
📱 Check your Pushover app
```

**Как использовать**:

### Вариант A: Цена выше (по умолчанию)
```python
target_price = current_price + 50  # +$50 выше
condition = SignalCondition.ABOVE
```

Ждём когда цена **поднимется** на $50.

### Вариант B: Цена ниже
Откройте `test_real_price_alert.py` и раскомментируйте:

```python
# target_price = current_price - 50  # -$50 ниже
# condition = SignalCondition.BELOW
```

Ждём когда цена **упадёт** на $50.

**Остановка теста**:
```
Ctrl+C  (или Cmd+C на Mac)
```

**Что проверить**:
- ✅ Проверка цены работает
- ✅ Логи показывают текущую vs target цену
- ✅ При достижении target → уведомление отправлено
- ✅ Signal triggered_count увеличился

---

## 🎯 Тест 4: Запуск полного price checker (production-like)

**Что тестируется**: Как работает в production (с Google Sheets)

**Время**: Бесконечный (работает пока не остановите)

**Команда**:
```bash
python src/main.py
```

**Что происходит**:
1. Запускается HTTP сервер на порту 8080
2. Каждый час проверяет сигналы из Google Sheets
3. Отправляет Pushover при триггере

**Требования**:
- Google Sheets настроен (см. `.env`)
- Сигналы добавлены в таблицу

**Формат Google Sheets**:

| name | exchange | symbol | condition | target_price | active | pushover_user_key |
|------|----------|--------|-----------|--------------|--------|-------------------|
| BTC Alert | binance | BTCUSDT | above | 96000 | TRUE | uQiRzpo4DX... |

**Остановка**:
```
Ctrl+C
```

---

## 🎯 Тест 5: Gradio UI + DynamoDB

**Что тестируется**: Полный UI с аутентификацией и DynamoDB

**Время**: Интерактивно

**Команда**:
```bash
python app_with_auth.py
```

**Что происходит**:
1. Запускается Gradio UI на `http://127.0.0.1:7860`
2. Открывается в браузере
3. Можно регистрироваться, логиниться, добавлять сигналы

**Шаги тестирования**:

### 1. Регистрация
- Username: `testuser`
- Password: `test123`
- Click "Register"

### 2. Добавить Pushover Key
- Go to **Settings** tab
- Pushover User Key: `your_user_key_here`
- Click "Save Settings"

### 3. Добавить сигнал
- Go to **Add Signal** tab
- Name: `Test BTC Alert`
- Exchange: `binance`
- Symbol: `BTC/USDT`
- Condition: `above`
- Target Price: `96000`
- Click "Add Signal"

### 4. Проверить список сигналов
- Go to **View Signals** tab
- Должен появиться ваш сигнал

### 5. Ждать триггера
- Когда BTC достигнет $96,000 → Pushover уведомление

**Остановка**:
```
Ctrl+C
```

---

## 📊 Checklist перед деплоем на HF

После успешного тестирования локально:

- [ ] ✅ Тест 1 прошёл (Pushover работает)
- [ ] ✅ Тест 2 прошёл (Full flow работает)
- [ ] ✅ Тест 3 прошёл (Реальная цена триггерится)
- [ ] ✅ Тест 5 прошёл (UI работает, DynamoDB подключается)
- [ ] ✅ Все credentials корректны
- [ ] ✅ DynamoDB таблица создана
- [ ] ✅ Google Sheets настроен (если используете)

**Готовы к деплою?** → [README_HF.md](./README_HF.md)

---

## 🐛 Troubleshooting

### Pushover не приходит

1. Проверьте tokens в `.env`
2. Убедитесь что app активен на pushover.net
3. Проверьте что телефон online
4. Проверьте звук/уведомления в настройках Pushover

### "Failed to connect to Binance"

1. Проверьте интернет соединение
2. API ключи не нужны для публичных данных
3. Попробуйте другую биржу (Coinbase)

### "DynamoDB access denied"

1. Проверьте AWS credentials
2. Убедитесь что IAM user имеет права на DynamoDB
3. Проверьте region

### Import errors

```bash
pip install -r requirements.txt
```

---

**Happy Testing!** 🚀

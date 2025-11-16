# 🚀 Quick Start Guide - Gradio UI

## ⚡ Быстрый запуск (5 минут)

### Шаг 1: Проверьте .env файл
```bash
# Убедитесь что у вас есть .env с необходимыми переменными
cat .env

# Обязательные переменные:
DYNAMODB_TABLE_NAME=trading-alerts
DYNAMODB_REGION=us-east-2
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Хотя бы одна биржа:
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret

# Опционально (для Google Sheets):
GOOGLE_SHEETS_CREDENTIALS_PATH=./secret-medium-476300-m9-c141e07c30ad.json
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
```

### Шаг 2: Установите зависимости
```bash
# Если еще не установлены
pip install gradio pandas

# Или полная установка
pip install -r requirements.txt
```

### Шаг 3: Запустите Gradio
```bash
# Windows
run_gradio.bat

# Linux/Mac
python gradio_app.py
```

### Шаг 4: Откройте браузер
```
http://localhost:7860
```

## 🎨 Первое использование

### 1️⃣ Создайте тестовый сигнал

Перейдите в **Create Signal** вкладку:

```
Signal Name:      Test BTC Alert
Exchange:         bybit
Symbol:           BTCUSDT
Condition:        above
Target Price:     50000
User ID:          (оставьте пустым для теста)
Notes:            My first signal test
☑ Also save to Google Sheets
```

Нажмите **Create Signal**

**Результат:** ✅ Signal created: BYBIT BTCUSDT above $50000.0 (ID: a1b2c3d4...)

---

### 2️⃣ Просмотрите созданные сигналы

Перейдите в **View Signals** вкладку:

Нажмите **🔄 Refresh**

Увидите таблицу:
```
ID          Name                Exchange  Symbol    Condition  Target Price  Status   Created
a1b2c3d4... Test BTC Alert      bybit     BTCUSDT   above      $50000.00     Active   2025-11-14 10:30
```

---

### 3️⃣ Проверьте текущую цену

Перейдите в **Check Price** вкладку:

```
Exchange:  bybit
Symbol:    BTCUSDT
```

Нажмите **Check Price**

**Результат:**
```
✅ Current Price Data:
📊 Symbol: BTCUSDT
💱 Exchange: bybit
💰 Price: $43567.89000000
📈 24h Volume: $1,234,567,890.12
⏰ Time: 2025-11-14 11:45:30
```

---

### 4️⃣ Удалите тестовый сигнал (опционально)

Перейдите в **Delete Signal** вкладку:

```
Signal ID:  a1b2c3d4...   (скопируйте из View Signals)
```

Нажмите **Delete Signal**

**Результат:** ✅ Signal deleted: Test BTC Alert

---

### 5️⃣ Синхронизируйте из Google Sheets (если настроено)

Перейдите в **Sync from Sheets** вкладку:

Нажмите **Sync from Google Sheets**

**Результат:** ✅ Synced 5 signals from Google Sheets to DynamoDB

---

## 🎯 Основные сценарии

### Сценарий A: Мониторинг BTC > $50k
```
1. Create Signal:
   - Symbol: BTCUSDT
   - Condition: above
   - Target: 50000
   - Exchange: bybit

2. Lambda автоматически проверит каждый час
3. Когда BTC > $50k → Pushover уведомление
```

### Сценарий B: Алерт на падение ETH < $3k
```
1. Create Signal:
   - Symbol: ETHUSDT
   - Condition: below
   - Target: 3000
   - Exchange: binance

2. Lambda проверяет по расписанию
3. Если ETH < $3k → уведомление
```

### Сценарий C: Массовое добавление через Sheets
```
1. Откройте Google Sheets
2. Добавьте строки:
   BTCUSDT | above | 50000 | bybit  | TRUE
   ETHUSDT | below | 3000  | binance| TRUE
   SOLUSDT | above | 150   | bybit  | TRUE

3. Gradio → Sync from Sheets
4. Все сигналы загрузятся в DynamoDB
```

---

## 🔧 Troubleshooting

### ❌ "DynamoDB connection failed"
```bash
# Проверьте AWS credentials
aws configure list

# Проверьте переменные окружения
echo %DYNAMODB_TABLE_NAME%
echo %DYNAMODB_REGION%
echo %AWS_ACCESS_KEY_ID%
```

**Решение:**
```bash
# Добавьте в .env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
DYNAMODB_REGION=us-east-2
```

---

### ❌ "No exchanges initialized"
```bash
# Проверьте API ключи
echo %BYBIT_API_KEY%
```

**Решение:**
```bash
# Добавьте в .env хотя бы одну биржу
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret
```

---

### ❌ "Google Sheets not initialized"
```bash
# Проверьте credentials file
ls secret-medium-476300-m9-c141e07c30ad.json
```

**Решение:**
```bash
# Добавьте в .env
GOOGLE_SHEETS_CREDENTIALS_PATH=./secret-medium-476300-m9-c141e07c30ad.json
GOOGLE_SPREADSHEET_ID=your_id
```

---

### ❌ Gradio не запускается на порту 7860
```bash
# Проверьте занят ли порт
netstat -ano | findstr :7860
```

**Решение:**
```python
# Измените порт в gradio_app.py
app.launch(server_port=8080)  # Используйте другой порт
```

---

## 📚 Следующие шаги

### После тестирования:

1. **Настройте Pushover уведомления:**
   ```bash
   # Добавьте в .env
   PUSHOVER_APP_TOKEN=your_token
   PUSHOVER_USER_KEY=your_user_key
   ```

2. **Деплой на продакшен:**
   - Локально: просто запустите `run_gradio.bat`
   - Облако: читайте [GRADIO_DEPLOY.md](GRADIO_DEPLOY.md)

3. **Интеграция с Lambda:**
   - Lambda уже настроен на чтение из DynamoDB
   - Все сигналы из Gradio автоматически проверяются Lambda

4. **Добавьте аутентификацию:**
   ```python
   # В gradio_app.py
   app.launch(auth=("admin", "password123"))
   ```

---

## 🎉 Готово!

Теперь у вас работает полноценная система мониторинга цен с:
- ✅ Красивым Gradio UI
- ✅ Автоматической проверкой через Lambda
- ✅ Хранением в DynamoDB
- ✅ Опциональной синхронизацией с Google Sheets

**Наслаждайтесь!** 🚀

---

## 📞 Поддержка

- **Документация:** [GRADIO_GUIDE.md](GRADIO_GUIDE.md)
- **Деплой:** [GRADIO_DEPLOY.md](GRADIO_DEPLOY.md)
- **Архитектура:** [ARCHITECTURE_V3.md](ARCHITECTURE_V3.md)
- **Lambda:** [DEPLOY_AWS_LAMBDA.md](DEPLOY_AWS_LAMBDA.md)

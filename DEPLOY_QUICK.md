# 🚀 Быстрый деплой МОНОЛИТА на AWS Lambda

## ⏱️ Время: 25 минут
## 💰 Стоимость: ~$0.02/месяц

---

## ⚠️ **ВАЖНО: DynamoDB ОБЯЗАТЕЛЕН!**

Lambda читает сигналы из Google Sheets, но **ДОЛЖНА** сохранять состояние в DynamoDB, иначе вы будете получать СПАМ уведомлений каждый час!

**Почему DynamoDB нужен:**
- ✅ Хранит состояние: `active`, `triggered_count`
- ✅ Предотвращает спам после срабатывания
- ✅ Стоимость: ~$0.02/мес (10 сигналов)

---

## Часть 1: Создание DynamoDB таблицы (5 минут)

### 1. Откройте DynamoDB:
- AWS Console → DynamoDB → **Create table**

### 2. Настройте таблицу:
- **Table name**: `trading-signals`
- **Partition key**: `PK` (String)
- **Sort key**: `SK` (String)
- **Table settings**: Default settings
- **Create table**

**✅ Таблица создана!**

---

## Часть 2: Создание Deployment Package (5 минут)

### Откройте PowerShell/Terminal:

```bash
cd C:\Users\annam\Documents\DeFi-RAG-Project\trading_alert_system

# Создайте папку
mkdir lambda_package
cd lambda_package

# Установите зависимости
pip install -r ..\requirements_lambda.txt -t .

# Скопируйте код
xcopy /E /I ..\src src
copy ..\lambda_function.py .
```

### Создайте ZIP:
1. Откройте `lambda_package` в проводнике
2. Выделите **ВСЕ файлы** (Ctrl+A)
3. Правый клик → Отправить → Сжатая ZIP-папка
4. Назовите: `trading-signals.zip`

**✅ ZIP готов!**

---

## Часть 3: AWS Lambda (10 минут)

### 1. Создайте функцию:
- AWS Console → Lambda → **Create function**
- Name: `trading-signals`
- Runtime: **Python 3.11**
- Create function

### 2. Загрузите код:
- Upload from → .zip file
- Выберите `trading-signals.zip`
- Handler: `lambda_function.lambda_handler`

### 3. Настройте переменные:
Configuration → Environment variables → Edit

**Обязательные:**
- `GOOGLE_SHEETS_SPREADSHEET_ID` = ваш ID таблицы
- `GOOGLE_SERVICE_ACCOUNT_JSON` = ваш JSON ключ
- `TRADING_ALERT_PUSHOVER_API_TOKEN` = ваш Pushover токен
- **`DYNAMODB_TABLE_NAME` = `trading-signals`** ⚠️ ВАЖНО!

**Опциональные (если есть API ключи):**
- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `COINBASE_API_KEY`
- `COINBASE_API_SECRET`

### 4. Добавьте права DynamoDB:
Configuration → Permissions → роль (откроется IAM)
- **Add permissions** → **Attach policies**
- Найдите **`AmazonDynamoDBFullAccess`**
- **Attach policy**

⚠️ **БЕЗ ЭТОГО ШАГА LAMBDA НЕ СМОЖЕТ СОХРАНЯТЬ СОСТОЯНИЕ!**

### 5. Настройте ресурсы:
Configuration → General configuration → Edit
- Memory: **512 MB**
- Timeout: **1 min**

### 6. Добавьте триггер:
Add trigger → EventBridge (CloudWatch Events)
- Rule name: `hourly-check`
- Schedule: `rate(1 hour)`
- Add

---

## Часть 4: Тестирование (5 минут)

### Ручной запуск:
1. Test → Create test event
2. Event name: `test`
3. JSON: `{}`
4. Save → Test

### Проверка логов:
- Monitor → View CloudWatch logs
- Должны быть логи: "✅ DynamoDB storage initialized"

### Проверка DynamoDB:
- DynamoDB → Tables → trading-signals → Explore table items
- Должны появиться сохраненные сигналы

---

## 🎉 Готово!

Теперь Lambda:
- ✅ Читает сигналы из Google Sheets каждый час
- ✅ Проверяет цены на биржах
- ✅ Сохраняет состояние в DynamoDB
- ✅ Отправляет Pushover уведомления
- ✅ НЕ спамит повторными уведомлениями

**Стоимость: ~$0.02/месяц** 💰

---

## 🔍 Мониторинг

**CloudWatch Logs:**
- AWS Console → CloudWatch → Log groups
- Найдите `/aws/lambda/trading-signals`

**DynamoDB:**
- DynamoDB → Tables → trading-signals → Explore table items
- Проверяйте `active` и `triggered_count`

**Отключить/включить:**
- Lambda → Configuration → Triggers
- Disable/Enable правило

---

## ⚠️ Troubleshooting

### "Module not found"
- Убедитесь что ZIP содержит файлы в корне (не папку)
- Проверьте что `src/` папка есть в ZIP

### "Google Sheets connection failed"
- Проверьте `GOOGLE_SERVICE_ACCOUNT_JSON`
- Проверьте права доступа к таблице

### "Timeout"
- Увеличьте Timeout до 2-3 минут
- Проверьте что биржи отвечают

### "DynamoDB access denied"
- Проверьте что добавили `AmazonDynamoDBFullAccess`
- Проверьте `DYNAMODB_TABLE_NAME` = `trading-signals`

---

## 📊 Расчет стоимости:

**Lambda:** $0.00 ✅
- ~720 вызовов/месяц
- В пределах FREE TIER (1M вызовов/мес)

**DynamoDB:** ~$0.02/месяц 💰
- Write: ~720 записей × $1.25/1M = $0.0009
- Read: ~720 чтений × $0.25/1M = $0.0002
- Storage: ~1 MB × $0.25/GB = $0.00
- Update: ~10 обновлений × $1.25/1M = $0.00001
- **Итого: ~$0.02/мес** (с запасом)

**CloudWatch:** $0.00 ✅
- ~500 MB логов/месяц
- В пределах FREE TIER (5GB/мес)

**ИТОГО: ~$0.02/месяц** 🎉

---

## 💡 Почему $0.02 - это отличная инвестиция:

✅ **Надежность:** Нет спама уведомлений
✅ **Правильная архитектура:** Состояние хранится корректно
✅ **Простая миграция:** При переходе на Fan-Out ничего не меняется
✅ **2 цента в месяц:** Меньше чем чашка кофе в год!

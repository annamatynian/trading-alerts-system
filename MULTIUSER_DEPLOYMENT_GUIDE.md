# ЁЯМР Multi-User Deployment Guide - Пошаговая Инструкция

## ЁЯМО Обзор

Эта инструкция покажет как развернуть систему с поддержкой нескольких пользователей, где каждый получает уведомления на свой телефон.

---

## ✅ Что уже готово (закоммичено)

- ✅ User ID обязательное поле в Gradio UI
- ✅ Фильтр по User ID
- ✅ Сохранение user_id в DynamoDB
- ✅ Модель данных SignalTarget с полем user_id
- ✅ Скрипты тестовых данных (anna, tomas)
- ✅ SecretsManager helper для работы с AWS Secrets
- ✅ Обновленный NotificationService с Secrets Manager поддержкой

---

## ЁЯМР Шаги развертывания

### **ШАГ 1: Настройка AWS Secrets Manager** (15 минут)

#### 1.1 Получите Pushover ключи

**A. Pushover App Token** (один для всего приложения)

1. Зайдите на https://pushover.net/apps/build
2. Создайте приложение:
   - Name: `Trading Alerts`
   - Description: `Multi-user trading price alerts`
   - URL: (оставьте пустым)
3. Скопируйте **API Token/Key** (выглядит как: `azgDf21y8MBH1j7X9K8y`)

**B. Pushover User Keys** (для каждого пользователя)

**Для Anna:**
1. Зайдите на https://pushover.net/ (ваш личный аккаунт)
2. После логина видите **Your User Key** в правом верхнем углу
3. Скопируйте ключ (выглядит как: `uQiRzpo4DXghDmr9QzzfQu27cmVRsG`)

**Для Tomas:**
1. Попросите Tomas зарегистрироваться на https://pushover.net/
2. Попросите скопировать его **User Key**
3. Он присылает вам ключ

---

#### 1.2 Создайте секрет в AWS Secrets Manager

1. Откройте AWS Console: https://console.aws.amazon.com/
2. Регион: **eu-west-1** (Ireland)
3. Найдите **AWS Secrets Manager**
4. Нажмите **"Store a new secret"**

**Настройка секрета:**

- **Secret type:** `Other type of secret`
- **Key/value:** Нажмите **"Plaintext"** tab

Вставьте (замените ключи на реальные):

```json
{
  "pushover_api_token": "azgDf21y8MBH1j7X9K8y",
  "users": {
    "anna": {
      "pushover_user_key": "uQiRzpo4DXghDmr9QzzfQu27cmVRsG",
      "name": "Anna",
      "phone": "iPhone",
      "enabled": true
    },
    "tomas": {
      "pushover_user_key": "uXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
      "name": "Tomas",
      "phone": "Android",
      "enabled": true
    },
    "default": {
      "pushover_user_key": "uQiRzpo4DXghDmr9QzzfQu27cmVRsG",
      "name": "Default User",
      "enabled": true
    }
  }
}
```

- **Secret name:** `trading-alerts/users`
- **Description:** `Multi-user Pushover keys mapping`
- Нажмите **"Next"** → **"Next"** → **"Store"**

✅ **Готово!** ARN секрета примерно:
```
arn:aws:secretsmanager:eu-west-1:123456789:secret:trading-alerts/users-AbCdEf
```

---

### **ШАГ 2: Настройка прав для Lambda** (10 минут)

#### 2.1 Найдите роль Lambda

1. Откройте **AWS Lambda Console**
2. Найдите вашу функцию (например: `trading-alerts-checker`)
3. Перейдите в **Configuration** → **Permissions**
4. Кликните на **Execution role name** (откроется IAM)

---

#### 2.2 Добавьте права на Secrets Manager

1. В IAM Role нажмите **"Add permissions"** → **"Create inline policy"**
2. Выберите **JSON** tab
3. Вставьте:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:eu-west-1:*:secret:trading-alerts/users-*"
    }
  ]
}
```

4. Нажмите **"Review policy"**
5. **Name:** `SecretsManagerReadAccess`
6. Нажмите **"Create policy"**

✅ **Готово!** Lambda теперь может читать секреты.

---

### **ШАГ 3: Обновление Lambda функции** (20 минут)

#### 3.1 Добавьте переменные окружения

В Lambda Console:
1. **Configuration** → **Environment variables**
2. Нажмите **"Edit"**
3. Добавьте:
   ```
   SECRET_NAME = trading-alerts/users
   USE_SECRETS_MANAGER = true
   ```
4. Нажмите **"Save"**

---

#### 3.2 Обновите код Lambda

**Вариант А: Через GitHub**

Если Lambda подключена к GitHub (recommended):

1. Ваши изменения уже в ветке `claude/add-user-id-filter-01WW9hA7TdLqL96pHYXAdB6g`
2. Сделайте merge в main branch
3. Lambda автоматически подхватит изменения

**Вариант Б: Вручную через AWS Console**

1. Скачайте файлы из GitHub:
   - `src/utils/secrets_manager.py` (новый)
   - `src/services/notification.py` (обновленный)
2. Откройте Lambda в AWS Console
3. Загрузите файлы в соответствующие директории
4. Нажмите **"Deploy"**

**Вариант В: Через AWS CLI**

```bash
# Упакуйте код
zip -r lambda_package.zip . -x "*.git*" "venv/*" "__pycache__/*"

# Загрузите в Lambda
aws lambda update-function-code \
  --function-name trading-alerts-checker \
  --zip-file fileb://lambda_package.zip \
  --region eu-west-1
```

---

### **ШАГ 4: Тестирование** (15 минут)

#### 4.1 Локальное тестирование Secrets Manager

Создайте файл `test_secrets.py`:

```python
from src.utils.secrets_manager import get_secrets_manager

# Получаем секреты
sm = get_secrets_manager(
    secret_name="trading-alerts/users",
    region="eu-west-1"
)

# Проверяем API token
api_token = sm.get_pushover_api_token()
print(f"✅ API Token: {api_token[:10]}...")

# Проверяем пользователей
users = sm.list_users()
print(f"✅ Users: {users}")

# Проверяем конкретного пользователя
anna_key = sm.get_user_pushover_key("anna")
print(f"✅ Anna's key: {anna_key[:10]}...")

tomas_key = sm.get_user_pushover_key("tomas")
print(f"✅ Tomas's key: {tomas_key[:10]}...")
```

Запустите:
```bash
python test_secrets.py
```

Ожидаемый вывод:
```
✅ API Token: azgDf21y8M...
✅ Users: ['anna', 'tomas', 'default']
✅ Anna's key: uQiRzpo4DX...
✅ Tomas's key: uXXXXXXXXX...
```

---

#### 4.2 Тестирование Lambda

1. В Lambda Console нажмите **"Test"**
2. **Event name:** `test-multiuser`
3. **Event JSON:**
   ```json
   {
     "test": true
   }
   ```
4. Нажмите **"Test"**

Проверьте CloudWatch Logs:
- ✅ `Pushover API token loaded from AWS Secrets Manager`
- ✅ `Loaded 3 users from Secrets Manager: anna, tomas, default`

---

#### 4.3 Полный тест с реальным сигналом

**A. Создайте тестовые сигналы через Gradio:**

1. Откройте Gradio UI (локально или Hugging Face)
2. Создайте сигнал:
   - User ID: `anna`
   - Symbol: `BTCUSDT`
   - Target Price: `1` (заведомо низкая цена для теста)
   - Condition: `above`
3. Нажмите **"Create Signal"**

**B. Запустите Lambda вручную:**

Lambda найдет сигнал, проверит цену BTC (больше $1), и отправит Pushover на телефон Anna.

**C. Проверьте телефон Anna:**

Должно прийти push-уведомление:
```
🚨 Alert: BTC Alert
Symbol: BTCUSDT
Exchange: BINANCE
Current Price: $94,523.45
Target: $1.00
```

---

### **ШАГ 5: Hugging Face Spaces** (10 минут)

#### 5.1 Синхронизация GitHub → Hugging Face

1. Зайдите на Hugging Face: https://huggingface.co/spaces/[ваш-username]/trading-alerts
2. Нажмите **"Settings"**
3. Найдите **"Sync from GitHub"**
4. Выберите branch: `claude/add-user-id-filter-01WW9hA7TdLqL96pHYXAdB6g`
5. Нажмите **"Sync"**

Или сделайте merge в main и синхронизируйте main.

---

#### 5.2 Настройте Secrets на Hugging Face

1. В Settings → **"Repository secrets"**
2. Добавьте:
   ```
   AWS_ACCESS_KEY_ID = AKIA...
   AWS_SECRET_ACCESS_KEY = ...
   AWS_DEFAULT_REGION = eu-west-1
   DYNAMODB_TABLE_NAME = trading-signals-eu
   DYNAMODB_REGION = eu-west-1
   ```

---

#### 5.3 Перезапустите Space

1. Нажмите **"Restart Space"**
2. Подождите ~2-3 минуты
3. Откройте Space URL

---

### **ШАГ 6: Финальный тест Multi-User** (10 минут)

#### 6.1 Создайте сигналы для обоих пользователей

**Сигнал Anna:**
- User ID: `anna`
- Symbol: `BTCUSDT`
- Target: `100000` (future price)
- Condition: `above`

**Сигнал Tomas:**
- User ID: `tomas`
- Symbol: `ETHUSDT`
- Target: `5000` (future price)
- Condition: `above`

---

#### 6.2 Проверьте фильтр

1. Перейдите в **"View Signals"**
2. Введите `anna` → Нажмите **"🔍 Filter"**
   - Видите только сигнал Anna
3. Введите `tomas` → Нажмите **"🔍 Filter"**
   - Видите только сигнал Tomas
4. Нажмите **"🔄 Refresh All"**
   - Видите оба сигнала

✅ **Фильтр работает!**

---

#### 6.3 Ждите уведомления

Когда Lambda запустится (каждый час) и цена BTC достигнет $100k:
- Anna получит push на свой телефон
- Tomas НЕ получит (его сигнал на ETH)

Когда ETH достигнет $5k:
- Tomas получит push на свой телефон
- Anna НЕ получит (её сигнал уже сработал)

---

## ЁЯМН Итоговая архитектура

```
Gradio UI
    ├─ Anna создает сигнал (user_id: anna)
    └─ Tomas создает сигнал (user_id: tomas)
              ↓
         DynamoDB
         (хранит сигналы с user_id)
              ↓
    Lambda (каждый час)
         ├─ Читает сигналы
         ├─ Проверяет цены
         └─ Если триггер:
              ↓
    AWS Secrets Manager
         ├─ Находит user_id сигнала
         └─ Получает Pushover key для этого user
              ↓
         Pushover API
              ├─ Отправка на телефон Anna (если сигнал Anna)
              └─ Отправка на телефон Tomas (если сигнал Tomas)
```

---

## ЁЯЪл Проверка что всё работает

### Checklist:

- [ ] AWS Secrets Manager создан
- [ ] Pushover ключи добавлены
- [ ] Lambda роль имеет права на Secrets
- [ ] Lambda код обновлен
- [ ] Переменные окружения настроены
- [ ] Локальный тест secrets прошел
- [ ] Gradio UI синхронизирован
- [ ] Тестовые сигналы созданы
- [ ] Фильтр по User ID работает
- [ ] Lambda отправляет на правильные телефоны

---

## ЁЯЪА Troubleshooting

### Ошибка: "AccessDeniedException" в Lambda

**Проблема:** Lambda не может читать Secrets Manager

**Решение:**
1. Проверьте IAM роль Lambda
2. Убедитесь что добавлена policy `SecretsManagerReadAccess`
3. Проверьте ARN в policy совпадает с ARN секрета

---

### Ошибка: "Secret not found"

**Проблема:** Неправильное имя секрета

**Решение:**
1. Проверьте что секрет называется `trading-alerts/users`
2. Проверьте регион (должен быть `eu-west-1`)
3. В переменных окружения Lambda должно быть `SECRET_NAME=trading-alerts/users`

---

### Pushover не приходит

**Проблема:** Неправильные ключи или user_id

**Решение:**
1. Проверьте Pushover User Key в Secrets Manager
2. Проверьте что user_id в сигнале совпадает с ключом в секрете
3. Проверьте логи Lambda в CloudWatch
4. Проверьте quota на Pushover.net (10000 сообщений/месяц)

---

### Фильтр не работает в Gradio

**Проблема:** Старая версия кода

**Решение:**
1. Синхронизируйте GitHub → Hugging Face
2. Перезапустите Space
3. Очистите кеш браузера

---

## ЁЯМР Готово!

Теперь у вас полностью работающая multi-user система:
- ✅ Anna видит только свои сигналы
- ✅ Tomas видит только свои сигналы
- ✅ Каждый получает уведомления на свой телефон
- ✅ Все ключи безопасно хранятся в AWS Secrets Manager

**Следующие шаги:**
- Добавить больше пользователей (просто добавьте в Secrets Manager)
- Настроить Google Sheets с колонкой user_id
- Настроить автоматический backup DynamoDB

**Вопросы?** Проверьте `SYSTEM_INTEGRATION_DIAGRAM.md` для понимания архитектуры!

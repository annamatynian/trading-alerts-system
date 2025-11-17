# 🔐 Настройка AWS Secrets Manager для Multi-User поддержки

## Шаг 1: Создание секрета в AWS Console

### 1.1 Откройте AWS Secrets Manager

1. Зайдите в AWS Console: https://console.aws.amazon.com/
2. Выберите регион: **eu-west-1** (Ireland) - тот же что и DynamoDB
3. Найдите сервис **Secrets Manager**
4. Нажмите **"Store a new secret"**

---

### 1.2 Создайте секрет

**Secret type:** `Other type of secret`

**Key/value pairs:**

Нажмите "Plaintext" и вставьте:

```json
{
  "pushover_api_token": "ваш_pushover_app_token",
  "users": {
    "anna": {
      "pushover_user_key": "ваш_pushover_user_key",
      "name": "Anna",
      "phone": "iPhone",
      "enabled": true
    },
    "tomas": {
      "pushover_user_key": "pushover_user_key_томаса",
      "name": "Tomas",
      "phone": "Android",
      "enabled": true
    },
    "default": {
      "pushover_user_key": "ваш_pushover_user_key",
      "name": "Default User",
      "enabled": true
    }
  }
}
```

**Encryption key:** `aws/secretsmanager` (по умолчанию)

---

### 1.3 Назовите секрет

**Secret name:** `trading-alerts/users`

**Description:** `User mapping for multi-user trading alerts with Pushover keys`

**Tags (опционально):**
- Key: `Project`, Value: `trading-alerts`
- Key: `Environment`, Value: `production`

---

### 1.4 Настройте автоматическую ротацию

**Automatic rotation:** Disabled (пока не нужно)

---

### 1.5 Подтвердите и создайте

Нажмите **"Store"**

**Результат:** Секрет создан с ARN похожим на:
```
arn:aws:secretsmanager:eu-west-1:123456789012:secret:trading-alerts/users-AbCdEf
```

---

## Шаг 2: Где взять Pushover ключи

### 2.1 Pushover App Token (API Token)

1. Зайдите на https://pushover.net/apps/build
2. Создайте приложение "Trading Alerts"
3. Скопируйте **API Token/Key** (например: `azgDf21y8MBH1j7X9K8y`)
4. Это ваш `pushover_api_token`

### 2.2 Pushover User Key (для каждого пользователя)

1. Зайдите на https://pushover.net/
2. После логина видите **Your User Key**
3. Скопируйте ключ (например: `uQiRzpo4DXghDmr9QzzfQu27cmVRsG`)
4. Это `pushover_user_key` для пользователя

**Для друга (tomas):**
- Попросите его зарегистрироваться на pushover.net
- Попросите скопировать его User Key
- Используйте его ключ в секрете

---

## Шаг 3: Настройка прав для Lambda

### 3.1 Создайте IAM Policy

Создайте файл `iam_policy_secrets.json`:

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

### 3.2 Добавьте policy к Lambda роли

1. Откройте **IAM Console** → **Roles**
2. Найдите роль вашей Lambda (например: `trading-alerts-lambda-role`)
3. Нажмите **"Add permissions"** → **"Create inline policy"**
4. Вставьте JSON из `iam_policy_secrets.json`
5. Назовите: `SecretsManagerReadAccess`
6. Нажмите **"Create policy"**

---

## Шаг 4: Проверка

### 4.1 Через AWS CLI

```bash
aws secretsmanager get-secret-value \
  --secret-id trading-alerts/users \
  --region eu-west-1
```

Должно вернуть JSON с вашими пользователями.

### 4.2 Через Python (локально)

```python
import boto3
import json

client = boto3.client('secretsmanager', region_name='eu-west-1')
response = client.get_secret_value(SecretId='trading-alerts/users')
secret = json.loads(response['SecretString'])

print("Users:", list(secret['users'].keys()))
print("Anna's key:", secret['users']['anna']['pushover_user_key'])
```

---

## Шаг 5: Переменные окружения для Lambda

В Lambda добавьте переменную окружения:

```
SECRET_NAME = trading-alerts/users
AWS_REGION = eu-west-1
```

---

## ✅ Готово!

После выполнения этих шагов:
- ✅ AWS Secrets Manager хранит mapping пользователей
- ✅ Lambda может читать секреты
- ✅ Каждый пользователь получает уведомления на свой телефон

---

## 📝 Пример итоговой структуры

```
AWS Secrets Manager: trading-alerts/users
├─ pushover_api_token: "azgDf21y8MBH1j7X9K8y"
└─ users:
   ├─ anna:
   │  ├─ pushover_user_key: "uQiRzpo4DXghDmr9QzzfQu27cmVRsG"
   │  ├─ name: "Anna"
   │  └─ enabled: true
   ├─ tomas:
   │  ├─ pushover_user_key: "uXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
   │  ├─ name: "Tomas"
   │  └─ enabled: true
   └─ default:
      └─ pushover_user_key: "uQiRzpo4DXghDmr9QzzfQu27cmVRsG"
```

---

## 🚨 Важно!

- **Никогда** не коммитьте Pushover ключи в GitHub!
- Храните их только в AWS Secrets Manager
- Используйте разные User Keys для разных людей
- API Token один для всего приложения

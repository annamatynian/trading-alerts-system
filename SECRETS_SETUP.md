# HF Spaces Secrets Configuration Guide

Подробная инструкция по настройке всех секретов для Hugging Face Spaces.

## 📍 Где добавлять Secrets

1. Откройте ваш Space на Hugging Face
2. Перейдите в **Settings** (⚙️ вверху справа)
3. Найдите секцию **Repository Secrets**
4. Нажмите **"Add a Secret"**

## 🔐 Required Secrets

### 1. AWS_ACCESS_KEY_ID

**Описание**: AWS Access Key для доступа к DynamoDB

**Как получить**:
1. Перейдите в [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Users → Create User
3. Attach policies: `AmazonDynamoDBFullAccess`
4. Create Access Key → Copy **Access Key ID**

**Формат**:
```
AKIA...  (20 символов, начинается с AKIA)
```

**Пример**:
```
AKIAIOSFODNN7EXAMPLE
```

---

### 2. AWS_SECRET_ACCESS_KEY

**Описание**: AWS Secret Key (парный к Access Key)

**Как получить**:
1. При создании Access Key (см. выше)
2. Copy **Secret Access Key** (показывается только один раз!)

**Формат**:
```
40 символов (буквы, цифры, +, /)
```

**Пример**:
```
wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

---

### 3. AWS_DEFAULT_REGION

**Описание**: AWS регион где находится ваша DynamoDB таблица

**Формат**:
```
eu-west-1  (или другой регион)
```

**Возможные значения**:
- `us-east-1` (N. Virginia)
- `us-west-2` (Oregon)
- `eu-west-1` (Ireland)
- `eu-central-1` (Frankfurt)
- `ap-southeast-1` (Singapore)

---

### 4. DYNAMODB_TABLE_NAME

**Описание**: Название вашей DynamoDB таблицы

**Формат**:
```
trading-alerts
```

**Требования к таблице**:
- **Partition Key**: `PK` (String)
- **Sort Key**: `SK` (String)

**Как создать таблицу**:
1. Перейдите в [DynamoDB Console](https://console.aws.amazon.com/dynamodb/)
2. Create Table
3. Table name: `trading-alerts`
4. Partition key: `PK` (String)
5. Add Sort key: `SK` (String)
6. Create

---

### 5. PUSHOVER_APP_TOKEN

**Описание**: Token вашего Pushover приложения

**Как получить**:
1. Зарегистрируйтесь на [pushover.net](https://pushover.net)
2. Login → Create New Application/API Token
3. Fill in:
   - Name: `Trading Alerts`
   - Type: `Application`
4. Copy **API Token**

**Формат**:
```
30 символов (буквы и цифры)
```

**Пример**:
```
azGDORePK8gMaC0QOYAMyEEuzJnyUi
```

---

### 6. JWT_SECRET_KEY

**Описание**: Секретный ключ для JWT токенов (аутентификация)

**Как создать**:
```bash
# Вариант 1: Random string
openssl rand -base64 32

# Вариант 2: UUID
python -c "import uuid; print(uuid.uuid4().hex)"

# Вариант 3: Просто сложная строка
your-super-secret-key-change-this-to-random-value-12345
```

**Требования**:
- Минимум 32 символа
- Сложная (буквы, цифры, спецсимволы)
- Уникальная (не используйте примеры!)

**Пример**:
```
7f3e9a1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f
```

---

### 7. GOOGLE_SERVICE_ACCOUNT_JSON

**Описание**: JSON ключ Google Service Account для доступа к Google Sheets

**Как получить**:

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com)
2. Create Project (если нет)
3. Enable **Google Sheets API**
4. IAM & Admin → Service Accounts → Create Service Account
5. Grant role: `Editor` or `Viewer`
6. Keys → Add Key → Create new key → JSON
7. Скачается файл `project-name-xxxxx.json`

**Формат**: Весь JSON файл одной строкой

**Пример**:
```json
{"type":"service_account","project_id":"trading-signals-123456","private_key_id":"abc123...","private_key":"-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq...\n-----END PRIVATE KEY-----\n","client_email":"service-account@project.iam.gserviceaccount.com","client_id":"123456789","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token"}
```

**ВАЖНО**:
- Копируйте ВЕСЬ содержимое JSON файла
- Должно быть одной строкой (без переносов внутри, кроме `\n` в приватном ключе)
- Не забудьте дать доступ к Google Sheets для email из Service Account!

---

### 8. GOOGLE_SHEETS_SPREADSHEET_ID

**Описание**: ID вашей Google таблицы с сигналами

**Как получить**:
1. Откройте вашу Google таблицу
2. Скопируйте ID из URL:

```
https://docs.google.com/spreadsheets/d/1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1/edit
                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                        Это ваш SPREADSHEET_ID
```

**Формат**:
```
44 символа (буквы, цифры, дефисы, подчеркивания)
```

**Пример**:
```
1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1
```

**ВАЖНО**: Дайте доступ к таблице для email из Service Account:
- Share → Add email из `client_email` в JSON
- Права: `Editor` or `Viewer`

---

## ⚙️ Optional Secrets (API ключи бирж)

### BINANCE_API_KEY & BINANCE_API_SECRET

**Описание**: API ключи для Binance (не обязательно для публичных цен)

**Как получить**:
1. [Binance](https://www.binance.com) → Account → API Management
2. Create API
3. Enable: **Enable Reading** (остальное выключить!)
4. Copy **API Key** и **Secret Key**

### COINBASE_API_KEY & COINBASE_API_SECRET

**Описание**: API ключи для Coinbase Pro

**Как получить**:
1. [Coinbase Pro](https://pro.coinbase.com) → Settings → API
2. New API Key
3. Permissions: **View** only
4. Copy **Key** и **Secret**

---

## ✅ Checklist для проверки

После добавления всех секретов, убедитесь:

- [ ] AWS credentials работают (проверьте IAM permissions)
- [ ] DynamoDB таблица создана (PK: `PK`, SK: `SK`)
- [ ] Pushover App Token получен
- [ ] JWT Secret Key сгенерирован (минимум 32 символа)
- [ ] Google Service Account JSON скопирован целиком
- [ ] Google Sheets ID корректный
- [ ] Email из Service Account добавлен в Google Sheets (Share)
- [ ] Все secrets добавлены в HF Spaces Settings → Repository Secrets
- [ ] Space перезапущен после добавления secrets

---

## 🐛 Troubleshooting

### "Missing required secrets"

Проверьте:
1. Все ли secrets добавлены в Repository Secrets
2. Правильное ли написание имён (с учётом регистра!)
3. Перезапустите Space после добавления

### "AWS credentials invalid"

Проверьте:
1. Access Key ID начинается с `AKIA`
2. Secret Access Key 40 символов
3. IAM user имеет права на DynamoDB
4. Region совпадает с регионом таблицы

### "DynamoDB table not found"

Проверьте:
1. Таблица создана в правильном регионе
2. Имя таблицы написано правильно (case-sensitive!)
3. Таблица имеет правильные ключи (PK, SK)

### "Pushover API error"

Проверьте:
1. App Token правильный (30 символов)
2. Пользователь добавил свой User Key в Settings UI
3. Pushover аккаунт активен

### "Google Sheets permission denied"

Проверьте:
1. Service Account JSON скопирован полностью
2. Email из `client_email` добавлен в Share таблицы
3. Spreadsheet ID правильный (из URL)

---

## 📞 Support

Если возникли проблемы:
1. Проверьте Logs в Settings → Logs
2. Убедитесь что все secrets корректны
3. Перезапустите Space после изменений

---

**Ready to deploy?** → [README_HF.md](./README_HF.md)

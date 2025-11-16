# 🤗 ПОЛНЫЙ ГАЙД: Деплой на Hugging Face Spaces

## 🎯 Что вы получите

После выполнения этого гайда у вас будет:

- ✅ Публичный URL для вашего Gradio UI
- ✅ Бесплатный хостинг (CPU tier)
- ✅ Автоматический деплой при push в Git
- ✅ HTTPS из коробки
- ✅ Доступ с любого устройства

**Примерный URL:** `https://huggingface.co/spaces/YOUR_USERNAME/trading-signal-system`

---

## ⏱️ Время: 15-20 минут

---

## 📋 ШАГ 1: Создайте аккаунт на Hugging Face (2 минуты)

### 1.1 Зарегистрируйтесь

Откройте: https://huggingface.co/join

```
Email: ваш email
Username: ваш username (запомните!)
Password: ваш пароль
```

### 1.2 Подтвердите email

Проверьте почту и кликните на ссылку подтверждения.

---

## 📋 ШАГ 2: Создайте новый Space (3 минуты)

### 2.1 Перейдите в Spaces

Откройте: https://huggingface.co/spaces

Нажмите **"Create new Space"**

### 2.2 Заполните форму

```
Owner: [ваш username]
Space name: trading-signal-system
License: MIT
Select the Space SDK: Gradio
Space hardware: CPU basic (free) ✅
Visibility: Public (или Private если хотите)
```

Нажмите **"Create Space"**

### 2.3 Что получили

Hugging Face создаст:
- Git репозиторий для вашего Space
- URL: `https://huggingface.co/spaces/USERNAME/trading-signal-system`
- Готовую структуру для Gradio приложения

---

## 📋 ШАГ 3: Подготовка файлов проекта (5 минут)

### 3.1 Переименуйте главный файл

В вашем проекте:

```bash
cd C:\Users\annam\Documents\DeFi-RAG-Project\trading_alert_system

# Переименуйте gradio_app.py в app.py
# (Hugging Face ищет app.py по умолчанию)
```

**Windows:**
```bash
copy gradio_app.py app.py
```

**Linux/Mac:**
```bash
cp gradio_app.py app.py
```

### 3.2 Создайте/обновите requirements.txt

Убедитесь что `requirements.txt` содержит все необходимое:

```txt
# Core dependencies
gradio>=4.0.0
pandas
pydantic>=2.0.0

# AWS
boto3
botocore

# Exchanges
ccxt

# Google Sheets (optional)
google-api-python-client
google-auth-httplib2
google-auth-oauthlib

# Notifications
requests

# Async
aiohttp
asyncio
```

### 3.3 Создайте README.md для Space

Создайте файл `README_SPACE.md` (или просто отредактируйте существующий README.md):

```markdown
---
title: Trading Signal System
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
---

# Trading Signal System

Автоматическая система мониторинга криптовалютных цен.

## Features

- Create trading signals with target prices
- Monitor multiple exchanges (Binance, Bybit, Coinbase)
- Real-time price checking
- DynamoDB integration
- Google Sheets sync (optional)

## Usage

1. Go to "Create Signal" tab
2. Fill in the form
3. Click "Create Signal"
4. Your signal is saved to DynamoDB
5. AWS Lambda checks hourly and sends Pushover notifications

Enjoy! 🎉
```

### 3.4 Проверьте структуру проекта

Убедитесь что у вас есть:

```
trading_alert_system/
├── app.py                       ← ГЛАВНЫЙ ФАЙЛ (renamed from gradio_app.py)
├── requirements.txt             ← Зависимости
├── README.md                    ← Описание Space
├── src/                         ← Вся структура кода
│   ├── models/
│   ├── exchanges/
│   ├── services/
│   ├── storage/
│   └── utils/
├── .env.example                 ← Пример переменных (НЕ коммитим .env!)
└── .gitignore                   ← Убедитесь что .env в игноре
```

---

## 📋 ШАГ 4: Настройка Git и Push в HF (5 минут)

### 4.1 Инициализируйте Git (если еще не сделано)

```bash
cd C:\Users\annam\Documents\DeFi-RAG-Project\trading_alert_system

# Если нет Git репозитория
git init
```

### 4.2 Добавьте Hugging Face remote

```bash
# Замените USERNAME на ваш username на HF
git remote add hf https://huggingface.co/spaces/USERNAME/trading-signal-system
```

**Пример:**
```bash
git remote add hf https://huggingface.co/spaces/basilisca/trading-signal-system
```

### 4.3 Проверьте .gitignore

Убедитесь что `.gitignore` содержит:

```
.env
*.json
secret-*.json
*.pem
lambda_deployment*.zip
__pycache__/
*.pyc
.pytest_cache/
venv/
.vscode/
```

### 4.4 Commit изменения

```bash
# Добавьте все файлы
git add app.py requirements.txt README.md src/

# Commit
git commit -m "Initial deployment to Hugging Face Spaces"
```

### 4.5 Push в Hugging Face

```bash
# Push в HF Space
git push hf main
```

**Если main ветка не существует:**
```bash
git branch -M main
git push hf main
```

**Если просят аутентификацию:**
- Username: ваш HF username
- Password: используйте **Access Token** (не пароль!)
  - Создайте токен: https://huggingface.co/settings/tokens
  - Token type: Write

---

## 📋 ШАГ 5: Настройка Secrets в Hugging Face (5 минут)

### 5.1 Откройте Settings

На странице вашего Space:

```
https://huggingface.co/spaces/USERNAME/trading-signal-system
```

Нажмите **Settings** (вкладка вверху)

### 5.2 Добавьте Repository Secrets

Прокрутите до раздела **"Repository secrets"**

Нажмите **"New secret"** и добавьте по одному:

#### AWS Credentials:
```
Name: AWS_ACCESS_KEY_ID
Value: AKIA...

Name: AWS_SECRET_ACCESS_KEY
Value: ...

Name: DYNAMODB_TABLE_NAME
Value: trading-alerts

Name: DYNAMODB_REGION
Value: us-east-2
```

#### Exchange API Keys (хотя бы одна биржа):
```
Name: BYBIT_API_KEY
Value: ...

Name: BYBIT_API_SECRET
Value: ...
```

Опционально (если используете):
```
Name: BINANCE_API_KEY
Value: ...

Name: BINANCE_API_SECRET
Value: ...

Name: COINBASE_API_KEY
Value: ...

Name: COINBASE_API_SECRET
Value: ...
```

#### Pushover (для уведомлений):
```
Name: PUSHOVER_APP_TOKEN
Value: ...

Name: PUSHOVER_USER_KEY
Value: ...
```

#### Google Sheets (опционально):
```
Name: GOOGLE_SPREADSHEET_ID
Value: ...
```

**Для Google Sheets credentials файла:**

Так как это JSON файл, есть два варианта:

**Вариант A:** Добавьте весь JSON как один secret:
```
Name: GOOGLE_SHEETS_CREDENTIALS
Value: {"type": "service_account", "project_id": "...", ...}  ← весь JSON
```

**Вариант B:** Загрузите JSON файл в Space:
1. В вашем Space → Files → Upload file
2. Загрузите `secret-medium-476300-m9-c141e07c30ad.json`
3. В app.py измените путь:
```python
GOOGLE_SHEETS_CREDENTIALS_PATH = "./secret-medium-476300-m9-c141e07c30ad.json"
```

### 5.3 Сохраните все secrets

После добавления всех secrets, они будут автоматически доступны как environment variables в вашем приложении.

---

## 📋 ШАГ 6: Модификация app.py для HF Spaces (3 минуты)

### 6.1 Измените функцию launch()

Откройте `app.py` и в самом низу измените:

**Было:**
```python
if __name__ == "__main__":
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True
    )
```

**Должно быть:**
```python
if __name__ == "__main__":
    app = create_interface()
    app.launch()  # HF сам настроит server_name и port
```

### 6.2 Обработка Google Sheets credentials

Если используете Google Sheets, добавьте в начало `app.py`:

```python
import os
import json

# Для Hugging Face Spaces: загрузка credentials из environment variable
def load_google_credentials():
    """Load Google Sheets credentials from env or file"""
    # Вариант 1: из environment variable (если JSON в secrets)
    creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        # Сохраняем во временный файл
        with open('/tmp/google_credentials.json', 'w') as f:
            json.dump(creds_dict, f)
        return '/tmp/google_credentials.json'
    
    # Вариант 2: файл уже в Space
    local_path = './secret-medium-476300-m9-c141e07c30ad.json'
    if os.path.exists(local_path):
        return local_path
    
    return None

# В функции init_services():
# Замените путь к credentials:
google_creds_path = load_google_credentials()
if google_creds_path:
    os.environ['GOOGLE_SHEETS_CREDENTIALS_PATH'] = google_creds_path
```

### 6.3 Commit и Push изменения

```bash
git add app.py
git commit -m "Update app.py for Hugging Face Spaces deployment"
git push hf main
```

---

## 📋 ШАГ 7: Проверка деплоя (2 минуты)

### 7.1 Откройте ваш Space

```
https://huggingface.co/spaces/USERNAME/trading-signal-system
```

### 7.2 Что должно происходить

Hugging Face автоматически:
1. ✅ Установит зависимости из requirements.txt
2. ✅ Загрузит secrets как environment variables
3. ✅ Запустит app.py
4. ✅ Покажет Gradio UI в iframe

**Процесс занимает 2-5 минут.**

### 7.3 Следите за логами

На странице Space:

- Вкладка **"Logs"** - реальное время логи
- Должны увидеть:
  ```
  ✅ DynamoDB initialized: trading-alerts in us-east-2
  ✅ Bybit initialized
  Running on public URL: https://USERNAME-trading-signal-system.hf.space
  ```

### 7.4 Проверьте UI

Gradio интерфейс должен загрузиться прямо на странице Space!

Попробуйте:
- Create Signal tab - создайте тестовый сигнал
- View Signals tab - посмотрите список
- Check Price tab - проверьте цену BTC

---

## 🎉 ГОТОВО!

### Ваш Trading Alert System теперь:

✅ **Доступен публично** по адресу:
```
https://huggingface.co/spaces/USERNAME/trading-signal-system
```

✅ **Работает 24/7** бесплатно (CPU tier)

✅ **Автоматически обновляется** при push в Git:
```bash
git add .
git commit -m "Update"
git push hf main
```

✅ **Интегрирован с вашим AWS Lambda** (Lambda проверяет сигналы каждый час)

---

## 🔧 Дополнительные настройки

### Добавление аутентификации

Если хотите защитить паролем:

В `app.py` измените launch():

```python
app.launch(
    auth=("admin", "your_password_here"),  # Username и пароль
    auth_message="Enter credentials to access Trading Signal System"
)
```

Или используйте environment variable:

```python
app.launch(
    auth=("admin", os.getenv("GRADIO_PASSWORD", "default_password"))
)
```

Добавьте secret в HF:
```
Name: GRADIO_PASSWORD
Value: your_secure_password
```

### Изменение видимости Space

Settings → Visibility:
- **Public** - любой может видеть и использовать
- **Private** - только вы

---

## 🐛 Troubleshooting

### ❌ Space не запускается

**Проверьте:**
1. Logs вкладка - что пишет в логах?
2. requirements.txt корректный?
3. app.py существует в корне?
4. Все secrets добавлены?

**Решение:**
```bash
# Локально проверьте что app.py работает
python app.py

# Если работает локально, проблема в secrets или requirements
```

### ❌ DynamoDB connection failed

**Проблема:** Secrets не загрузились

**Решение:**
1. Settings → Repository secrets
2. Проверьте что добавлены:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - DYNAMODB_TABLE_NAME
   - DYNAMODB_REGION

### ❌ No exchanges initialized

**Проблема:** Exchange API keys не настроены

**Решение:**
Добавьте хотя бы одну биржу в secrets:
- BYBIT_API_KEY
- BYBIT_API_SECRET

### ❌ Google Sheets не работает

**Решение:**

**Вариант 1:** Загрузите JSON файл в Space:
1. Files tab → Upload file
2. Загрузите credentials.json
3. Перезапустите Space

**Вариант 2:** JSON в secret:
1. Откройте ваш JSON файл
2. Скопируйте весь JSON (убедитесь что валидный!)
3. Settings → New secret:
   - Name: GOOGLE_SHEETS_CREDENTIALS
   - Value: {весь JSON}

---

## 📊 Мониторинг

### Проверка логов

```
Space page → Logs tab → Real-time logs
```

Должны видеть:
```
INFO: Started server process
INFO: Waiting for application startup
INFO: Application startup complete
Running on public URL: https://...
```

### Проверка использования

Settings → Usage:
- CPU usage
- Memory usage
- Storage usage

---

## 💰 Стоимость

**CPU basic tier:** БЕСПЛАТНО ✅

**Ограничения free tier:**
- 2 vCPU
- 16 GB RAM
- 50 GB Storage
- Unlimited requests

**Если нужно больше:**
- Upgraded CPU: $9/месяц
- GPU T4: $60/месяц
- GPU A10G: $300/месяц

Для Trading Signal System **CPU basic достаточно!**

---

## 🔄 Обновление Space

Когда хотите обновить код:

```bash
# Локально
cd trading_alert_system

# Измените код в app.py или других файлах

# Commit
git add .
git commit -m "Updated UI with new features"

# Push в HF
git push hf main

# Hugging Face автоматически перезапустит Space через 1-2 минуты
```

---

## 📚 Полезные ссылки

- **HF Spaces Docs:** https://huggingface.co/docs/hub/spaces
- **Gradio на HF:** https://huggingface.co/docs/hub/spaces-sdks-gradio
- **Ваш Space:** https://huggingface.co/spaces/USERNAME/trading-signal-system
- **HF Community:** https://discuss.huggingface.co/

---

## 🎊 Поздравляем!

Теперь у вас есть:

✅ Публичный Gradio UI на Hugging Face  
✅ Интеграция с AWS DynamoDB  
✅ Автоматический деплой  
✅ Бесплатный хостинг 24/7  

**Делитесь ссылкой с друзьями!** 🚀

```
https://huggingface.co/spaces/YOUR_USERNAME/trading-signal-system
```

---

*Последнее обновление: 14 ноября 2025*

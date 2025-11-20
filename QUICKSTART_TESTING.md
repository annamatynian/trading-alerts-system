# ⚡ Quick Start - Testing & Deployment

Быстрый старт для тестирования и деплоя.

---

## 🧪 Тестирование (на вашем компьютере)

### Шаг 1: Установите зависимости

```bash
pip install -r requirements.txt
```

### Шаг 2: Настройте .env

Создайте файл `.env` в корне проекта:

```bash
# Pushover (обязательно)
PUSHOVER_APP_TOKEN=azGDORePK8gMaC0QOYAMyEEuzJnyUi
PUSHOVER_USER_KEY=uQiRzpo4DXPMxz9aZXqJm6xPEszZmE

# AWS (для продакшн тестов)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCY
DYNAMODB_TABLE_NAME=trading-alerts
DYNAMODB_REGION=eu-west-1

# JWT
JWT_SECRET_KEY=your-secret-key-here-min-32-chars
```

### Шаг 3: Выберите тест

#### 🟢 ТЕСТ 1: Простая отправка Pushover (НАЧНИТЕ С ЭТОГО!)

```bash
python test_pushover_simple.py
```

**Время**: 30 секунд
**Проверяет**: Pushover credentials работают
**Результат**: Вы получите push-уведомление на телефон

---

#### 🟡 ТЕСТ 2: Полный flow с mock ценой

```bash
python test_full_flow.py
```

**Время**: 1 минута
**Проверяет**: Весь flow (сигнал → проверка → уведомление)
**Результат**: Получите уведомление с mock данными

---

#### 🔴 ТЕСТ 3: Реальная цена BTC

```bash
python test_real_price_alert.py
```

**Время**: 1-10 минут (зависит от колебания цены)
**Проверяет**: Реальная цена с Binance
**Результат**: Когда BTC изменится на $50 → получите уведомление

**Чтобы остановить**: `Ctrl+C`

---

#### 🎨 ТЕСТ 4: Gradio UI

```bash
python app_with_auth.py
```

**Время**: Интерактивно
**Проверяет**: UI, DynamoDB, аутентификация
**URL**: http://127.0.0.1:7860

**Чтобы остановить**: `Ctrl+C`

---

## 🚀 Деплой на Hugging Face Spaces

### Шаг 1: Создайте Space

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Choose:
   - **Name**: `trading-alerts-system`
   - **SDK**: Gradio
   - **Hardware**: CPU Basic (FREE)

### Шаг 2: Загрузите файлы

Загрузите эти файлы в ваш Space:

```
app_hf.py              # ← Main entry point for HF
requirements_hf.txt    # ← Dependencies
app_with_auth.py       # ← Gradio UI
src/                   # ← Весь каталог src/
```

### Шаг 3: Настройте Secrets

Go to **Settings → Repository Secrets**

Добавьте (см. подробности в [SECRETS_SETUP.md](./SECRETS_SETUP.md)):

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION
DYNAMODB_TABLE_NAME
PUSHOVER_APP_TOKEN
JWT_SECRET_KEY
GOOGLE_SERVICE_ACCOUNT_JSON
GOOGLE_SHEETS_SPREADSHEET_ID
```

### Шаг 4: Запустите Space

После добавления secrets → Space автоматически перезапустится.

Проверьте **Settings → Logs**:

```
✅ All required secrets found
✅ Background price checker thread started
🚀 Launching Gradio UI...
Running on http://0.0.0.0:7860
```

---

## 📁 Созданные файлы

### Тестовые скрипты:

- `test_pushover_simple.py` - Простой тест Pushover
- `test_full_flow.py` - Полный flow с mock
- `test_real_price_alert.py` - Реальная цена BTC

### Деплой файлы:

- `app_hf.py` - Entry point для Hugging Face
- `requirements_hf.txt` - Зависимости для HF
- `README_HF.md` - Инструкция по деплою
- `SECRETS_SETUP.md` - Подробности по secrets

### Документация:

- `TESTING_GUIDE.md` - Полная инструкция по тестам
- `QUICKSTART_TESTING.md` - Эта страница (краткая версия)

---

## ✅ Checklist

### Тестирование локально:

- [ ] Установлены зависимости (`pip install -r requirements.txt`)
- [ ] Создан `.env` файл с Pushover credentials
- [ ] Тест 1 прошёл (простая отправка)
- [ ] Тест 2 прошёл (full flow)
- [ ] Тест 3 прошёл (реальная цена) - опционально
- [ ] Тест 4 прошёл (Gradio UI) - опционально

### Деплой на HF:

- [ ] Space создан на Hugging Face
- [ ] Файлы загружены (`app_hf.py`, `requirements_hf.txt`, `src/`)
- [ ] Все Secrets добавлены
- [ ] Space запустился без ошибок (проверьте Logs)
- [ ] UI открывается и работает
- [ ] Можно зарегистрироваться / залогиниться
- [ ] Можно добавить сигнал
- [ ] Background price checker работает (проверьте Logs каждый час)

---

## 🆘 Проблемы?

### Pushover не приходит

→ Проверьте tokens в `.env`
→ Убедитесь что Pushover app установлен на телефоне

### Import errors

```bash
pip install -r requirements.txt
```

### DynamoDB access denied

→ Проверьте AWS credentials
→ Убедитесь что IAM user имеет права на DynamoDB

### Полная документация

→ [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Детальные инструкции
→ [SECRETS_SETUP.md](./SECRETS_SETUP.md) - Подробности по secrets
→ [README_HF.md](./README_HF.md) - Полный гайд по деплою

---

**Happy Testing!** 🚀

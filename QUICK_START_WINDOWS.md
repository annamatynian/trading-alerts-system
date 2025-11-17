# 🚀 Quick Start - Запуск на Windows

## Шаг 1: Проверь ветку

```bash
git branch --show-current
```

Должно быть: `claude/session-persistence-01Pv8ALJ5J24HHtguGQCiAoA`

Если нет:
```bash
git checkout claude/session-persistence-01Pv8ALJ5J24HHtguGQCiAoA
```

---

## Шаг 2: Установи зависимости

```bash
pip install PyJWT bcrypt boto3 pydantic pyyaml python-dotenv gradio
```

---

## Шаг 3: Запусти тесты (по возрастанию сложности)

### 1️⃣ Самый простой - Проверка синтаксиса (0.1 сек)
```bash
python test_syntax_only.py
```
**Ожидаемый результат:**
```
✅ All files have valid Python syntax!
8/8 files passed
```

---

### 2️⃣ Интерактивная демонстрация
```bash
python demo_auth.py
```
**Что покажет:**
- 🔐 Регистрация пользователя
- 🎫 Создание JWT токена
- ✅ Валидация токена
- 🔓 Logout
- 📚 Объяснения каждого шага

---

### 3️⃣ Unit тесты (8 tests)
```bash
python test_unit_auth.py
```
**Ожидаемый результат:**
```
✅ 8/8 tests PASSED
```

---

### 4️⃣ Production features тесты (7 tests)
```bash
python test_production_features.py
```
**Ожидаемый результат:**
```
✅ 6/7 tests PASSED
(1 AWS тест может не пройти - это норма для dev окружения)
```

---

### 5️⃣ Полный тест-набор
```bash
python test_all.py
```
**Требует:** Все зависимости установлены

---

## Шаг 4: Запусти приложение

### Создай `.env` файл:
```bash
# .env
JWT_SECRET_KEY=your-super-secret-key-min-32-chars-here
BCRYPT_ROUNDS=12
JWT_EXPIRATION_DAYS=30
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=300

# AWS (если используешь DynamoDB)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
DYNAMODB_REGION=eu-west-1
DYNAMODB_TABLE_NAME=trading-alerts
```

### Запусти:
```bash
python app.py
```

### Открой в браузере:
```
http://localhost:7860
```

---

## 🎉 Что ты увидишь в UI:

1. **Login Tab** - Вход для существующих пользователей
2. **Register Tab** - Регистрация новых пользователей
3. После успешного входа → **Main App**:
   - ✅ User ID автоматически заполняется
   - ✅ Можно создавать сигналы
   - ✅ Сессия сохраняется в DynamoDB

---

## 🔒 Security Features:

✅ **bcrypt** - Безопасное хеширование паролей (12 rounds, с солью)
✅ **JWT** - Стандартные токены аутентификации (HS256, 30 дней)
✅ **Rate Limiting** - Защита от brute force (5 попыток, 5 мин блокировка)
✅ **DynamoDB Sessions** - Сессии переживают рестарт сервера
✅ **TTL Auto-cleanup** - DynamoDB сама удаляет истекшие сессии

---

## ⚠️ Troubleshooting

### Ошибка: `ModuleNotFoundError`
**Решение:**
```bash
pip install PyJWT bcrypt boto3 pydantic
```

### Ошибка: `No module named 'gradio'`
**Решение:**
```bash
pip install gradio
```

### Ошибка: `Unable to locate credentials` (AWS)
**Решение:**
Настрой AWS credentials или используй демо-режим без DynamoDB:
```bash
python demo_auth.py
```

---

## 📚 Полная документация:

- `TESTING_GUIDE.md` - Подробный гайд по тестам
- `docs/AUTHENTICATION.md` - Как работает аутентификация
- `docs/PRODUCTION_ENHANCEMENTS.md` - bcrypt, rate limiting, cookies

---

## ✅ Checklist:

- [ ] Проверил версию Python (`python --version` - нужен 3.8+)
- [ ] Установил зависимости (`pip install PyJWT bcrypt boto3 pydantic gradio`)
- [ ] Переключился на правильную ветку (`git checkout claude/session-persistence-...`)
- [ ] Запустил `python test_syntax_only.py` → ✅ 8/8
- [ ] Запустил `python demo_auth.py` → ✅ Демонстрация работает
- [ ] Создал `.env` файл с `JWT_SECRET_KEY`
- [ ] Запустил `python app.py`
- [ ] Открыл `http://localhost:7860`
- [ ] Зарегистрировался
- [ ] Залогинился
- [ ] Создал сигнал

---

**🎯 Готово! Система production-ready!** 🚀

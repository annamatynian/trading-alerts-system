# JWT Authentication System with DynamoDB Session Persistence

Production-ready JWT authentication system для Trading Alerts с хранением сессий в DynamoDB.

## Созданные файлы

### 1. **src/storage/session_storage.py** (15 KB)
DynamoDB storage для JWT сессий с автоматическим TTL cleanup.

**Основные функции:**
- `save_session(session_id, user_id, token, metadata)` - Сохраняет сессию
- `get_session(session_id)` - Получает сессию с проверкой истечения
- `delete_session(session_id)` - Удаляет сессию (logout)
- `get_user_sessions(user_id)` - Все активные сессии пользователя
- `cleanup_expired_sessions()` - Очистка истекших сессий
- `extend_session(session_id, hours)` - Продление сессии

**Особенности:**
- ✅ Асинхронные операции (async/await)
- ✅ DynamoDB TTL для автоматического удаления
- ✅ Детальное логирование
- ✅ Обработка ошибок
- ✅ Переиспользует существующую таблицу `trading-signals`

### 2. **src/services/auth_service.py** (18 KB)
JWT authentication service с полным набором функций.

**Основные функции:**
- `register_user(username, password, metadata)` - Регистрация с bcrypt hashing
- `login(username, password, metadata)` - Вход и генерация JWT
- `validate_token(token)` - Валидация JWT + проверка в DynamoDB
- `logout(session_id)` - Выход и удаление сессии
- `refresh_token(session_id, hours)` - Обновление токена
- `get_user_sessions(username)` - Все сессии пользователя

**Безопасность:**
- ✅ **bcrypt** password hashing (fallback на SHA256)
- ✅ **Rate limiting**: 5 попыток, 5-минутная блокировка
- ✅ **JWT** с signature verification
- ✅ **Token tampering detection** через DynamoDB
- ✅ **Session validation** при каждом запросе

### 3. **test_unit_auth.py** (18 KB)
8 unit тестов - работают БЕЗ AWS credentials (используют mocking).

**Тесты:**
1. `test_password_hashing` - Проверка bcrypt/SHA256 хеширования
2. `test_jwt_generation` - Генерация JWT токенов
3. `test_jwt_validation` - Валидация токенов
4. `test_session_crud` - CRUD операции с сессиями
5. `test_full_auth_flow` - Полный поток: register → login → validate → logout
6. `test_rate_limiting` - Rate limiting защита
7. `test_token_tampering` - Обнаружение подделки токенов
8. `test_session_expiration` - Истечение сессий

**Запуск:**
```bash
pytest test_unit_auth.py -v
```

### 4. **test_production_features.py** (17 KB)
7 production тестов - тестируют продакшн функции.

**Тесты:**
1. `test_bcrypt_hashing` - bcrypt хеширование (если доступен)
2. `test_sha256_fallback` - SHA256 fallback
3. `test_rate_limiter_timing` - Точность rate limiter по времени
4. `test_multiple_user_sessions` - Множественные сессии
5. `test_token_refresh_flow` - Refresh token flow
6. `test_concurrent_login_attempts` - Параллельные запросы
7. `test_session_cleanup_integration` - Интеграция cleanup

**Запуск:**
```bash
pytest test_production_features.py -v
```

### 5. **demo_auth.py** (17 KB)
Интерактивное демо с цветным выводом - показывает все возможности.

**Демонстрирует:**
1. ✅ User Registration (bcrypt hashing)
2. ✅ Login (JWT generation, DynamoDB persistence)
3. ✅ Token Validation (signature + DynamoDB check)
4. ✅ Tampering Detection (безопасность)
5. ✅ Rate Limiting (brute-force защита)
6. ✅ Multiple Sessions (multi-device login)
7. ✅ Token Refresh (продление сессии)
8. ✅ Logout (удаление сессии)

**Запуск:**
```bash
python demo_auth.py
```

**Работает БЕЗ AWS credentials** - использует mock storage!

---

## Установка зависимостей

```bash
pip install -r requirements_auth.txt
```

Или вручную:
```bash
pip install PyJWT bcrypt boto3 pytest pytest-asyncio
```

---

## Быстрый старт

### 1. Регистрация и логин

```python
import asyncio
from src.services.auth_service import AuthService

async def main():
    # Инициализация (работает с DynamoDB)
    auth = AuthService(secret_key="your-secret-key-here")

    # Регистрация
    user = await auth.register_user(
        username="alice",
        password="SecurePass123!",
        metadata={"email": "alice@example.com"}
    )
    print(f"User registered: {user['user_id']}")

    # Логин
    result = await auth.login("alice", "SecurePass123!")
    token = result['access_token']
    session_id = result['session_id']
    print(f"Token: {token}")

    # Валидация
    payload = await auth.validate_token(token)
    print(f"Valid user: {payload['username']}")

    # Logout
    await auth.logout(session_id)

asyncio.run(main())
```

### 2. Protected endpoint пример

```python
async def protected_endpoint(request):
    # Получаем token из header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return {"error": "Unauthorized"}, 401

    token = auth_header.split(' ')[1]

    # Валидируем token
    try:
        payload = await auth.validate_token(token)
        user_id = payload['sub']
        username = payload['username']

        # Пользователь аутентифицирован
        return {"message": f"Hello, {username}!"}

    except ValueError as e:
        return {"error": str(e)}, 401
```

---

## Конфигурация для production

### Environment Variables

```bash
# JWT секретный ключ (ОБЯЗАТЕЛЬНО в production!)
export JWT_SECRET_KEY="your-super-secret-key-change-this-in-production"

# AWS для DynamoDB
export AWS_REGION="us-east-2"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

### DynamoDB Table

Использует существующую таблицу `trading-signals`:
- PK: `session#{session_id}`
- SK: `metadata`
- TTL field: `ttl` (Unix timestamp)

**Важно:** Включите TTL на поле `ttl` для автоматического удаления истекших сессий!

---

## Архитектура безопасности

### 🔐 Password Security
- **bcrypt** hashing с солью (industry standard)
- Fallback на SHA256 если bcrypt недоступен
- Минимум 8 символов для пароля

### 🎫 JWT Tokens
- Signed с secret key (HS256)
- Содержит: user_id, username, session_id, expiration
- Tamper-proof (signature verification)

### 💾 Session Persistence
- Каждый токен привязан к сессии в DynamoDB
- При валидации проверяется:
  1. ✅ JWT signature
  2. ✅ Token expiration
  3. ✅ Session exists в DynamoDB
  4. ✅ Token matches stored token (tampering detection)

### 🛡️ Rate Limiting
- 5 неудачных попыток входа
- 5-минутная блокировка
- Защита от brute-force атак

### 🚪 Logout
- Удаляет сессию из DynamoDB
- Токен становится невалидным
- Безопасный выход

---

## Тестирование

### Запуск всех тестов
```bash
# Unit tests (без AWS)
pytest test_unit_auth.py -v

# Production tests (без AWS)
pytest test_production_features.py -v

# Все тесты
pytest test_unit_auth.py test_production_features.py -v
```

### Интерактивное демо
```bash
python demo_auth.py
```

---

## Production Checklist

- [ ] Установить уникальный `JWT_SECRET_KEY` (не использовать default!)
- [ ] Настроить AWS credentials для DynamoDB
- [ ] Включить TTL на таблице DynamoDB (поле `ttl`)
- [ ] Установить bcrypt для secure password hashing
- [ ] Настроить логирование в production
- [ ] Добавить monitoring для rate limiting
- [ ] Рассмотреть Redis для distributed rate limiting (если multiple instances)
- [ ] Регулярно обновлять зависимости (PyJWT, bcrypt)
- [ ] Настроить HTTPS для API endpoints
- [ ] Добавить refresh token rotation (для повышенной безопасности)

---

## Статистика

- **5 файлов** создано
- **15 тестов** (8 unit + 7 production)
- **~85 KB** кода
- **100% async/await** во всех операциях
- **Детальные docstrings** для всех функций
- **Работает БЕЗ AWS** (для тестирования и демо)

---

## Интеграция с существующим кодом

Система полностью совместима с существующим `src/storage/dynamodb_storage.py`:
- Использует тот же `boto3` client
- Переиспользует таблицу `trading-signals`
- Следует тем же паттернам async/await
- Совместима с существующими моделями

---

## Поддержка

Все файлы содержат:
- ✅ Детальные docstrings
- ✅ Type hints
- ✅ Examples в docstrings
- ✅ Inline комментарии
- ✅ Error handling
- ✅ Logging

---

## Следующие шаги

1. **Настроить AWS DynamoDB**
   ```bash
   aws dynamodb update-time-to-live \
       --table-name trading-signals \
       --time-to-live-specification \
           "Enabled=true, AttributeName=ttl"
   ```

2. **Интегрировать в API**
   - Добавить middleware для проверки токенов
   - Защитить endpoints с `validate_token()`
   - Добавить login/logout endpoints

3. **Мониторинг**
   - Логировать failed login attempts
   - Отслеживать rate limiting events
   - Мониторить session cleanup

4. **Масштабирование**
   - Рассмотреть Redis для rate limiting
   - Добавить GSI по user_id для быстрых запросов
   - Оптимизировать DynamoDB indexes

---

**Система готова к production использованию!** 🚀

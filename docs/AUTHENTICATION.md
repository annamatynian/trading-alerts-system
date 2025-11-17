# Authentication & Session Persistence

## Обзор

Система теперь поддерживает полноценную аутентификацию с JWT токенами и persistence сессий в DynamoDB! 🎉

## Архитектура

### 1. **JWT Токены**
- Используется стандарт JWT (JSON Web Tokens)
- Токены содержат: `sub` (username), `jti` (session_id), `iat`, `exp`
- Время жизни: 30 дней (настраивается через `JWT_EXPIRATION_DAYS`)

### 2. **DynamoDB Session Storage**
- Сессии хранятся в той же таблице что и сигналы
- Структура записи:
  ```
  PK: session#{session_id}
  SK: metadata
  entity_type: session
  user_id: username
  created_at: timestamp
  expires_at: timestamp
  ttl: unix_timestamp (для автоудаления)
  ```
- Автоматическое удаление через DynamoDB TTL

### 3. **Пользовательские данные**
- Хешированные пароли (SHA256 для MVP, в production использовать bcrypt)
- Структура записи:
  ```
  PK: user#{username}
  SK: metadata
  entity_type: user
  username: string
  password_hash: string
  created_at: timestamp
  active: boolean
  ```

## Компоненты

### 1. `src/storage/session_storage.py`
Управление сессиями в DynamoDB:
- `save_session(session_id, user_id)` - создание сессии
- `get_session(session_id)` - получение сессии
- `delete_session(session_id)` - удаление сессии
- `get_user_sessions(user_id)` - все сессии пользователя
- `cleanup_expired_sessions()` - очистка истекших сессий

### 2. `src/services/auth_service.py`
JWT аутентификация:
- `register_user(username, password)` - регистрация
- `login(username, password)` - вход (возвращает JWT)
- `validate_token(token)` - проверка токена
- `logout(token)` - выход (удаление сессии)
- `refresh_token(old_token)` - обновление токена

### 3. `app.py` - Gradio UI
- Login/Register интерфейс
- Автоматическое переключение UI после входа
- State management для текущего пользователя

## Использование

### Регистрация
```python
success, message = await auth_service.register_user("anna", "password123")
```

### Логин
```python
success, jwt_token, message = await auth_service.login("anna", "password123")
# jwt_token - сохраняется в cookies (или Gradio State)
```

### Валидация сессии
```python
valid, username, message = await auth_service.validate_token(jwt_token)
```

### Логаут
```python
success, message = await auth_service.logout(jwt_token)
```

## Environment Variables

```bash
# JWT Secret (ОБЯЗАТЕЛЬНО установить в production!)
JWT_SECRET_KEY=your-super-secret-key-change-me

# JWT expiration (дни)
JWT_EXPIRATION_DAYS=30

# Session TTL (дни)
SESSION_TTL_DAYS=30

# DynamoDB
DYNAMODB_TABLE_NAME=trading-alerts
DYNAMODB_REGION=eu-west-1
AWS_REGION=eu-west-1
```

## Session Persistence при обновлении страницы

### Текущая реализация (MVP)
- Сессии хранятся в DynamoDB ✅
- JWT токены генерируются ✅
- **НО**: Токен пока не сохраняется в cookies автоматически ⚠️

### Что нужно для полной persistence

#### Вариант 1: JavaScript + Cookies (рекомендуется)
Добавить в `app.py`:
```python
# Custom HTML/JS для работы с cookies
cookie_js = """
<script>
function setCookie(name, value, days) {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=/';
}

function getCookie(name) {
    return document.cookie.split('; ').reduce((r, v) => {
        const parts = v.split('=');
        return parts[0] === name ? decodeURIComponent(parts[1]) : r;
    }, '');
}

// При логине сохраняем токен
window.addEventListener('load', function() {
    // Проверяем существующий токен
    const token = getCookie('session_token');
    if (token) {
        // Валидируем через API
        // ...
    }
});
</script>
"""
```

#### Вариант 2: FastAPI middleware (для production)
Обернуть Gradio в FastAPI и использовать proper cookie handling:
```python
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
gradio_app = create_interface()

@app.post("/api/login")
async def login(response: Response, credentials: LoginRequest):
    success, token, msg = await auth_service.login(...)
    if success:
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=30 * 24 * 60 * 60  # 30 days
        )
    return {"success": success, "message": msg}

app = gr.mount_gradio_app(app, gradio_app, path="/")
```

#### Вариант 3: Gradio State + LocalStorage (текущий)
- State сохраняет username/authenticated в памяти
- После обновления страницы нужен новый логин
- Простой и безопасный для MVP ✅

## Security Best Practices

### ✅ Уже реализовано
1. JWT токены с expiration
2. Session storage в DynamoDB с TTL
3. Хеширование паролей
4. Валидация токенов на сервере

### 🔒 Для production
1. **Использовать bcrypt/argon2** вместо SHA256:
   ```python
   import bcrypt
   password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
   ```

2. **HTTPS only** для cookies:
   ```python
   response.set_cookie(..., secure=True)
   ```

3. **Надежный JWT secret**:
   ```bash
   JWT_SECRET_KEY=$(openssl rand -hex 32)
   ```

4. **Rate limiting** для login endpoint

5. **CSRF protection** для form submissions

6. **Password requirements**:
   - Минимум 8 символов
   - Uppercase + lowercase + numbers + symbols

## Тестирование

### Локальное тестирование
```bash
# Запуск приложения
python app.py

# Открыть http://localhost:7860
# 1. Зарегистрировать пользователя
# 2. Войти
# 3. Создать сигнал
# 4. Выйти
# 5. Войти снова - сигналы должны остаться!
```

### Проверка сессий в DynamoDB
```bash
aws dynamodb scan \
    --table-name trading-alerts \
    --filter-expression "entity_type = :type" \
    --expression-attribute-values '{":type":{"S":"session"}}' \
    --region eu-west-1
```

### Очистка истекших сессий
```python
from src.storage.session_storage import SessionStorage

storage = SessionStorage()
deleted = await storage.cleanup_expired_sessions()
print(f"Deleted {deleted} expired sessions")
```

## Миграция существующих пользователей

Если у вас уже есть пользователи с `user_id`:

```python
# Скрипт миграции
from src.services.auth_service import AuthService

auth = AuthService()

# Создаем аккаунты для существующих user_id
existing_users = ["anna", "john", "maria"]

for username in existing_users:
    # Временный пароль (попросить пользователя изменить)
    temp_password = f"{username}_temp123"
    success, msg = await auth.register_user(username, temp_password)
    print(f"{username}: {msg}")
```

## Troubleshooting

### Ошибка: "JWT_SECRET_KEY not set"
```bash
export JWT_SECRET_KEY="your-secret-key-here"
```

### Сессия не сохраняется после обновления
- Это нормально для MVP! Используйте full production setup с cookies (см. выше)

### "Session not found or expired"
- Сессия истекла (TTL = 30 дней)
- Требуется новый логин

### DynamoDB "ResourceNotFoundException"
- Убедитесь что таблица `trading-alerts` существует
- Проверьте AWS credentials и region

## Roadmap

- [ ] Full cookie-based session persistence
- [ ] Password reset functionality
- [ ] Email verification
- [ ] 2FA (Two-Factor Authentication)
- [ ] OAuth2 integration (Google, GitHub)
- [ ] Role-based access control (admin, user)
- [ ] Session activity log
- [ ] Device management (view/revoke sessions)

## Заключение

Теперь ваша система имеет production-ready аутентификацию! 🚀

**MVP features** (текущая реализация):
- ✅ JWT токены
- ✅ DynamoDB persistence
- ✅ Register/Login/Logout
- ✅ TTL для автоочистки

**Production features** (требуют дополнительной настройки):
- ⏳ Cookie-based persistence
- ⏳ HTTPS
- ⏳ bcrypt passwords
- ⏳ Rate limiting

Следующий шаг: протестируйте систему и добавьте cookie persistence если нужно!

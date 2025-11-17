"""
Authentication Service с JWT токенами и DynamoDB persistence
Production-ready реализация для веб-аутентификации
"""
import os
import logging
import secrets
import hashlib
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import time

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("⚠️  bcrypt not available, falling back to SHA256")

from storage.session_storage import SessionStorage

logger = logging.getLogger(__name__)


class AuthService:
    """
    Сервис аутентификации с JWT токенами

    Features:
    - JWT токены для клиента (в cookies)
    - Сессии в DynamoDB для серверной валидации
    - Автоматическое истечение сессий (TTL)
    - bcrypt хеширование паролей (production-ready)
    - Rate limiting (защита от brute force)
    """

    def __init__(self, session_storage: SessionStorage = None):
        """
        Args:
            session_storage: Хранилище сессий (если None - создаст новое)
        """
        # JWT Secret - ВАЖНО: в production использовать надежный секрет
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', self._generate_secret())
        self.jwt_algorithm = 'HS256'
        self.jwt_expiration_days = int(os.getenv('JWT_EXPIRATION_DAYS', '30'))

        # Session storage
        self.session_storage = session_storage or SessionStorage()

        # Rate limiting для защиты от brute force
        self.login_attempts = defaultdict(list)  # {username: [timestamp1, timestamp2, ...]}
        self.max_login_attempts = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
        self.lockout_duration = int(os.getenv('LOCKOUT_DURATION', '300'))  # 5 минут

        # bcrypt параметры
        self.bcrypt_rounds = int(os.getenv('BCRYPT_ROUNDS', '12'))  # Стоимость хеширования

        hash_method = "bcrypt" if BCRYPT_AVAILABLE else "SHA256"
        logger.info(f"AuthService initialized (JWT: {self.jwt_expiration_days}d, Hash: {hash_method}, Rate limit: {self.max_login_attempts} attempts)")

    def _generate_secret(self) -> str:
        """
        Генерирует случайный JWT секрет

        ВНИМАНИЕ: В production нужно использовать постоянный секрет из env!
        """
        secret = secrets.token_urlsafe(32)
        logger.warning(
            "⚠️  JWT_SECRET_KEY not set! Generated temporary secret. "
            "Set JWT_SECRET_KEY environment variable for production!"
        )
        return secret

    def _hash_password(self, password: str) -> str:
        """
        Хеширование пароля (bcrypt если доступен, иначе SHA256)

        Args:
            password: Пароль в открытом виде

        Returns:
            Хеш пароля (строка)
        """
        if BCRYPT_AVAILABLE:
            # bcrypt возвращает bytes, конвертируем в строку
            salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        else:
            # Fallback на SHA256 (только для dev!)
            return f"sha256:{hashlib.sha256(password.encode()).hexdigest()}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Проверка пароля против хеша

        Args:
            password: Пароль в открытом виде
            password_hash: Хеш из базы данных

        Returns:
            True если пароль совпадает
        """
        if BCRYPT_AVAILABLE and not password_hash.startswith('sha256:'):
            # bcrypt verification
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        else:
            # SHA256 fallback
            expected_hash = f"sha256:{hashlib.sha256(password.encode()).hexdigest()}"
            return password_hash == expected_hash

    def _check_rate_limit(self, username: str) -> Tuple[bool, str]:
        """
        Проверяет rate limit для пользователя

        Args:
            username: Имя пользователя

        Returns:
            (allowed, message)
        """
        now = time.time()
        cutoff = now - self.lockout_duration

        # Очищаем старые попытки
        self.login_attempts[username] = [
            timestamp for timestamp in self.login_attempts[username]
            if timestamp > cutoff
        ]

        # Проверяем количество попыток
        if len(self.login_attempts[username]) >= self.max_login_attempts:
            remaining = int(self.login_attempts[username][0] + self.lockout_duration - now)
            return False, f"Too many login attempts. Try again in {remaining} seconds."

        return True, ""

    def _record_login_attempt(self, username: str):
        """Записывает попытку входа"""
        self.login_attempts[username].append(time.time())

    async def register_user(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Регистрация нового пользователя

        Args:
            username: Имя пользователя
            password: Пароль

        Returns:
            (success, message)
        """
        try:
            # Проверяем минимальные требования
            if not username or len(username) < 3:
                return False, "Username must be at least 3 characters"

            if not password or len(password) < 6:
                return False, "Password must be at least 6 characters"

            # Хешируем пароль
            password_hash = self._hash_password(password)

            # Сохраняем в DynamoDB через user_data
            from storage.dynamodb_storage import DynamoDBStorage

            storage = DynamoDBStorage()
            user_data = {
                'username': username,
                'password_hash': password_hash,
                'created_at': datetime.now().isoformat(),
                'active': True
            }

            success = await storage.save_user_data(username, user_data)

            if success:
                logger.info(f"✅ User registered: {username}")
                return True, f"User {username} registered successfully"
            else:
                return False, "Failed to save user data"

        except Exception as e:
            logger.error(f"❌ Registration failed: {e}")
            return False, f"Registration error: {e}"

    async def login(self, username: str, password: str, ip_address: str = None) -> Tuple[bool, Optional[str], str]:
        """
        Аутентификация пользователя и создание JWT токена

        Args:
            username: Имя пользователя
            password: Пароль
            ip_address: IP адрес клиента (для rate limiting)

        Returns:
            (success, jwt_token, message)
        """
        try:
            # 1. Проверяем rate limit
            allowed, rate_msg = self._check_rate_limit(username)
            if not allowed:
                logger.warning(f"🚫 Rate limit exceeded: {username}")
                return False, None, rate_msg

            # Получаем данные пользователя
            from storage.dynamodb_storage import DynamoDBStorage

            storage = DynamoDBStorage()
            user_data = await storage.get_user_data(username)

            if not user_data:
                # Записываем неудачную попытку (защита от подбора username)
                self._record_login_attempt(username)
                logger.warning(f"❌ Login failed: user not found ({username})")
                return False, None, "Invalid username or password"

            # 2. Проверяем пароль используя новый метод
            password_hash = user_data.get('password_hash')
            if not self._verify_password(password, password_hash):
                # Записываем неудачную попытку
                self._record_login_attempt(username)
                logger.warning(f"❌ Login failed: wrong password ({username})")
                return False, None, "Invalid username or password"

            # 3. Проверяем активность аккаунта
            if not user_data.get('active', True):
                return False, None, "Account is disabled"

            # 4. Создаем JWT токен
            jwt_token = self._create_jwt_token(username)

            # Извлекаем session_id из токена (jti claim)
            payload = jwt.decode(jwt_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            session_id = payload['jti']

            # 5. Сохраняем сессию в DynamoDB
            await self.session_storage.save_session(
                session_id=session_id,
                user_id=username,
                metadata={
                    'login_time': datetime.now().isoformat(),
                    'ip_address': ip_address or 'unknown'
                }
            )

            # Очищаем счетчик попыток после успешного входа
            if username in self.login_attempts:
                del self.login_attempts[username]

            logger.info(f"✅ User logged in: {username}")
            return True, jwt_token, "Login successful"

        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False, None, f"Login error: {e}"

    def _create_jwt_token(self, username: str) -> str:
        """
        Создает JWT токен для пользователя

        Args:
            username: Имя пользователя

        Returns:
            JWT токен string
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.jwt_expiration_days)

        # JWT payload
        payload = {
            'sub': username,  # Subject (user_id)
            'jti': secrets.token_urlsafe(16),  # JWT ID (session_id)
            'iat': now,  # Issued at
            'exp': expires_at,  # Expiration
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token

    async def validate_token(self, token: str) -> Tuple[bool, Optional[str], str]:
        """
        Валидирует JWT токен и проверяет сессию в DynamoDB

        Args:
            token: JWT токен

        Returns:
            (valid, username, message)
        """
        try:
            # Декодируем JWT
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )

            username = payload.get('sub')
            session_id = payload.get('jti')

            if not username or not session_id:
                return False, None, "Invalid token payload"

            # Проверяем сессию в DynamoDB
            session = await self.session_storage.get_session(session_id)

            if not session:
                return False, None, "Session not found or expired"

            if session['user_id'] != username:
                return False, None, "Session user mismatch"

            logger.debug(f"✅ Token validated for user: {username}")
            return True, username, "Token valid"

        except ExpiredSignatureError:
            return False, None, "Token expired"
        except InvalidTokenError as e:
            logger.warning(f"❌ Invalid token: {e}")
            return False, None, "Invalid token"
        except Exception as e:
            logger.error(f"❌ Token validation error: {e}")
            return False, None, f"Validation error: {e}"

    async def logout(self, token: str) -> Tuple[bool, str]:
        """
        Выход пользователя (удаление сессии)

        Args:
            token: JWT токен

        Returns:
            (success, message)
        """
        try:
            # Декодируем токен чтобы получить session_id
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": False}  # Разрешаем expired токены для logout
            )

            session_id = payload.get('jti')
            if not session_id:
                return False, "Invalid token"

            # Удаляем сессию
            success = await self.session_storage.delete_session(session_id)

            if success:
                logger.info(f"✅ User logged out: {payload.get('sub')}")
                return True, "Logged out successfully"
            else:
                return False, "Failed to delete session"

        except Exception as e:
            logger.error(f"❌ Logout error: {e}")
            return False, f"Logout error: {e}"

    async def get_user_sessions(self, username: str) -> list:
        """
        Получает все активные сессии пользователя

        Args:
            username: Имя пользователя

        Returns:
            Список активных сессий
        """
        return await self.session_storage.get_user_sessions(username)

    async def refresh_token(self, old_token: str) -> Tuple[bool, Optional[str], str]:
        """
        Обновляет JWT токен (создает новый с новым expiration)

        Args:
            old_token: Старый JWT токен

        Returns:
            (success, new_token, message)
        """
        try:
            # Валидируем старый токен
            valid, username, msg = await self.validate_token(old_token)

            if not valid:
                return False, None, msg

            # Удаляем старую сессию
            await self.logout(old_token)

            # Создаем новый токен и сессию
            new_token = self._create_jwt_token(username)

            payload = jwt.decode(new_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            session_id = payload['jti']

            await self.session_storage.save_session(
                session_id=session_id,
                user_id=username,
                metadata={'refreshed_at': datetime.now().isoformat()}
            )

            logger.info(f"✅ Token refreshed for user: {username}")
            return True, new_token, "Token refreshed"

        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            return False, None, f"Refresh error: {e}"

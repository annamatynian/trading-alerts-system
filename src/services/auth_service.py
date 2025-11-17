"""
JWT Authentication Service с DynamoDB Session Persistence
Production-ready с bcrypt, rate limiting, и detailed logging
"""
import os
import logging
import hashlib
import secrets
import uuid
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

# JWT
import jwt

# Password hashing (bcrypt с fallback на SHA256)
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.warning("⚠️  bcrypt not available, falling back to SHA256 (less secure)")

from storage.session_storage import SessionStorage

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter для защиты от brute-force атак

    Production: следует использовать Redis для distributed rate limiting
    """

    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 5):
        """
        Args:
            max_attempts: Максимум попыток до блокировки
            lockout_minutes: Время блокировки в минутах
        """
        self.max_attempts = max_attempts
        self.lockout_minutes = lockout_minutes
        self.attempts: Dict[str, list] = {}  # {username: [timestamp1, timestamp2, ...]}

    def check_rate_limit(self, username: str) -> Tuple[bool, Optional[str]]:
        """
        Проверяет rate limit для пользователя

        Returns:
            (allowed, error_message)
            - allowed: True если можно продолжать
            - error_message: Сообщение об ошибке если заблокирован
        """
        now = datetime.now()

        if username not in self.attempts:
            return True, None

        # Удаляем старые попытки (старше lockout_minutes)
        cutoff = now - timedelta(minutes=self.lockout_minutes)
        self.attempts[username] = [
            ts for ts in self.attempts[username]
            if ts > cutoff
        ]

        # Проверяем количество попыток
        if len(self.attempts[username]) >= self.max_attempts:
            remaining_time = self.lockout_minutes - (
                (now - self.attempts[username][0]).total_seconds() / 60
            )
            return False, f"Too many attempts. Try again in {int(remaining_time)} minutes"

        return True, None

    def record_attempt(self, username: str):
        """Записывает попытку входа"""
        if username not in self.attempts:
            self.attempts[username] = []
        self.attempts[username].append(datetime.now())

    def clear_attempts(self, username: str):
        """Очищает попытки после успешного входа"""
        if username in self.attempts:
            del self.attempts[username]


class AuthService:
    """
    JWT Authentication Service с DynamoDB persistence

    Features:
        ✅ User registration с bcrypt password hashing
        ✅ JWT token generation и validation
        ✅ Session persistence в DynamoDB
        ✅ Rate limiting (5 attempts, 5-minute lockout)
        ✅ Secure logout с session cleanup
        ✅ Token refresh
        ✅ Production-ready error handling

    Example:
        >>> auth = AuthService(secret_key="my-secret-key")
        >>>
        >>> # Register user
        >>> user = await auth.register_user("john", "secure_password_123")
        >>>
        >>> # Login
        >>> result = await auth.login("john", "secure_password_123")
        >>> token = result['access_token']
        >>> session_id = result['session_id']
        >>>
        >>> # Validate token
        >>> payload = await auth.validate_token(token)
        >>>
        >>> # Logout
        >>> await auth.logout(session_id)
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_hours: int = 24,
        session_storage: Optional[SessionStorage] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Инициализирует AuthService

        Args:
            secret_key: Секретный ключ для JWT (если None - генерирует случайный)
            algorithm: Алгоритм JWT (default: HS256)
            access_token_expire_hours: Время жизни токена в часах
            session_storage: SessionStorage instance (если None - создает новый)
            rate_limiter: RateLimiter instance (если None - создает новый)
        """
        # JWT configuration
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY') or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.access_token_expire_hours = access_token_expire_hours

        # Session storage
        self.session_storage = session_storage or SessionStorage(
            ttl_hours=access_token_expire_hours
        )

        # Rate limiter
        self.rate_limiter = rate_limiter or RateLimiter()

        # In-memory user storage (для demo - в production использовать DynamoDB)
        self.users: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"AuthService initialized (algorithm: {algorithm}, "
            f"token_ttl: {access_token_expire_hours}h, "
            f"bcrypt: {BCRYPT_AVAILABLE})"
        )

    def _hash_password(self, password: str) -> str:
        """
        Хеширует пароль с использованием bcrypt или SHA256

        Args:
            password: Пароль в plain text

        Returns:
            Хешированный пароль
        """
        if BCRYPT_AVAILABLE:
            # bcrypt (рекомендуется для production)
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        else:
            # SHA256 fallback (менее безопасно, но работает без bcrypt)
            salt = secrets.token_hex(16)
            hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
            return f"sha256${salt}${hashed}"

    def _verify_password(self, password: str, hashed: str) -> bool:
        """
        Проверяет пароль против хеша

        Args:
            password: Пароль в plain text
            hashed: Хешированный пароль

        Returns:
            True если пароль совпадает
        """
        if BCRYPT_AVAILABLE and not hashed.startswith('sha256$'):
            # bcrypt verification
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        else:
            # SHA256 verification
            parts = hashed.split('$')
            if len(parts) != 3 or parts[0] != 'sha256':
                return False
            salt = parts[1]
            stored_hash = parts[2]
            computed_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
            return computed_hash == stored_hash

    async def register_user(
        self,
        username: str,
        password: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Регистрирует нового пользователя

        Args:
            username: Имя пользователя (уникальное)
            password: Пароль (будет захеширован)
            metadata: Дополнительные данные (email, name и т.д.)

        Returns:
            Словарь с данными пользователя

        Raises:
            ValueError: Если пользователь уже существует или данные невалидны

        Example:
            >>> user = await auth.register_user(
            ...     username="john",
            ...     password="secure_password_123",
            ...     metadata={"email": "john@example.com", "name": "John Doe"}
            ... )
        """
        # Валидация
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        if username in self.users:
            raise ValueError(f"User '{username}' already exists")

        # Хешируем пароль
        password_hash = await asyncio.to_thread(self._hash_password, password)

        # Создаем пользователя
        user_id = str(uuid.uuid4())
        user = {
            'user_id': user_id,
            'username': username,
            'password_hash': password_hash,
            'created_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }

        self.users[username] = user

        logger.info(f"✅ User registered: {username} (ID: {user_id})")

        # Возвращаем без password_hash
        return {
            'user_id': user_id,
            'username': username,
            'created_at': user['created_at'],
            'metadata': user['metadata']
        }

    async def login(
        self,
        username: str,
        password: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Аутентифицирует пользователя и создает JWT сессию

        Args:
            username: Имя пользователя
            password: Пароль
            metadata: Метаданные сессии (IP, User-Agent, device и т.д.)

        Returns:
            Словарь с access_token, session_id, и user_info

        Raises:
            ValueError: Если credentials неверные или rate limit превышен

        Example:
            >>> result = await auth.login(
            ...     username="john",
            ...     password="secure_password_123",
            ...     metadata={"ip": "192.168.1.1", "user_agent": "Mozilla/5.0"}
            ... )
            >>> print(f"Token: {result['access_token']}")
            >>> print(f"Session: {result['session_id']}")
        """
        # Проверяем rate limit
        allowed, error_msg = self.rate_limiter.check_rate_limit(username)
        if not allowed:
            logger.warning(f"🚫 Rate limit exceeded for user: {username}")
            raise ValueError(error_msg)

        # Проверяем существует ли пользователь
        if username not in self.users:
            self.rate_limiter.record_attempt(username)
            raise ValueError("Invalid username or password")

        user = self.users[username]

        # Проверяем пароль
        password_valid = await asyncio.to_thread(
            self._verify_password,
            password,
            user['password_hash']
        )

        if not password_valid:
            self.rate_limiter.record_attempt(username)
            logger.warning(f"❌ Failed login attempt for user: {username}")
            raise ValueError("Invalid username or password")

        # Успешная аутентификация - очищаем rate limit
        self.rate_limiter.clear_attempts(username)

        # Генерируем JWT token
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=self.access_token_expire_hours)

        payload = {
            'sub': user['user_id'],  # subject (user_id)
            'username': username,
            'session_id': session_id,
            'exp': expires_at,  # expiration time
            'iat': datetime.now(),  # issued at
        }

        access_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Сохраняем сессию в DynamoDB
        await self.session_storage.save_session(
            session_id=session_id,
            user_id=user['user_id'],
            token=access_token,
            metadata=metadata
        )

        logger.info(f"✅ User logged in: {username} (session: {session_id[:8]}...)")

        return {
            'access_token': access_token,
            'session_id': session_id,
            'token_type': 'Bearer',
            'expires_at': expires_at.isoformat(),
            'user': {
                'user_id': user['user_id'],
                'username': username,
                'metadata': user['metadata']
            }
        }

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Валидирует JWT token и проверяет сессию в DynamoDB

        Args:
            token: JWT access token

        Returns:
            Payload токена если валиден

        Raises:
            ValueError: Если токен невалиден или сессия не найдена

        Example:
            >>> payload = await auth.validate_token(token)
            >>> print(f"User ID: {payload['sub']}")
            >>> print(f"Username: {payload['username']}")
        """
        try:
            # Декодируем JWT token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            session_id = payload.get('session_id')
            if not session_id:
                raise ValueError("Token missing session_id")

            # Проверяем существует ли сессия в DynamoDB
            session = await self.session_storage.get_session(session_id)
            if not session:
                raise ValueError("Session not found or expired")

            # Проверяем что токен совпадает
            if session['token'] != token:
                logger.warning(f"⚠️  Token mismatch for session {session_id[:8]}...")
                raise ValueError("Token mismatch - possible tampering")

            logger.debug(f"✅ Token validated for user: {payload['username']}")
            return payload

        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    async def logout(self, session_id: str) -> bool:
        """
        Выход пользователя - удаляет сессию из DynamoDB

        Args:
            session_id: ID сессии для удаления

        Returns:
            True если успешно

        Example:
            >>> await auth.logout(session_id)
        """
        success = await self.session_storage.delete_session(session_id)
        if success:
            logger.info(f"✅ User logged out (session: {session_id[:8]}...)")
        return success

    async def refresh_token(
        self,
        session_id: str,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Обновляет токен - продлевает сессию

        Args:
            session_id: ID сессии
            hours: На сколько часов продлить (если None - использует default TTL)

        Returns:
            Новый токен и время истечения

        Raises:
            ValueError: Если сессия не найдена

        Example:
            >>> # Продлить текущую сессию на 24 часа
            >>> result = await auth.refresh_token(session_id)
            >>> new_token = result['access_token']
        """
        # Получаем текущую сессию
        session = await self.session_storage.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        # Продлеваем сессию
        hours = hours or self.access_token_expire_hours
        success = await self.session_storage.extend_session(session_id, hours=hours)
        if not success:
            raise ValueError("Failed to extend session")

        # Генерируем новый JWT token
        user_id = session['user_id']
        expires_at = datetime.now() + timedelta(hours=hours)

        # Находим username по user_id
        username = None
        for uname, user in self.users.items():
            if user['user_id'] == user_id:
                username = uname
                break

        if not username:
            raise ValueError("User not found")

        payload = {
            'sub': user_id,
            'username': username,
            'session_id': session_id,
            'exp': expires_at,
            'iat': datetime.now(),
        }

        new_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Обновляем токен в сессии
        metadata = session.get('metadata')
        await self.session_storage.save_session(
            session_id=session_id,
            user_id=user_id,
            token=new_token,
            metadata=metadata
        )

        logger.info(f"🔄 Token refreshed for session {session_id[:8]}...")

        return {
            'access_token': new_token,
            'session_id': session_id,
            'token_type': 'Bearer',
            'expires_at': expires_at.isoformat()
        }

    async def get_user_sessions(self, username: str) -> list:
        """
        Получает все активные сессии пользователя

        Args:
            username: Имя пользователя

        Returns:
            Список активных сессий
        """
        if username not in self.users:
            return []

        user_id = self.users[username]['user_id']
        sessions = await self.session_storage.get_user_sessions(user_id)
        return sessions

"""
Authentication Service с JWT токенами
"""
import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
import boto3
from botocore.exceptions import ClientError

# Импорт моделей
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from storage.session_storage import Session, SessionStorage

logger = logging.getLogger(__name__)


class User:
    """Модель пользователя"""

    def __init__(
        self,
        username: str,
        password_hash: str,
        created_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
        is_active: bool = True,
        pushover_key: Optional[str] = None
    ):
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        self.is_active = is_active
        self.pushover_key = pushover_key

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для DynamoDB"""
        return {
            'username': self.username,
            'password_hash': self.password_hash,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else '',
            'is_active': self.is_active,
            'pushover_key': self.pushover_key or ''
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Создание из словаря DynamoDB"""
        return cls(
            username=data['username'],
            password_hash=data['password_hash'],
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') else None,
            is_active=data.get('is_active', True),
            pushover_key=data.get('pushover_key')
        )


class AuthService:
    """Сервис аутентификации с JWT"""

    def __init__(
        self,
        session_storage: SessionStorage,
        secret_key: str,
        user_storage=None,
        token_expiry_hours: int = 24
    ):
        self.session_storage = session_storage
        self.secret_key = secret_key
        self.user_storage = user_storage
        self.token_expiry_hours = token_expiry_hours
        self.users: Dict[str, User] = {}  # In-memory cache
        logger.info("✅ AuthService initialized")

    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширование пароля с солью"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return f"{salt}${pwd_hash.hex()}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Проверка пароля"""
        try:
            salt, pwd_hash = password_hash.split('$')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return new_hash.hex() == pwd_hash
        except Exception as e:
            logger.error(f"❌ Password verification error: {e}")
            return False

    async def load_users_from_storage(self) -> None:
        """Загрузка пользователей из DynamoDB в память"""
        if not self.user_storage:
            logger.warning("⚠️ User storage not configured")
            return

        try:
            table = self.user_storage.table
            response = table.scan(
                FilterExpression='#type = :type',
                ExpressionAttributeNames={'#type': 'Type'},
                ExpressionAttributeValues={':type': 'User'}
            )

            for item in response.get('Items', []):
                user = User.from_dict(item)
                self.users[user.username] = user

            logger.info(f"✅ Loaded {len(self.users)} users from DynamoDB")

        except Exception as e:
            logger.error(f"❌ Failed to load users: {e}")

    async def register_user(self, username: str, password: str) -> Optional[User]:
        """Регистрация нового пользователя"""
        try:
            # Проверка существует ли пользователь
            if username in self.users:
                logger.warning(f"⚠️ User already exists: {username}")
                return None

            # Создаем пользователя
            password_hash = self.hash_password(password)
            user = User(username=username, password_hash=password_hash)

            # Сохраняем в DynamoDB
            if self.user_storage:
                item = {
                    'PK': f'USER#{username}',
                    'SK': f'USER#{username}',
                    'Type': 'User',
                    **user.to_dict()
                }
                self.user_storage.table.put_item(Item=item)

            # Добавляем в память
            self.users[username] = user

            logger.info(f"✅ User registered: {username}")
            return user

        except Exception as e:
            logger.error(f"❌ Registration error: {e}")
            return None

    async def login(self, username: str, password: str) -> Dict[str, str]:
        """Логин пользователя и создание JWT токена"""
        try:
            # Проверяем существует ли пользователь
            user = self.users.get(username)
            if not user:
                raise ValueError("Invalid username or password")

            # Проверяем пароль
            if not self.verify_password(password, user.password_hash):
                raise ValueError("Invalid username or password")

            # Проверяем активен ли пользователь
            if not user.is_active:
                raise ValueError("User account is disabled")

            # Создаем сессию
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)

            session = Session(
                session_id=session_id,
                username=username,
                created_at=datetime.utcnow(),
                expires_at=expires_at
            )

            await self.session_storage.save_session(session)

            # Создаем JWT токен
            token_payload = {
                'session_id': session_id,
                'username': username,
                'exp': expires_at,
                'iat': datetime.utcnow()
            }

            access_token = jwt.encode(token_payload, self.secret_key, algorithm='HS256')

            # Обновляем last_login
            user.last_login = datetime.utcnow()
            if self.user_storage:
                item = {
                    'PK': f'USER#{username}',
                    'SK': f'USER#{username}',
                    'Type': 'User',
                    **user.to_dict()
                }
                self.user_storage.table.put_item(Item=item)

            logger.info(f"✅ User logged in: {username}")

            return {
                'access_token': access_token,
                'session_id': session_id,
                'expires_at': expires_at.isoformat()
            }

        except ValueError as e:
            # Пробрасываем ValueError дальше (для обработки в UI)
            raise e
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            raise ValueError(f"Login failed: {str(e)}")

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Валидация JWT токена"""
        try:
            # Декодируем токен
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])

            session_id = payload.get('session_id')
            username = payload.get('username')

            if not session_id or not username:
                raise ValueError("Invalid token payload")

            # Проверяем сессию в DynamoDB
            session = await self.session_storage.get_session(session_id)
            if not session:
                raise ValueError("Session not found or expired")

            # Проверяем пользователя
            user = self.users.get(username)
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")

            return payload

        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Token validation error: {e}")
            raise ValueError(f"Token validation failed: {str(e)}")

    async def logout(self, token: str) -> bool:
        """Логаут - удаление сессии"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            session_id = payload.get('session_id')

            if session_id:
                await self.session_storage.delete_session(session_id)
                logger.info(f"✅ User logged out (session: {session_id[:8]}...)")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Logout error: {e}")
            return False

    async def update_pushover_key(self, username: str, pushover_key: str) -> bool:
        """Обновление Pushover ключа пользователя"""
        try:
            user = self.users.get(username)
            if not user:
                logger.error(f"❌ User {username} not found")
                return False

            # Обновляем pushover_key
            user.pushover_key = pushover_key

            # Сохраняем в DynamoDB
            await self._save_user_to_dynamodb(user)

            logger.info(f"✅ Pushover key updated for user: {username}")
            return True

        except Exception as e:
            logger.error(f"❌ Error updating pushover key for {username}: {e}")
            return False

    def get_user(self, username: str) -> Optional[User]:
        """Получение пользователя по username"""
        return self.users.get(username)

    def get_pushover_key(self, username: str) -> Optional[str]:
        """Получение Pushover ключа пользователя"""
        user = self.users.get(username)
        return user.pushover_key if user else None

    def list_users(self) -> List[User]:
        """Список всех пользователей"""
        return list(self.users.values())

"""
DynamoDB Session Storage для JWT Authentication
Production-ready реализация с TTL auto-cleanup
"""
import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SessionStorage:
    """
    DynamoDB storage для JWT сессий с автоматическим TTL cleanup

    Таблица: trading-signals (переиспользуем существующую)
    Структура сессий:
        PK (hash): session#{session_id}
        SK (range): metadata
        Attributes:
            - session_id: UUID сессии
            - user_id: ID пользователя
            - token: JWT token
            - created_at: Timestamp создания
            - expires_at: Timestamp истечения
            - ttl: Unix timestamp для DynamoDB TTL (auto-cleanup)
            - metadata: Дополнительные данные (IP, User-Agent и т.д.)

    Features:
        - Автоматический cleanup через DynamoDB TTL
        - Async operations
        - Error handling
        - Detailed logging
    """

    def __init__(self, table_name: str = "trading-signals", region: str = None, ttl_hours: int = 24):
        """
        Инициализирует SessionStorage

        Args:
            table_name: Имя DynamoDB таблицы
            region: AWS регион (если None - читает из AWS_REGION)
            ttl_hours: Время жизни сессии в часах (default: 24)
        """
        self.table_name = table_name
        self.region = region or os.getenv('AWS_REGION', 'us-east-2')
        self.ttl_hours = ttl_hours

        # Инициализируем DynamoDB client
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.table = self.dynamodb.Table(table_name)

        logger.info(f"SessionStorage initialized: {table_name} in {self.region} (TTL: {ttl_hours}h)")

    async def save_session(
        self,
        session_id: str,
        user_id: str,
        token: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Сохраняет новую сессию в DynamoDB с TTL

        Args:
            session_id: Уникальный ID сессии (UUID)
            user_id: ID пользователя
            token: JWT access token
            metadata: Дополнительные данные (IP, User-Agent, device_info и т.д.)

        Returns:
            True если успешно сохранено, False при ошибке

        Example:
            >>> storage = SessionStorage()
            >>> success = await storage.save_session(
            ...     session_id="550e8400-e29b-41d4-a716-446655440000",
            ...     user_id="user123",
            ...     token="eyJhbGciOiJIUzI1NiIs...",
            ...     metadata={"ip": "192.168.1.1", "user_agent": "Mozilla/5.0"}
            ... )
        """
        try:
            now = datetime.now()
            expires_at = now + timedelta(hours=self.ttl_hours)

            # TTL для DynamoDB (Unix timestamp)
            # DynamoDB автоматически удалит запись после этого времени
            ttl_timestamp = int(expires_at.timestamp())

            item = {
                'PK': f"session#{session_id}",
                'SK': 'metadata',
                'entity_type': 'session',
                'session_id': session_id,
                'user_id': user_id,
                'token': token,
                'created_at': now.isoformat(),
                'expires_at': expires_at.isoformat(),
                'ttl': ttl_timestamp,  # DynamoDB TTL field
            }

            # Добавляем metadata если есть
            if metadata:
                # Конвертируем все числа в Decimal для DynamoDB
                item['metadata'] = json.dumps(metadata)

            # Асинхронно сохраняем в DynamoDB
            await asyncio.to_thread(self.table.put_item, Item=item)

            logger.info(f"✅ Session saved: {session_id[:8]}... for user {user_id} (expires: {expires_at})")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to save session {session_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error saving session: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает сессию по ID с проверкой истечения

        Args:
            session_id: ID сессии

        Returns:
            Словарь с данными сессии или None если не найдена/истекла

        Example:
            >>> session = await storage.get_session("550e8400-e29b-41d4-a716-446655440000")
            >>> if session:
            ...     print(f"User: {session['user_id']}, Token: {session['token']}")
        """
        try:
            # Асинхронно получаем из DynamoDB
            response = await asyncio.to_thread(
                self.table.get_item,
                Key={
                    'PK': f"session#{session_id}",
                    'SK': 'metadata'
                }
            )

            item = response.get('Item')
            if not item:
                logger.debug(f"Session {session_id[:8]}... not found")
                return None

            # Проверяем истечение сессии
            expires_at = datetime.fromisoformat(item['expires_at'])
            if datetime.now() > expires_at:
                logger.info(f"⏰ Session {session_id[:8]}... expired (expired at: {expires_at})")
                # Удаляем истекшую сессию
                await self.delete_session(session_id)
                return None

            # Конвертируем обратно metadata
            session_data = {
                'session_id': item['session_id'],
                'user_id': item['user_id'],
                'token': item['token'],
                'created_at': item['created_at'],
                'expires_at': item['expires_at'],
            }

            if 'metadata' in item:
                session_data['metadata'] = json.loads(item['metadata'])

            logger.debug(f"✅ Session retrieved: {session_id[:8]}... (user: {item['user_id']})")
            return session_data

        except ClientError as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting session: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Удаляет сессию из DynamoDB (logout)

        Args:
            session_id: ID сессии для удаления

        Returns:
            True если успешно удалено

        Example:
            >>> await storage.delete_session("550e8400-e29b-41d4-a716-446655440000")
        """
        try:
            # Асинхронно удаляем из DynamoDB
            await asyncio.to_thread(
                self.table.delete_item,
                Key={
                    'PK': f"session#{session_id}",
                    'SK': 'metadata'
                }
            )
            logger.info(f"🗑️  Session deleted: {session_id[:8]}...")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to delete session {session_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting session: {e}")
            return False

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает все активные сессии пользователя

        Полезно для:
        - Просмотра всех устройств с активными сессиями
        - Force logout со всех устройств
        - Аудит безопасности

        Args:
            user_id: ID пользователя

        Returns:
            Список активных сессий пользователя

        Example:
            >>> sessions = await storage.get_user_sessions("user123")
            >>> print(f"Active sessions: {len(sessions)}")
            >>> for session in sessions:
            ...     print(f"  - {session['session_id']}: {session['metadata'].get('device')}")
        """
        try:
            # Используем Scan с фильтром (для production нужен GSI по user_id)
            response = await asyncio.to_thread(
                self.table.scan,
                FilterExpression='entity_type = :type AND user_id = :uid',
                ExpressionAttributeValues={
                    ':type': 'session',
                    ':uid': user_id
                }
            )

            items = response.get('Items', [])
            sessions = []

            now = datetime.now()

            for item in items:
                # Проверяем истечение
                expires_at = datetime.fromisoformat(item['expires_at'])
                if now <= expires_at:
                    session_data = {
                        'session_id': item['session_id'],
                        'user_id': item['user_id'],
                        'created_at': item['created_at'],
                        'expires_at': item['expires_at'],
                    }
                    if 'metadata' in item:
                        session_data['metadata'] = json.loads(item['metadata'])
                    sessions.append(session_data)

            logger.info(f"📋 Found {len(sessions)} active sessions for user {user_id}")
            return sessions

        except ClientError as e:
            logger.error(f"❌ Failed to get user sessions for {user_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error getting user sessions: {e}")
            return []

    async def cleanup_expired_sessions(self) -> int:
        """
        Очищает истекшие сессии (backup для DynamoDB TTL)

        NOTE: DynamoDB TTL автоматически удаляет истекшие записи,
        но это происходит с задержкой до 48 часов.
        Этот метод позволяет принудительно очистить истекшие сессии.

        Returns:
            Количество удаленных сессий

        Example:
            >>> # Запускать периодически (например, раз в час)
            >>> deleted = await storage.cleanup_expired_sessions()
            >>> print(f"Cleaned up {deleted} expired sessions")
        """
        try:
            # Сканируем все сессии
            response = await asyncio.to_thread(
                self.table.scan,
                FilterExpression='entity_type = :type',
                ExpressionAttributeValues={':type': 'session'}
            )

            items = response.get('Items', [])
            now = datetime.now()
            deleted_count = 0

            for item in items:
                expires_at = datetime.fromisoformat(item['expires_at'])
                if now > expires_at:
                    # Сессия истекла - удаляем
                    success = await self.delete_session(item['session_id'])
                    if success:
                        deleted_count += 1

            if deleted_count > 0:
                logger.info(f"🧹 Cleanup: deleted {deleted_count} expired sessions")
            else:
                logger.debug("🧹 Cleanup: no expired sessions found")

            return deleted_count

        except ClientError as e:
            logger.error(f"❌ Failed to cleanup expired sessions: {e}")
            return 0
        except Exception as e:
            logger.error(f"❌ Unexpected error during cleanup: {e}")
            return 0

    async def extend_session(self, session_id: str, hours: Optional[int] = None) -> bool:
        """
        Продлевает сессию на указанное количество часов

        Полезно для "remember me" функционала или refresh token flow

        Args:
            session_id: ID сессии
            hours: На сколько часов продлить (если None - использует self.ttl_hours)

        Returns:
            True если успешно продлено

        Example:
            >>> # Продлить сессию на 7 дней
            >>> await storage.extend_session(session_id, hours=24*7)
        """
        try:
            # Получаем текущую сессию
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Cannot extend session {session_id}: not found")
                return False

            # Новое время истечения
            hours = hours or self.ttl_hours
            new_expires_at = datetime.now() + timedelta(hours=hours)
            new_ttl = int(new_expires_at.timestamp())

            # Обновляем expires_at и ttl
            await asyncio.to_thread(
                self.table.update_item,
                Key={
                    'PK': f"session#{session_id}",
                    'SK': 'metadata'
                },
                UpdateExpression='SET expires_at = :expires, #ttl = :ttl',
                ExpressionAttributeNames={'#ttl': 'ttl'},  # ttl - reserved word
                ExpressionAttributeValues={
                    ':expires': new_expires_at.isoformat(),
                    ':ttl': new_ttl
                }
            )

            logger.info(f"⏰ Session extended: {session_id[:8]}... (new expiry: {new_expires_at})")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to extend session {session_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error extending session: {e}")
            return False

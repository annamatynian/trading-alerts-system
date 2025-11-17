"""
Session Storage для DynamoDB
Хранит активные сессии пользователей с TTL для автоматического удаления
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SessionStorage:
    """
    Хранилище сессий в DynamoDB

    Структура записи:
        PK: session#{session_id}
        SK: metadata
        entity_type: session
        user_id: ID пользователя
        created_at: Время создания
        expires_at: Время истечения (для TTL)
        ttl: Unix timestamp для автоматического удаления DynamoDB
    """

    def __init__(self, table_name: str = "trading-signals", region: str = None):
        """
        Args:
            table_name: Имя DynamoDB таблицы (переиспользуем основную таблицу)
            region: AWS регион
        """
        self.table_name = table_name
        self.region = region or os.getenv('AWS_REGION', 'eu-west-1')

        # Инициализация DynamoDB
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.table = self.dynamodb.Table(table_name)

        # Настройки TTL
        self.session_ttl_days = int(os.getenv('SESSION_TTL_DAYS', '30'))

        logger.info(f"SessionStorage initialized: {table_name} (TTL: {self.session_ttl_days} days)")

    async def save_session(self, session_id: str, user_id: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Сохраняет сессию в DynamoDB

        Args:
            session_id: Уникальный ID сессии (обычно JWT token ID)
            user_id: ID пользователя
            metadata: Дополнительные данные сессии (опционально)

        Returns:
            True если успешно
        """
        try:
            now = datetime.now()
            expires_at = now + timedelta(days=self.session_ttl_days)

            item = {
                'PK': f"session#{session_id}",
                'SK': 'metadata',
                'entity_type': 'session',
                'session_id': session_id,
                'user_id': user_id,
                'created_at': now.isoformat(),
                'expires_at': expires_at.isoformat(),
                'ttl': int(expires_at.timestamp()),  # Unix timestamp для DynamoDB TTL
            }

            # Добавляем metadata если есть
            if metadata:
                item['metadata'] = metadata

            await asyncio.to_thread(self.table.put_item, Item=item)
            logger.debug(f"✅ Session saved: {session_id[:8]}... for user {user_id}")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to save session: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные сессии по ID

        Args:
            session_id: ID сессии

        Returns:
            Словарь с данными сессии или None если не найдена
        """
        try:
            response = await asyncio.to_thread(
                self.table.get_item,
                Key={
                    'PK': f"session#{session_id}",
                    'SK': 'metadata'
                }
            )

            item = response.get('Item')
            if not item:
                logger.debug(f"Session not found: {session_id[:8]}...")
                return None

            # Проверяем не истекла ли сессия
            expires_at = datetime.fromisoformat(item['expires_at'])
            if datetime.now() > expires_at:
                logger.debug(f"Session expired: {session_id[:8]}...")
                await self.delete_session(session_id)
                return None

            # Возвращаем данные
            return {
                'session_id': item['session_id'],
                'user_id': item['user_id'],
                'created_at': item['created_at'],
                'expires_at': item['expires_at'],
                'metadata': item.get('metadata', {})
            }

        except ClientError as e:
            logger.error(f"❌ Failed to get session: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Удаляет сессию

        Args:
            session_id: ID сессии

        Returns:
            True если успешно
        """
        try:
            await asyncio.to_thread(
                self.table.delete_item,
                Key={
                    'PK': f"session#{session_id}",
                    'SK': 'metadata'
                }
            )
            logger.debug(f"Session deleted: {session_id[:8]}...")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to delete session: {e}")
            return False

    async def get_user_sessions(self, user_id: str) -> list:
        """
        Получает все активные сессии пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Список сессий
        """
        try:
            # Используем Scan с фильтром (можно оптимизировать через GSI)
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

            for item in items:
                # Проверяем валидность
                expires_at = datetime.fromisoformat(item['expires_at'])
                if datetime.now() <= expires_at:
                    sessions.append({
                        'session_id': item['session_id'],
                        'user_id': item['user_id'],
                        'created_at': item['created_at'],
                        'expires_at': item['expires_at']
                    })

            logger.debug(f"Found {len(sessions)} active sessions for user {user_id}")
            return sessions

        except ClientError as e:
            logger.error(f"❌ Failed to get user sessions: {e}")
            return []

    async def cleanup_expired_sessions(self) -> int:
        """
        Очищает истекшие сессии вручную (backup для TTL)

        Returns:
            Количество удаленных сессий
        """
        try:
            # Сканируем все сессии
            response = await asyncio.to_thread(
                self.table.scan,
                FilterExpression='entity_type = :type',
                ExpressionAttributeValues={':type': 'session'}
            )

            items = response.get('Items', [])
            deleted_count = 0
            now = datetime.now()

            for item in items:
                expires_at = datetime.fromisoformat(item['expires_at'])
                if now > expires_at:
                    await self.delete_session(item['session_id'])
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"🧹 Cleaned up {deleted_count} expired sessions")

            return deleted_count

        except ClientError as e:
            logger.error(f"❌ Failed to cleanup sessions: {e}")
            return 0

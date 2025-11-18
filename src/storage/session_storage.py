"""
Session Storage для JWT токенов в DynamoDB
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class Session:
    """Модель сессии пользователя"""

    def __init__(
        self,
        session_id: str,
        username: str,
        created_at: datetime,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        self.session_id = session_id
        self.username = username
        self.created_at = created_at
        self.expires_at = expires_at
        self.ip_address = ip_address
        self.user_agent = user_agent

    def is_expired(self) -> bool:
        """Проверка истёк ли срок сессии"""
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для DynamoDB"""
        return {
            'session_id': self.session_id,
            'username': self.username,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'ip_address': self.ip_address or '',
            'user_agent': self.user_agent or ''
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Создание из словаря DynamoDB"""
        return cls(
            session_id=data['session_id'],
            username=data['username'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent')
        )


class SessionStorage:
    """Хранилище сессий в DynamoDB"""

    def __init__(self, table_name: str = 'trading-alerts', region: str = 'eu-west-1'):
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        logger.info(f"SessionStorage initialized: {table_name} in {region}")

    async def save_session(self, session: Session) -> bool:
        """Сохранение сессии в DynamoDB"""
        try:
            item = {
                'PK': f'SESSION#{session.session_id}',
                'SK': f'SESSION#{session.session_id}',
                'Type': 'Session',
                **session.to_dict()
            }

            self.table.put_item(Item=item)
            logger.info(f"✅ Session saved: {session.session_id[:8]}... for user {session.username}")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to save session: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Получение сессии из DynamoDB"""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'SESSION#{session_id}',
                    'SK': f'SESSION#{session_id}'
                }
            )

            if 'Item' not in response:
                return None

            session = Session.from_dict(response['Item'])

            # Проверяем не истекла ли сессия
            if session.is_expired():
                logger.warning(f"⚠️ Session expired: {session_id[:8]}...")
                await self.delete_session(session_id)
                return None

            return session

        except ClientError as e:
            logger.error(f"❌ Failed to get session: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Удаление сессии из DynamoDB"""
        try:
            self.table.delete_item(
                Key={
                    'PK': f'SESSION#{session_id}',
                    'SK': f'SESSION#{session_id}'
                }
            )
            logger.info(f"✅ Session deleted: {session_id[:8]}...")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to delete session: {e}")
            return False

    async def delete_user_sessions(self, username: str) -> int:
        """Удаление всех сессий пользователя"""
        try:
            # Query all sessions for user
            response = self.table.scan(
                FilterExpression='#type = :type AND username = :username',
                ExpressionAttributeNames={'#type': 'Type'},
                ExpressionAttributeValues={':type': 'Session', ':username': username}
            )

            count = 0
            for item in response.get('Items', []):
                await self.delete_session(item['session_id'])
                count += 1

            logger.info(f"✅ Deleted {count} sessions for user {username}")
            return count

        except ClientError as e:
            logger.error(f"❌ Failed to delete user sessions: {e}")
            return 0

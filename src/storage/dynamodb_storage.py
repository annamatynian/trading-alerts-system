"""
DynamoDB Storage для Trading Signals
Production-ready реализация с error handling
"""
import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from models.signal import SignalTarget
from storage.base import StorageBase

logger = logging.getLogger(__name__)


class DynamoDBStorage(StorageBase):
    """
    DynamoDB storage для сигналов и пользовательских данных
    
    Таблица: trading-signals
    Структура:
        PK (hash): signal_id или user#{user_id}
        SK (range): metadata (для гибкости)
        Attributes: signal data / user data
    """
    
    def __init__(self, table_name: str = "trading-signals", region: str = None):
        """
        Args:
            table_name: Имя DynamoDB таблицы
            region: AWS регион (если None - читает из AWS_REGION)
        """
        self.table_name = table_name
        # Читаем регион из environment или используем переданный
        self.region = region or os.getenv('AWS_REGION', 'us-east-2')
        
        # Инициализируем DynamoDB client
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.table = self.dynamodb.Table(table_name)
        
        logger.info(f"DynamoDB storage initialized: {table_name} in {self.region}")
    
    def _signal_to_item(self, signal: SignalTarget) -> Dict[str, Any]:
        """
        Конвертирует SignalTarget в DynamoDB item
        
        DynamoDB не поддерживает float, используем Decimal
        """
        item = {
            'PK': f"signal#{signal.id or signal.name}",
            'SK': 'metadata',
            'entity_type': 'signal',
            'signal_id': signal.id or signal.name,
            'name': signal.name,
            'exchange': signal.exchange.value,
            'symbol': signal.symbol,
            'condition': signal.condition.value,
            'target_price': Decimal(str(signal.target_price)),  # float -> Decimal
            'active': signal.active,
            'triggered_count': signal.triggered_count,
            'created_at': signal.created_at.isoformat(),
            'updated_at': signal.updated_at.isoformat(),
        }
        
        # Optional fields
        if signal.percentage_threshold:
            item['percentage_threshold'] = Decimal(str(signal.percentage_threshold))
        if signal.max_triggers:
            item['max_triggers'] = signal.max_triggers
        if signal.last_triggered_at:
            item['last_triggered_at'] = signal.last_triggered_at.isoformat()
        if signal.user_id:
            item['user_id'] = signal.user_id
        if signal.notes:
            item['notes'] = signal.notes
        
        return item
    
    def _item_to_signal(self, item: Dict[str, Any]) -> SignalTarget:
        """
        Конвертирует DynamoDB item в SignalTarget
        
        Decimal -> float для target_price
        """
        from models.signal import ExchangeType, SignalCondition
        
        return SignalTarget(
            id=item['signal_id'],
            name=item['name'],
            exchange=ExchangeType(item['exchange']),
            symbol=item['symbol'],
            condition=SignalCondition(item['condition']),
            target_price=float(item['target_price']),  # Decimal -> float
            active=item.get('active', True),
            triggered_count=item.get('triggered_count', 0),
            percentage_threshold=float(item['percentage_threshold']) if item.get('percentage_threshold') else None,
            max_triggers=item.get('max_triggers'),
            created_at=datetime.fromisoformat(item['created_at']),
            updated_at=datetime.fromisoformat(item['updated_at']),
            last_triggered_at=datetime.fromisoformat(item['last_triggered_at']) if item.get('last_triggered_at') else None,
            user_id=item.get('user_id'),
            notes=item.get('notes'),
        )
    
    async def save_signal(self, signal: SignalTarget) -> bool:
        """
        Сохраняет или обновляет сигнал в DynamoDB (UPSERT - TRUE ASYNC)
        
        Если сигнал с таким ID уже существует:
        - Сохраняет created_at из старой записи
        - Обновляет все остальные поля
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Генерируем ID если его нет
            if not signal.id:
                signal.id = signal.generate_id()
            
            # Проверяем существует ли уже этот сигнал
            pk = f"signal#{signal.id}"
            try:
                response = await asyncio.to_thread(
                    self.table.get_item,
                    Key={'PK': pk, 'SK': 'metadata'}
                )
                existing_item = response.get('Item')
                
                if existing_item:
                    # UPSERT: сохраняем created_at из существующей записи
                    signal.created_at = datetime.fromisoformat(existing_item['created_at'])
                    logger.debug(f"Updating existing signal: {signal.name}")
                else:
                    logger.debug(f"Creating new signal: {signal.name}")
            except ClientError:
                # Если ошибка при получении - создаем новый
                pass
            
            # Обновляем updated_at
            signal.updated_at = datetime.now()
            
            # Сохраняем (перезапись или создание)
            item = self._signal_to_item(signal)
            await asyncio.to_thread(self.table.put_item, Item=item)
            logger.info(f"✅ Saved signal: {signal.name} (ID: {signal.id})")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to save signal {signal.name}: {e}")
            return False
    
    async def load_signals(self) -> List[SignalTarget]:
        """
        Загружает все сигналы из DynamoDB (TRUE ASYNC)
        Использует Query с GSI для оптимизации (вместо Scan)
    
        Returns:
            Список SignalTarget объектов
        """
        try:
            # Пробуем использовать Query с GSI (если индекс существует)
            try:
                # ✅ Настоящий async
                response = await asyncio.to_thread(
                    self.table.query,
                    IndexName='entity_type-index',
                    KeyConditionExpression='entity_type = :type',
                    ExpressionAttributeValues={':type': 'signal'}
                )
                logger.debug("Using Query with GSI (optimized)")
            except ClientError as e:
                # Если GSI не существует, fallback на Scan
                if 'ResourceNotFoundException' in str(e):
                    logger.warning("GSI 'entity_type-index' not found, using Scan (slower)")
                    # ✅ Настоящий async
                    response = await asyncio.to_thread(
                        self.table.scan,
                        FilterExpression='entity_type = :type',
                        ExpressionAttributeValues={':type': 'signal'}
                    )
                else:
                    raise
            
            items = response.get('Items', [])
            signals = [self._item_to_signal(item) for item in items]
            
            logger.info(f"Loaded {len(signals)} signals from DynamoDB")
            return signals
            
        except ClientError as e:
            logger.error(f"Failed to load signals: {e}")
            return []

    
    async def delete_signal(self, signal_id: str) -> bool:
        """
        Удаляет сигнал по ID (TRUE ASYNC)
        
        Args:
            signal_id: ID сигнала
            
        Returns:
            True если успешно
        """
        try:
            # ✅ Настоящий async
            await asyncio.to_thread(
                self.table.delete_item,
                Key={
                    'PK': f"signal#{signal_id}",
                    'SK': 'metadata'
                }
            )
            logger.info(f"Deleted signal: {signal_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete signal {signal_id}: {e}")
            return False
    
    async def update_signal(self, signal: SignalTarget) -> bool:
        """
        Обновляет существующий сигнал
        
        Используем put_item (перезаписывает полностью)
        """
        return await self.save_signal(signal)
    
    async def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Получает данные пользователя по ID (TRUE ASYNC)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с данными пользователя
        """
        try:
            # ✅ Настоящий async
            response = await asyncio.to_thread(
                self.table.get_item,
                Key={
                    'PK': f"user#{user_id}",
                    'SK': 'metadata'
                }
            )
            
            item = response.get('Item', {})
            if not item:
                logger.debug(f"User {user_id} not found")
                return {}
            
            # Убираем служебные поля
            user_data = {k: v for k, v in item.items() if k not in ['PK', 'SK', 'entity_type']}
            return user_data
            
        except ClientError as e:
            logger.error(f"Failed to get user data for {user_id}: {e}")
            return {}
    
    async def save_user_data(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Сохраняет данные пользователя (TRUE ASYNC)
        
        Args:
            user_id: ID пользователя
            data: Словарь с данными
            
        Returns:
            True если успешно
        """
        try:
            item = {
                'PK': f"user#{user_id}",
                'SK': 'metadata',
                'entity_type': 'user',
                'user_id': user_id,
                **data  # Добавляем все данные из словаря
            }
            
            # ✅ Настоящий async
            await asyncio.to_thread(self.table.put_item, Item=item)
            logger.debug(f"Saved user data: {user_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to save user data for {user_id}: {e}")
            return False

    async def get_all_signals(self) -> List[SignalTarget]:
        """Alias for load_signals() for compatibility"""
        return await self.load_signals()

    # ============================================================================
    # USER MANAGEMENT METHODS
    # ============================================================================

    def _user_to_item(self, user) -> Dict[str, Any]:
        """
        Convert User object to DynamoDB item

        Args:
            user: User object from models.user

        Returns:
            DynamoDB item dictionary
        """
        item = {
            'PK': f"user#{user.username}",
            'SK': 'metadata',
            'entity_type': 'user',
            'username': user.username,
            'password_hash': user.password_hash,
            'created_at': user.created_at.isoformat(),
            'is_active': user.is_active,
        }

        # Optional fields
        if user.email:
            item['email'] = user.email
        if user.full_name:
            item['full_name'] = user.full_name
        if user.last_login:
            item['last_login'] = user.last_login.isoformat()
        if user.pushover_key:
            item['pushover_key'] = user.pushover_key
        if user.telegram_chat_id:
            item['telegram_chat_id'] = user.telegram_chat_id
        if user.timezone:
            item['timezone'] = user.timezone

        return item

    def _item_to_user(self, item: Dict[str, Any]):
        """
        Convert DynamoDB item to User object

        Args:
            item: DynamoDB item dictionary

        Returns:
            User object from models.user
        """
        from models.user import User

        return User(
            username=item['username'],
            password_hash=item['password_hash'],
            email=item.get('email'),
            full_name=item.get('full_name'),
            created_at=datetime.fromisoformat(item['created_at']),
            last_login=datetime.fromisoformat(item['last_login']) if item.get('last_login') else None,
            is_active=item.get('is_active', True),
            pushover_key=item.get('pushover_key'),
            telegram_chat_id=item.get('telegram_chat_id'),
            timezone=item.get('timezone'),
        )

    async def get_user(self, username: str):
        """
        Get user by username

        Args:
            username: Username to lookup

        Returns:
            User object if found, None otherwise
        """
        try:
            response = await asyncio.to_thread(
                self.table.get_item,
                Key={
                    'PK': f"user#{username.lower()}",
                    'SK': 'metadata'
                }
            )

            item = response.get('Item')
            if not item:
                logger.debug(f"User not found: {username}")
                return None

            user = self._item_to_user(item)
            logger.debug(f"User found: {username}")
            return user

        except ClientError as e:
            logger.error(f"Failed to get user {username}: {e}")
            return None

    async def save_user(self, user) -> bool:
        """
        Save or update user in DynamoDB

        Args:
            user: User object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            item = self._user_to_item(user)
            await asyncio.to_thread(self.table.put_item, Item=item)
            logger.info(f"✅ Saved user: {user.username}")
            return True

        except ClientError as e:
            logger.error(f"Failed to save user {user.username}: {e}")
            return False
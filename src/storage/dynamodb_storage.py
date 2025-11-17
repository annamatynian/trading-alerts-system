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

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по username (TRUE ASYNC)

        Args:
            username: Username пользователя

        Returns:
            Словарь с данными пользователя или None если не найден
        """
        try:
            response = await asyncio.to_thread(
                self.table.get_item,
                Key={'PK': f"user#{username}", 'SK': 'metadata'}
            )

            if 'Item' not in response:
                return None

            item = response['Item']
            # Убираем служебные поля
            user_data = {k: v for k, v in item.items() if k not in ['PK', 'SK', 'entity_type']}
            return user_data

        except ClientError as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None

    async def save_user(self, username: str, user_data: Dict[str, Any]) -> bool:
        """
        Сохраняет пользователя по username (TRUE ASYNC)

        Args:
            username: Username пользователя
            user_data: Словарь с данными (user_id, password_hash, created_at, metadata)

        Returns:
            True если успешно
        """
        try:
            item = {
                'PK': f"user#{username}",
                'SK': 'metadata',
                'entity_type': 'user',
                'username': username,
                **user_data  # user_id, password_hash, created_at, metadata
            }

            await asyncio.to_thread(self.table.put_item, Item=item)
            logger.debug(f"Saved user: {username}")
            return True

        except ClientError as e:
            logger.error(f"Failed to save user {username}: {e}")
            return False

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Получает всех пользователей (TRUE ASYNC)

        Returns:
            Список словарей с данными пользователей
        """
        try:
            # Сканируем таблицу, ищем только user# записи
            response = await asyncio.to_thread(
                self.table.scan,
                FilterExpression='begins_with(PK, :pk_prefix) AND entity_type = :entity',
                ExpressionAttributeValues={
                    ':pk_prefix': 'user#',
                    ':entity': 'user'
                }
            )

            users = []
            for item in response.get('Items', []):
                # Убираем служебные поля
                user_data = {k: v for k, v in item.items() if k not in ['PK', 'SK', 'entity_type']}
                users.append(user_data)

            logger.debug(f"Loaded {len(users)} users from DynamoDB")
            return users

        except ClientError as e:
            logger.error(f"Failed to get all users: {e}")
            return []

    async def get_all_signals(self) -> List[SignalTarget]:
        """Alias for load_signals() for compatibility"""
        return await self.load_signals()
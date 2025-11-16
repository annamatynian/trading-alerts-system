"""
Базовый абстрактный класс для всех бирж
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from models.price import PriceData
from models.signal import ExchangeType

logger = logging.getLogger(__name__)


class ExchangeBase(ABC):
    """Абстрактный базовый класс для всех бирж"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self._client = None
    
    @property
    @abstractmethod
    def exchange_type(self) -> ExchangeType:
        """Тип биржи"""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """Подключение к бирже"""
        pass
    
    @abstractmethod
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Получить цену одной торговой пары"""
        pass
    
    @abstractmethod
    async def get_multiple_prices(self, symbols: List[str]) -> List[PriceData]:
        """Получить цены нескольких торговых пар"""
        pass
    
    @abstractmethod
    async def is_symbol_valid(self, symbol: str) -> bool:
        """Проверить существует ли торговая пара на бирже"""
        pass
    
    async def disconnect(self):
        """Отключение от биржи"""
        if self._client:
            try:
                if hasattr(self._client, 'close'):
                    await self._client.close()
            except Exception as e:
                logger.warning(f"Error closing exchange connection: {e}")

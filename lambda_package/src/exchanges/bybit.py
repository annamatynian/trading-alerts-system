"""Bybit exchange adapter using pybit library."""
import logging
import asyncio
from typing import List, Optional, Dict, Any
from pybit.unified_trading import HTTP

from exchanges.base import ExchangeBase
from models.price import PriceData
from models.signal import ExchangeType

logger = logging.getLogger(__name__)


class BybitExchange(ExchangeBase):
    """Bybit exchange implementation with async support"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False):
        """
        Initialize Bybit exchange
        
        Args:
            api_key: API key (optional for public endpoints)
            api_secret: API secret (optional for public endpoints)
            testnet: Use testnet
        """
        super().__init__(api_key, api_secret, testnet)
        self._client: Optional[HTTP] = None
    
    @property
    def exchange_type(self) -> ExchangeType:
        """Return exchange type"""
        return ExchangeType.BYBIT

    async def connect(self) -> bool:
        """Initializes the Bybit client."""
        try:
            # Определяем URL в зависимости от testnet
            if self.testnet:
                endpoint = "https://api-testnet.bybit.com"
            else:
                endpoint = "https://api.bybit.com"
            
            # API ключи не нужны для публичных endpoints
            if self.api_key and self.api_secret:
                self._client = HTTP(
                    testnet=self.testnet,
                    api_key=self.api_key,
                    api_secret=self.api_secret
                )
            else:
                # Публичный клиент без аутентификации
                self._client = HTTP(testnet=self.testnet)
            
            logger.info(f"✅ Bybit connected ({'testnet' if self.testnet else 'mainnet'})")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Bybit: {e}")
            return False

    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """
        Fetches the current price for a single symbol from Bybit.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT, ETHUSDT)
        
        Returns:
            PriceData object or None if error
        """
        if not self._client:
            logger.error("Bybit client not initialized.")
            return None
        
        try:
            # Bybit использует формат BTCUSDT (без слэша)
            # Убираем слэш если есть
            symbol_formatted = symbol.replace('/', '')
            
            # Получаем тикер через синхронный API (pybit не async)
            # Используем asyncio.to_thread для неблокирующего вызова
            response = await asyncio.to_thread(
                self._client.get_tickers,
                category="spot",  # Spot market
                symbol=symbol_formatted
            )
            
            if response['retCode'] != 0:
                logger.error(f"Bybit API error: {response['retMsg']}")
                return None
            
            tickers = response['result']['list']
            if not tickers:
                logger.warning(f"No ticker data for {symbol} from Bybit")
                return None
            
            ticker = tickers[0]
            
            # Парсим данные
            last_price = float(ticker['lastPrice'])
            high_24h = float(ticker.get('highPrice24h', 0))
            low_24h = float(ticker.get('lowPrice24h', 0))
            volume_24h = float(ticker.get('volume24h', 0))
            
            return PriceData(
                exchange=self.exchange_type,
                symbol=symbol,
                price=last_price,
                volume_24h=volume_24h,
                high_24h=high_24h,
                low_24h=low_24h,
                raw_data=ticker
            )
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol} from Bybit: {e}")
            return None

    async def get_multiple_prices(self, symbols: List[str]) -> List[PriceData]:
        """
        Fetches prices for multiple symbols from Bybit.
        
        Args:
            symbols: List of trading pairs
        
        Returns:
            List of PriceData objects
        """
        prices = []
        # Используем asyncio.gather для параллельных запросов
        tasks = [self.get_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, PriceData):
                prices.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Failed to fetch price: {result}")
        
        return prices

    async def is_symbol_valid(self, symbol: str) -> bool:
        """
        Check if symbol exists on Bybit.
        
        Args:
            symbol: Trading pair to check
        
        Returns:
            True if valid, False otherwise
        """
        if not self._client:
            return False
        
        try:
            symbol_formatted = symbol.replace('/', '')
            response = await asyncio.to_thread(
                self._client.get_tickers,
                category="spot",
                symbol=symbol_formatted
            )
            return response['retCode'] == 0 and len(response['result']['list']) > 0
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            return False

    async def disconnect(self) -> bool:
        """Closes the Bybit client connection."""
        try:
            # pybit HTTP client не требует явного закрытия
            self._client = None
            logger.info("Bybit disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Bybit: {e}")
            return False

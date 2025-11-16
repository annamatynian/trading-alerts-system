"""Coinbase exchange adapter using a direct API call."""
import logging
import asyncio
import aiohttp  # <--- Используем aiohttp напрямую
from typing import List, Optional, Dict, Any
import ccxt.async_support as ccxt # <--- ccxt используется только для совместимости

from exchanges.base import ExchangeBase
from models.price import PriceData
from models.signal import ExchangeType

logger = logging.getLogger(__name__)

class CoinbaseExchange(ExchangeBase):
    """Coinbase exchange implementation with direct API support"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False):
        """Initialize the adapter."""
        super().__init__(api_key, api_secret, testnet)
        # Инициализируем ccxt клиент (но не будем его использовать для get_price)
        try:
            self._client = ccxt.coinbase()
        except Exception:
            self._client = None 

    @property
    def exchange_type(self) -> ExchangeType:
        """Return exchange type"""
        return ExchangeType.COINBASE

    async def connect(self) -> bool:
        """Initializes the ccxt Coinbase client (optional)."""
        logger.info("✅ Coinbase adapter initialized (direct API mode)")
        return True

    # <--- НАЧАЛО ФИНАЛЬНОГО ИСПРАВЛЕНИЯ ---
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """
        Fetches the current price for a single symbol from Coinbase
        using the direct REST API (bypassing ccxt's fetch_ticker).
        """
        # Конвертируем ALGOUSDT -> ALGO-USDT
        if len(symbol) > 4 and symbol.endswith('USDT'):
            base = symbol[:-4]
            pair = f"{base}-USDT"
        else:
            logger.warning(f"Unsupported symbol format for Coinbase: {symbol}")
            return None
        
        # Прямой URL API Coinbase для получения спотовой цены
        url = f"https://api.coinbase.com/v2/prices/{pair}/spot"
        
        try:
            # Используем aiohttp для прямого запроса
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    
                    if response.status != 200:
                        # Логируем ошибку, если пара не найдена (404) или другая ошибка
                        error_text = await response.text()
                        logger.error(f"Coinbase API error for {pair} (Status {response.status}): {error_text}")
                        return None
                    
                    data = await response.json()
                    price = data.get('data', {}).get('amount')
                    
                    if not price:
                        logger.error(f"Invalid data from Coinbase for {symbol}: {data}")
                        return None
                    
                    # ВНИМАНИЕ: Этот эндпоинт НЕ предоставляет 24h объем/high/low.
                    # Но для проверки цены (нашего главного резервного варианта)
                    # это идеально.
                    return PriceData(
                        exchange=self.exchange_type,
                        symbol=symbol,
                        price=float(price),
                        volume_24h=0, # Недоступно
                        high_24h=0,   # Недоступно
                        low_24h=0,    # Недоступно
                    )
        except (Exception, asyncio.TimeoutError) as e:
            # Этот блок по-прежнему ловит ЛЮБЫЕ ошибки
            logger.error(f"Error fetching direct price for {symbol} from Coinbase: {e}")
            return None
    # <--- КОНЕЦ ФИНАЛЬНОГО ИСПРАВЛЕНИЯ ---

    async def get_multiple_prices(self, symbols: List[str]) -> List[PriceData]:
        """Fetches prices for multiple symbols from Coinbase."""
        # Этот метод теперь будет использовать наш новый get_price
        tasks = [self.get_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        prices = [price for price in results if price]
        return prices

    async def is_symbol_valid(self, symbol: str) -> bool:
        """
Storage service: Validation will happen at fetch time
        """
        return True

    async def disconnect(self) -> bool:
        """Closes the ccxt Coinbase client connection."""
        try:
            if self._client:
                await self._client.close()
                logger.info("Coinbase disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Coinbase: {e}")
            return False
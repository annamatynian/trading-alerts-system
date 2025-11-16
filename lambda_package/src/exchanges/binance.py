"""Binance exchange adapter using ccxt library."""
import logging
import asyncio  # <--- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ 1
import os
from typing import List, Optional, Dict, Any
import ccxt.async_support as ccxt

from exchanges.base import ExchangeBase
from models.price import PriceData
from models.signal import ExchangeType

logger = logging.getLogger(__name__)

class BinanceExchange(ExchangeBase):
    """Binance exchange implementation with async support"""
    
    @property
    def exchange_type(self) -> ExchangeType:
        """Return exchange type"""
        return ExchangeType.BINANCE

    async def connect(self) -> bool:
        """Initializes the ccxt Binance client."""
        try:
            config: Dict[str, Any] = {
                'options': {
                    'defaultType': 'spot',
                },
                'enableRateLimit': True,
            }
            
            # Проверяем наличие прокси
            proxy_url = os.getenv('PROXY_URL')
            if proxy_url and 'your_proxy_url_here' not in proxy_url.lower():
                # Убедимся, что ccxt знает о прокси
                config['aiohttp_proxy'] = proxy_url
                logger.info("Используется прокси для Binance")

            # API ключи не нужны для публичных endpoints
            api_key = os.getenv("BINANCE_API_KEY", "")
            api_secret = os.getenv("BINANCE_API_SECRET", "")
            if api_key and api_secret:
                config['apiKey'] = api_key
                config['secret'] = api_secret
            
            self._client = ccxt.binance(config)
            if self.testnet:
                self._client.set_sandbox_mode(True)
            
            # Не загружаем рынки для быстрого старта
            logger.info("✅ Binance connected (fast mode)")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Binance: {e}")
            if self._client:
                await self._client.close()
            return False

    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Fetches the current price for a single symbol from Binance."""
        if not self._client:
            logger.error("Binance client not initialized.")
            return None
        try:
            # Конвертируем ALGOUSDT -> ALGO/USDT
            if len(symbol) > 4 and symbol.endswith('USDT'):
                base = symbol[:-4]
                ccxt_symbol = f"{base}/USDT"
            else:
                ccxt_symbol = symbol
            
            ticker = await self._client.fetch_ticker(ccxt_symbol)
            return PriceData(
                exchange=self.exchange_type,
                symbol=symbol,
                price=float(ticker['last']),
                volume_24h=float(ticker.get('baseVolume', 0)),
                high_24h=float(ticker.get('high', 0)),
                low_24h=float(ticker.get('low', 0)),
            )
        except (Exception, asyncio.TimeoutError) as e:  # <--- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ 2
            logger.error(f"Error fetching price for {symbol} from Binance: {e}")
            return None

    async def get_multiple_prices(self, symbols: List[str]) -> List[PriceData]:
        """Fetches prices for multiple symbols from Binance."""
        prices = []
        # Используем asyncio.gather для параллельных запросов
        tasks = [self.get_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        for price in results:
            if price:
                prices.append(price)
        return prices

    async def is_symbol_valid(self, symbol: str) -> bool:
        """
        Check if symbol exists on Binance.
        (For public endpoints we just return True)
        """
        return True

    async def disconnect(self) -> bool:
        """Closes the ccxt Binance client connection."""
        try:
            if self._client:
                await self._client.close()
                logger.info("Binance disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Binance: {e}")
            return False
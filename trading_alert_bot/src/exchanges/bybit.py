"""
Адаптер для биржи Bybit
"""
import logging
from typing import List, Optional
from pybit.unified_trading import HTTP
from exchanges.base import ExchangeBase
from models.price import PriceData
from models.alert import ExchangeType

logger = logging.getLogger(__name__)


class BybitExchange(ExchangeBase):
    """Адаптер для работы с Bybit API"""
    
    @property
    def exchange_type(self) -> ExchangeType:
        return ExchangeType.BYBIT
    
    async def connect(self) -> bool:
        """Инициализация клиента Bybit"""
        try:
            # Создаем клиент с ключами только если они предоставлены
            if self.api_key and self.api_secret:
                self._client = HTTP(
                    testnet=self.testnet,
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                )
                logger.info(f"Подключение к Bybit {'testnet' if self.testnet else 'mainnet'} с API ключами")
            else:
                # Публичный клиент для получения цен
                self._client = HTTP(testnet=self.testnet)
                logger.info(f"Подключение к Bybit {'testnet' if self.testnet else 'mainnet'} в публичном режиме")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к Bybit: {e}")
            return False
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Получить цену торговой пары с Bybit"""
        try:
            response = self._client.get_tickers(category="spot", symbol=symbol)
            
            if response['retCode'] != 0:
                logger.error(f"Ошибка API Bybit: {response.get('retMsg', 'Unknown error')}")
                return None
            
            if not response['result']['list']:
                logger.warning(f"Торговая пара {symbol} не найдена на Bybit")
                return None
            
            ticker = response['result']['list'][0]
            price = float(ticker['lastPrice'])
            
            return PriceData(
                exchange=self.exchange_type,
                symbol=symbol,
                price=price,
                volume_24h=float(ticker.get('volume24h', 0)),
                high_24h=float(ticker.get('highPrice24h', 0)) if ticker.get('highPrice24h') else None,
                low_24h=float(ticker.get('lowPrice24h', 0)) if ticker.get('lowPrice24h') else None,
                price_change_percent_24h=float(ticker.get('price24hPcnt', 0)) * 100 if ticker.get('price24hPcnt') else None,
                raw_data=ticker
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения цены {symbol} с Bybit: {e}")
            return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> List[PriceData]:
        """Получить цены нескольких пар с Bybit"""
        results = []
        
        for symbol in symbols:
            price_data = await self.get_price(symbol)
            if price_data:
                results.append(price_data)
        
        return results
    
    async def is_symbol_valid(self, symbol: str) -> bool:
        """Проверить существует ли пара на Bybit"""
        try:
            response = self._client.get_instruments_info(category="spot", symbol=symbol)
            return response['retCode'] == 0 and bool(response['result']['list'])
        except Exception as e:
            logger.error(f"Ошибка проверки символа {symbol}: {e}")
            return False

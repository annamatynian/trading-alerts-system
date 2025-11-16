"""Price Checker Service"""
import logging
import asyncio
from typing import List, Optional
from models.price import PriceData
from models.signal import ExchangeType

logger = logging.getLogger(__name__)

class PriceChecker:
    def __init__(self, exchanges_dict):
        self.exchanges = exchanges_dict
    
    async def get_price(self, exchange: ExchangeType, symbol: str) -> Optional[PriceData]:
        """Get price for symbol from exchange with automatic fallback"""
        exchange_adapter = self.exchanges.get(exchange)
        if not exchange_adapter:
            logger.error(f"Exchange {exchange} not found in available exchanges")
            return None
        
        try:
            price_data = await exchange_adapter.get_price(symbol)
            if price_data:
                return price_data
            logger.warning(f"No price data from {exchange} for {symbol}")
        except Exception as e:
            logger.warning(f"Error getting price for {symbol} on {exchange}: {e}")
        
        # 🔄 FALLBACK: Пробуем другие доступные биржи
        logger.info(f"🔄 Fallback: trying other exchanges for {symbol}")
        for fallback_exchange, fallback_adapter in self.exchanges.items():
            if fallback_exchange == exchange:
                continue  # Пропускаем оригинальную биржу
            
            try:
                logger.info(f"⚙️ Trying {fallback_exchange} as fallback...")
                price_data = await fallback_adapter.get_price(symbol)
                if price_data:
                    logger.info(f"✅ Fallback successful! Got price from {fallback_exchange}")
                    return price_data
            except (Exception, asyncio.TimeoutError) as e:
                logger.warning(f"❌ Fallback {fallback_exchange} also failed: {e}")
                continue
        
        logger.error(f"❌ All exchanges failed for {symbol}")
        return None
    
    async def get_prices_for_exchange(self, exchange: ExchangeType, symbols: List[str]) -> List[PriceData]:
        """Get multiple prices from one exchange with automatic fallback"""
        prices = []
        
        # Пробуем получить каждую цену с fallback механизмом
        for symbol in symbols:
            price_data = await self.get_price(exchange, symbol)
            if price_data:
                prices.append(price_data)
        
        return prices

"""Price Checker Service"""
import logging
from typing import List, Optional
from models.price import PriceData
from models.alert import ExchangeType

logger = logging.getLogger(__name__)

class PriceChecker:
    def __init__(self, exchanges_dict):
        self.exchanges = exchanges_dict
    
    async def get_price(self, exchange: ExchangeType, symbol: str) -> Optional[PriceData]:
        """Get price for symbol from exchange"""
        # TODO: Implement price fetching
        return None
    
    async def get_prices_for_exchange(self, exchange: ExchangeType, symbols: List[str]) -> List[PriceData]:
        """Get multiple prices from one exchange"""
        # TODO: Implement batch price fetching
        return []

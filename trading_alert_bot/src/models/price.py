"""
Price-related data models
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from models.alert import ExchangeType


class PriceData(BaseModel):
    """Current price data from exchange"""
    exchange: ExchangeType
    symbol: str = Field(..., pattern=r'^[A-Z]{3,10}[A-Z]{3,5}$')
    price: float = Field(..., gt=0)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Additional market data
    volume_24h: Optional[float] = Field(None, ge=0)
    high_24h: Optional[float] = Field(None, gt=0)
    low_24h: Optional[float] = Field(None, gt=0)
    price_change_24h: Optional[float] = None
    price_change_percent_24h: Optional[float] = None
    
    # Raw data from exchange
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    def get_price_change_info(self) -> Dict[str, Optional[float]]:
        """Get price change information"""
        return {
            'absolute_change': self.price_change_24h,
            'percent_change': self.price_change_percent_24h,
            'high_24h': self.high_24h,
            'low_24h': self.low_24h
        }


class PriceHistory(BaseModel):
    """Historical price data point"""
    exchange: ExchangeType
    symbol: str
    price: float = Field(..., gt=0)
    volume: Optional[float] = Field(None, ge=0)
    timestamp: datetime
    
    # Technical indicators (optional)
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    rsi: Optional[float] = Field(None, ge=0, le=100)


class MarketSummary(BaseModel):
    """Market summary for a symbol across exchanges"""
    symbol: str
    prices: Dict[ExchangeType, PriceData] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Aggregate data
    average_price: Optional[float] = None
    price_spread: Optional[float] = None  # Max - Min price
    price_spread_percent: Optional[float] = None
    
    def calculate_aggregates(self):
        """Calculate aggregate statistics"""
        if not self.prices:
            return
        
        prices = [data.price for data in self.prices.values()]
        self.average_price = sum(prices) / len(prices)
        self.price_spread = max(prices) - min(prices)
        if self.average_price > 0:
            self.price_spread_percent = (self.price_spread / self.average_price) * 100
    
    def get_best_price(self, condition: str = "buy") -> Optional[tuple[ExchangeType, PriceData]]:
        """Get best price for buying or selling"""
        if not self.prices:
            return None
        
        if condition == "buy":
            # Lowest price for buying
            best_exchange, best_data = min(
                self.prices.items(), 
                key=lambda x: x[1].price
            )
        else:
            # Highest price for selling
            best_exchange, best_data = max(
                self.prices.items(), 
                key=lambda x: x[1].price
            )
        
        return best_exchange, best_data


class ExchangeStatus(BaseModel):
    """Exchange connectivity and status"""
    exchange: ExchangeType
    is_connected: bool = True
    last_successful_request: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int = 0
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None
    
    def record_success(self):
        """Record successful API call"""
        self.is_connected = True
        self.last_successful_request = datetime.now()
        self.error_count = 0
        self.last_error = None
    
    def record_error(self, error_message: str):
        """Record failed API call"""
        self.error_count += 1
        self.last_error = error_message
        if self.error_count >= 3:  # Consider disconnected after 3 failures
            self.is_connected = False

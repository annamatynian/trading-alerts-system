"""
Signal-related data models
"""
import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ExchangeType(str, Enum):
    """Supported exchanges"""
    BINANCE = "binance"
    BYBIT = "bybit"  # Добавлен Bybit
    COINBASE = "coinbase"
    OKEX = "okex"
    KRAKEN = "kraken"


class SignalCondition(str, Enum):
    """Signal trigger conditions"""
    ABOVE = "above"
    BELOW = "below"
    EQUAL = "equal"
    PERCENT_CHANGE = "percent_change"


class SignalStatus(str, Enum):
    """Signal status states"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    PAUSED = "paused"
    EXPIRED = "expired"


class SignalTarget(BaseModel):
    """Configuration for a price signal"""
    id: Optional[str] = Field(None, description="Unique signal identifier")
    name: str = Field(..., description="Human-readable signal name")
    exchange: Optional[ExchangeType] = Field(None, description="Target exchange (optional - uses available exchange if not specified)")
    symbol: str = Field(..., pattern=r'^[A-Z]{5,15}$', description="Trading pair symbol")
    target_price: float = Field(..., gt=0, description="Target price")
    condition: SignalCondition = Field(..., description="Trigger condition")
    
    # Optional fields
    percentage_threshold: Optional[float] = Field(None, gt=0, le=100, description="For percent_change condition")
    active: bool = Field(True, description="Whether signal is active")
    max_triggers: Optional[int] = Field(None, gt=0, description="Maximum number of triggers")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    triggered_count: int = Field(0, ge=0)
    last_triggered_at: Optional[datetime] = None
    
    # User context
    user_id: Optional[str] = Field(None, description="User identifier")
    notes: Optional[str] = Field(None, max_length=500, description="User notes")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate trading pair symbol format"""
        if not v.isupper():
            raise ValueError('Symbol must be uppercase')
        return v
    
    @validator('percentage_threshold')
    def validate_percentage_threshold(cls, v, values):
        """Validate percentage threshold is provided for percent_change condition"""
        if values.get('condition') == SignalCondition.PERCENT_CHANGE and v is None:
            raise ValueError('percentage_threshold required for percent_change condition')
        return v
    
    def is_expired(self) -> bool:
        """Check if signal has reached maximum triggers"""
        return (
            self.max_triggers is not None and 
            self.triggered_count >= self.max_triggers
        )
    
    def can_trigger(self) -> bool:
        """Check if signal can be triggered"""
        return (
            self.active and 
            not self.is_expired()
        )
    
    def generate_id(self) -> str:
        """
        Generate a unique, deterministic ID for this signal based on its key attributes.
        Same signal configuration will always produce the same ID.
        """
        # Create string from key attributes
        exchange_str = self.exchange.value if self.exchange else "any"
        components = [
            exchange_str,
            self.symbol,
            self.condition.value,
            str(self.target_price),
            self.user_id or "default"
        ]
        
        # Generate deterministic hash (БЕЗ префикса signal# - он добавится в storage)
        hash_input = "|".join(components)
        hash_object = hashlib.sha256(hash_input.encode())
        return hash_object.hexdigest()[:16]  # Возвращаем только хеш без префикса


class SignalResult(BaseModel):
    """Result of a signal check"""
    signal: SignalTarget
    current_price: float
    triggered: bool
    trigger_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Additional context
    price_change_percent: Optional[float] = None
    volume_24h: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

"""
Alert-related data models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ExchangeType(str, Enum):
    """Supported exchanges"""
    BYBIT = "bybit"
    BINANCE = "binance"
    OKEX = "okex"
    KRAKEN = "kraken"
    COINBASE = "coinbase"


class AlertCondition(str, Enum):
    """Alert trigger conditions"""
    ABOVE = "above"
    BELOW = "below"
    EQUAL = "equal"
    PERCENT_CHANGE = "percent_change"


class AlertStatus(str, Enum):
    """Alert status states"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    PAUSED = "paused"
    EXPIRED = "expired"


class AlertTarget(BaseModel):
    """Configuration for a price alert"""
    id: Optional[str] = Field(None, description="Unique alert identifier")
    name: str = Field(..., description="Human-readable alert name")
    exchange: ExchangeType = Field(..., description="Target exchange")
    symbol: str = Field(..., pattern=r'^[A-Z]{3,10}[A-Z]{3,5}$', description="Trading pair symbol")
    target_price: float = Field(..., gt=0, description="Target price")
    condition: AlertCondition = Field(..., description="Trigger condition")
    
    # Optional fields
    percentage_threshold: Optional[float] = Field(None, gt=0, le=100, description="For percent_change condition")
    active: bool = Field(True, description="Whether alert is active")
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
        if values.get('condition') == AlertCondition.PERCENT_CHANGE and v is None:
            raise ValueError('percentage_threshold required for percent_change condition')
        return v
    
    def is_expired(self) -> bool:
        """Check if alert has reached maximum triggers"""
        return (
            self.max_triggers is not None and 
            self.triggered_count >= self.max_triggers
        )
    
    def can_trigger(self) -> bool:
        """Check if alert can be triggered"""
        return (
            self.active and 
            not self.is_expired()
        )


class AlertResult(BaseModel):
    """Result of an alert check"""
    alert: AlertTarget
    current_price: float
    triggered: bool
    trigger_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Additional context
    price_change_percent: Optional[float] = None
    volume_24h: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

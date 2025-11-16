"""Base Storage Interface"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from models.alert import AlertTarget

class StorageBase(ABC):
    """Base storage interface"""
    
    @abstractmethod
    async def load_alerts(self) -> List[AlertTarget]:
        """Load all alerts"""
        pass
    
    @abstractmethod
    async def save_alert(self, alert: AlertTarget) -> bool:
        """Save single alert"""
        pass
    
    @abstractmethod
    async def delete_alert(self, alert_id: str) -> bool:
        """Delete alert by ID"""
        pass
    
    @abstractmethod
    async def update_alert(self, alert: AlertTarget) -> bool:
        """Update existing alert"""
        pass
    
    @abstractmethod
    async def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user data by ID"""
        pass

"""Base Storage Interface"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from models.signal import SignalTarget

class StorageBase(ABC):
    """Base storage interface"""
    
    @abstractmethod
    async def load_signals(self) -> List[SignalTarget]:
        """Load all signals"""
        pass
    
    @abstractmethod
    async def save_signal(self, signal: SignalTarget) -> bool:
        """Save single signal"""
        pass
    
    @abstractmethod
    async def delete_signal(self, signal_id: str) -> bool:
        """Delete signal by ID"""
        pass
    
    @abstractmethod
    async def update_signal(self, signal: SignalTarget) -> bool:
        """Update existing signal"""
        pass
    
    @abstractmethod
    async def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user data by ID"""
        pass

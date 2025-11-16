"""Notification Service - Pushover only via HTTP API"""
import asyncio
import logging
import aiohttp
from typing import Optional

from models.signal import SignalResult
from utils.config import NotificationConfig
from storage.base import StorageBase

logger = logging.getLogger(__name__)

class NotificationService:
    PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
    
    def __init__(self, config: NotificationConfig, storage: StorageBase):
        self.config = config
        self.storage = storage
        self.pushover_api_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize Pushover API token"""
        if self.config.pushover_enabled and self.config.pushover_api_token:
            self.pushover_api_token = self.config.pushover_api_token
            logger.info("✅ Pushover API token configured")
            
            # Create aiohttp session for async requests
            self._session = aiohttp.ClientSession()
        else:
            logger.warning("⚠️ Pushover is not enabled or API token is missing")

    async def send_alert_notification(self, result: SignalResult):
        """
        Send notification via Pushover HTTP API.
        Gets user's Pushover key from storage.
        """
        user_id = result.signal.user_id
        if not user_id:
            logger.error(f"❌ Signal '{result.signal.name}' has no user_id")
            return

        # Get user's Pushover key from storage
        user_data = await self.storage.get_user_data(user_id)
        user_pushover_key = user_data.get("pushover_key")

        # Send via Pushover
        if not self.pushover_api_token:
            logger.error(f"❌ Pushover API token not configured")
            return
            
        if not user_pushover_key:
            logger.error(f"❌ No Pushover key for user {user_id}")
            return
            
        await self.send_pushover_alert(result, user_pushover_key)

    async def send_pushover_alert(self, result: SignalResult, user_key: str):
        """Send alert via Pushover HTTP API with emergency priority"""
        if not self.pushover_api_token or not self._session:
            logger.error("❌ Pushover not initialized")
            return
            
        title = f"🚨 Alert: {result.signal.name}"
        message_body = (
            f"Symbol: {result.signal.symbol}\n"
            f"Exchange: {result.signal.exchange.value.upper()}\n"
            f"Current Price: ${result.current_price:,.4f}\n"
            f"Target: ${result.signal.target_price:,.4f}"
        )
        
        # Pushover API payload
        payload = {
            "token": self.pushover_api_token,
            "user": user_key,
            "title": title,
            "message": message_body,
            "sound": "persistent",
            "priority": 2,  # Emergency priority - requires acknowledgment
            "retry": 30,    # Retry every 30 seconds
            "expire": 3600  # Expire after 1 hour
        }
        
        try:
            async with self._session.post(self.PUSHOVER_API_URL, data=payload) as response:
                response_data = await response.json()
                
                if response.status == 200 and response_data.get("status") == 1:
                    logger.info(f"✅ Pushover alert sent successfully for '{result.signal.name}'")
                else:
                    logger.error(f"❌ Pushover API error: {response_data}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to send Pushover notification to {user_key}: {e}")
    
    async def close(self):
        """Close aiohttp session"""
        if self._session:
            await self._session.close()
            logger.info("📌 Notification service closed (aiohttp session closed)")
        else:
            logger.info("📌 Notification service closed")

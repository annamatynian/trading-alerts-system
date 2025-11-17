"""Notification Service - Pushover only via HTTP API with Multi-User support"""
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

    def __init__(self, config: NotificationConfig, storage: StorageBase, use_secrets_manager: bool = True):
        self.config = config
        self.storage = storage
        self.use_secrets_manager = use_secrets_manager
        self.secrets_manager: Optional['SecretsManager'] = None
        self.pushover_api_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize Pushover API token from Secrets Manager or config"""
        # Пробуем использовать Secrets Manager
        if self.use_secrets_manager:
            try:
                from utils.secrets_manager import get_secrets_manager
                self.secrets_manager = get_secrets_manager()
                self.pushover_api_token = self.secrets_manager.get_pushover_api_token()
                logger.info("✅ Pushover API token loaded from AWS Secrets Manager")

                # Логируем список пользователей
                users = self.secrets_manager.list_users()
                logger.info(f"✅ Loaded {len(users)} users from Secrets Manager: {', '.join(users)}")

            except Exception as e:
                logger.warning(f"⚠️  Failed to load from Secrets Manager: {e}")
                logger.info("Falling back to config...")
                self.use_secrets_manager = False

        # Fallback на config если Secrets Manager не сработал
        if not self.use_secrets_manager:
            if self.config.pushover_enabled and self.config.pushover_api_token:
                self.pushover_api_token = self.config.pushover_api_token
                logger.info("✅ Pushover API token configured from environment")
            else:
                logger.warning("⚠️ Pushover is not enabled or API token is missing")

        # Создаем aiohttp session
        if self.pushover_api_token:
            self._session = aiohttp.ClientSession()
            logger.info("✅ HTTP session created for Pushover API")
        else:
            logger.error("❌ No Pushover API token available")

    async def send_alert_notification(self, result: SignalResult):
        """
        Send notification via Pushover HTTP API.
        Gets user's Pushover key from Secrets Manager (preferred) or storage (fallback).
        """
        user_id = result.signal.user_id
        if not user_id:
            logger.error(f"❌ Signal '{result.signal.name}' has no user_id")
            return

        user_pushover_key = None

        # Вариант 1: Получаем из Secrets Manager (multiuser)
        if self.use_secrets_manager and self.secrets_manager:
            try:
                user_pushover_key = self.secrets_manager.get_user_pushover_key(user_id)
                if user_pushover_key:
                    user_config = self.secrets_manager.get_user_config(user_id)
                    user_name = user_config.get('name', user_id) if user_config else user_id
                    logger.info(f"✅ Found Pushover key for user '{user_name}' ({user_id}) from Secrets Manager")
                else:
                    logger.warning(f"⚠️  No Pushover key in Secrets Manager for user '{user_id}'")
            except Exception as e:
                logger.warning(f"⚠️  Failed to get user config from Secrets Manager: {e}")

        # Вариант 2: Fallback на storage (старая логика)
        if not user_pushover_key:
            try:
                user_data = await self.storage.get_user_data(user_id)
                user_pushover_key = user_data.get("pushover_key")
                if user_pushover_key:
                    logger.info(f"✅ Found Pushover key for user '{user_id}' from storage")
                else:
                    logger.error(f"❌ No Pushover key found in storage for user '{user_id}'")
            except Exception as e:
                logger.warning(f"⚠️  Failed to get user data from storage: {e}")

        # Проверки перед отправкой
        if not self.pushover_api_token:
            logger.error(f"❌ Pushover API token not configured")
            return

        if not user_pushover_key:
            logger.error(f"❌ No Pushover key for user {user_id} (checked both Secrets Manager and storage)")
            return

        # Отправляем уведомление
        await self.send_pushover_alert(result, user_pushover_key, user_id)

    async def send_pushover_alert(self, result: SignalResult, user_key: str, user_id: str = "unknown"):
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
                    logger.info(f"✅ Pushover alert sent successfully to user '{user_id}' for '{result.signal.name}'")
                else:
                    logger.error(f"❌ Pushover API error for user '{user_id}': {response_data}")

        except Exception as e:
            logger.error(f"❌ Failed to send Pushover notification to user '{user_id}': {e}")

    async def close(self):
        """Close aiohttp session"""
        if self._session:
            await self._session.close()
            logger.info("📌 Notification service closed (aiohttp session closed)")
        else:
            logger.info("📌 Notification service closed")

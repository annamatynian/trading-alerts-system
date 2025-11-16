"""Notification Service"""
import asyncio
import logging

import chump
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from models.alert import AlertResult
from utils.config import NotificationConfig
from storage.base import StorageBase

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, config: NotificationConfig, storage: StorageBase):
        self.config = config
        self.storage = storage
        self.telegram_bot: Bot | None = None
        self.pushover_client: chump.Client | None = None

    async def initialize(self):
        if self.config.telegram_enabled and self.config.telegram_bot_token:
            try:
                self.telegram_bot = Bot(token=self.config.telegram_bot_token)
                bot_info = await self.telegram_bot.get_me()
                logger.info(f"Telegram bot initialized successfully: @{bot_info.username}")
            except TelegramAPIError as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.telegram_bot = None
        
        if self.config.pushover_enabled and self.config.pushover_api_token:
            try:
                self.pushover_client = chump.Client(self.config.pushover_api_token)
                if self.pushover_client.is_authenticated():
                    logger.info("Pushover client initialized and authenticated successfully")
                else:
                    logger.error("Pushover authentication failed. Check your API Token.")
                    self.pushover_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Pushover client: {e}")
                self.pushover_client = None

    async def send_alert_notification(self, result: AlertResult):
        """
        Главный метод для отправки уведомлений.
        Теперь он сам получает данные пользователя из хранилища.
        """
        logger.info(f"Processing triggered alert: {result.alert.name}")
        
        user_id = result.alert.user_id
        if not user_id:
            logger.error(f"Alert '{result.alert.name}' has no user_id. Cannot send notification.")
            return

        user_data = await self.storage.get_user_data(user_id)
        user_pushover_key = user_data.get("pushover_key")
        user_telegram_chat_id = user_data.get("chat_id")

        # Приоритет отдаем Pushover для критических алертов
        if self.pushover_client and user_pushover_key:
            await self.send_critical_alert(result, user_pushover_key)
        # Если Pushover не настроен, отправляем в Telegram
        elif self.telegram_bot and user_telegram_chat_id:
            logger.warning(f"Pushover not configured for user {user_id}. Falling back to Telegram.")
            await self.send_telegram_message(result, user_telegram_chat_id)
        else:
            logger.error(f"No notification methods available for user {user_id} on alert '{result.alert.name}'.")

    async def send_telegram_message(self, result: AlertResult, chat_id: str):
        if not self.telegram_bot:
            return
        message_text = (
            f"🔔 **Сработал алерт: {result.alert.name}**\n\n"
            f"**Пара:** `{result.alert.symbol}`\n"
            f"**Биржа:** {result.alert.exchange.value.upper()}\n"
            f"**Текущая цена:** `${result.current_price:,.2f}`"
        )
        try:
            await self.telegram_bot.send_message(chat_id, message_text, parse_mode="Markdown")
            logger.info(f"Standard alert for '{result.alert.name}' sent to Telegram chat {chat_id}.")
        except TelegramAPIError as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")

    async def send_critical_alert(self, result: AlertResult, user_key: str):
        if not self.pushover_client:
            return
        title = f"🚨 Сработал алерт: {result.alert.name}"
        message_body = (
            f"Пара {result.alert.symbol} на бирже {result.alert.exchange.value.upper()} "
            f"достигла цены ${result.current_price:,.2f}."
        )
        try:
            user = self.pushover_client.get_user(user_key)
            message = user.create_message(
                title=title,
                message=message_body,
                sound='persistent',
                priority=2,
                retry=30,
                expire=3600
            )
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, message.send)
            logger.info(f"Critical alert for '{result.alert.name}' sent successfully via Pushover.")
        except Exception as e:
            logger.error(f"Failed to send Pushover notification for user {user_key}: {e}")

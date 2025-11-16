import sys
import os
import asyncio
import logging

# Добавляем папку src в PYTHONPATH, чтобы импорты работали
src_path = os.path.dirname(os.path.abspath(__file__))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Импорты ---
from aiogram import Bot, Dispatcher
from handlers import commands as commands_router
from services.alert_manager import AlertManager
from services.price_checker import PriceChecker
from services.notification import NotificationService
from storage.json_storage import JSONStorage
from exchange_adapters.factory import create_exchange_adapters
from utils.config import load_config
from utils.logger import setup_logging
from storage.base import StorageBase

# --- ОПРЕДЕЛЯЕМ КОРНЕВУЮ ПАПКУ ПРОЕКТА ---
# Это нужно, чтобы найти .env и alerts.json, которые лежат на уровень выше
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


async def run_alert_checks_periodically(alert_manager: AlertManager, interval_seconds: int):
    """Запускает проверку алертов в бесконечном цикле."""
    while True:
        try:
            await alert_manager.check_all_alerts()
        except Exception as e:
            logging.error(f"An error occurred during the alert check cycle: {e}", exc_info=True)
        await asyncio.sleep(interval_seconds)


async def main():
    """Главная функция, которая запускает и бота, и проверку алертов."""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # 1. Загружаем конфигурацию, указывая путь к .env файлу
        config = load_config(env_path=os.path.join(PROJECT_ROOT, '.env'))
        logger.info("Configuration loaded successfully")
        
        # 2. Создаем все зависимости
        storage_path = os.path.join(PROJECT_ROOT, config.app.json_file_path)
        storage: StorageBase = JSONStorage(storage_path)
        
        exchange_adapters = await create_exchange_adapters(config.exchanges)
        price_checker = PriceChecker(exchange_adapters)
        notification_service = NotificationService(config.notifications, storage=storage)
        await notification_service.initialize()
        
        # 3. Собираем AlertManager
        alert_manager = AlertManager(
            price_checker=price_checker,
            notification_service=notification_service,
            storage_service=storage
        )
        
        # 4. Настраиваем Telegram-бота
        bot = Bot(token=config.notifications.telegram_bot_token)
        dp = Dispatcher()
        
        # Сохраняем storage в workflow_data, чтобы handlers могли его использовать
        dp.workflow_data.update({"storage": storage})
        
        dp.include_router(commands_router.router)
        
        # 5. Запускаем проверку алертов в фоновом режиме
        logger.info("Starting background alert checker...")
        asyncio.create_task(
            run_alert_checks_periodically(alert_manager, config.app.check_interval_seconds)
        )

        logger.info("Bot is starting...")
        await dp.start_polling(bot)

    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

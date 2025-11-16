"""
AWS Lambda handler для проверки алертов
Эта функция запускается по расписанию (EventBridge/CloudWatch)
"""
import os
import sys
import asyncio
import logging

# Добавляем текущую директорию в path для импортов
sys.path.insert(0, os.path.dirname(__file__))

from services.alert_manager import AlertManager
from services.price_checker import PriceChecker
from services.notification import NotificationService
from storage.json_storage import JSONStorage
from exchange_adapters.factory import create_exchange_adapters
from utils.config import load_config
from utils.logger import setup_logging

# Инициализация логирования
setup_logging()
logger = logging.getLogger(__name__)


async def check_alerts_once():
    """
    Одна проверка всех алертов.
    Вызывается Lambda каждый раз при срабатывании триггера.
    """
    try:
        logger.info("Lambda function started - checking alerts...")
        
        # 1. Загружаем конфигурацию из переменных окружения
        config = load_config()
        logger.info("Configuration loaded from environment variables")
        
        # 2. Создаем все зависимости
        # В Lambda используем /tmp для временных файлов
        storage_path = f"/tmp/{config.app.json_file_path}"
        storage = JSONStorage(storage_path)
        
        exchange_adapters = await create_exchange_adapters(config.exchanges)
        logger.info(f"Connected to {len(exchange_adapters)} exchanges")
        
        price_checker = PriceChecker(exchange_adapters)
        notification_service = NotificationService(config.notifications, storage=storage)
        await notification_service.initialize()
        
        # 3. Создаем AlertManager
        alert_manager = AlertManager(
            price_checker=price_checker,
            notification_service=notification_service,
            storage_service=storage
        )
        
        # 4. Проверяем все алерты ОДИН РАЗ
        await alert_manager.check_all_alerts()
        
        logger.info("Alert check completed successfully")
        
        return {
            'statusCode': 200,
            'body': 'Alert check completed successfully'
        }
        
    except Exception as e:
        logger.error(f"Error in Lambda function: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }


def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    
    Args:
        event: EventBridge/CloudWatch event (не используется)
        context: Lambda context
    
    Returns:
        dict: Response with statusCode and body
    """
    logger.info(f"Lambda invoked. Request ID: {context.request_id}")
    
    # Запускаем асинхронную проверку
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(check_alerts_once())
    
    return result

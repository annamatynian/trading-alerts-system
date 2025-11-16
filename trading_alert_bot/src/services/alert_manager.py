# Это файл src/services/alert_manager.py

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

# --- Импорты ваших моделей и сервисов ---
from models.alert import AlertTarget, AlertResult, AlertCondition
from services.price_checker import PriceChecker
from services.notification import NotificationService
from storage.base import StorageBase

logger = logging.getLogger(__name__)

class AlertManager:
    """
    Главный сервис, который управляет жизненным циклом алертов:
    1. Загружает активные алерты из хранилища.
    2. Получает актуальные цены с бирж.
    3. Проверяет, сработали ли условия алертов.
    4. Отправляет уведомления через NotificationService.
    5. Обновляет состояние сработавших алертов.
    """
    def __init__(
        self,
        price_checker: PriceChecker,
        notification_service: NotificationService,
        storage_service: StorageBase
    ):
        self.price_checker = price_checker
        self.notification_service = notification_service
        self.storage = storage_service

    async def check_all_alerts(self):
        """
        Основной метод для выполнения одного цикла проверки всех алертов.
        """
        logger.info("Starting new alert check cycle...")
        
        # 1. Загружаем все алерты из хранилища
        try:
            all_alerts = await self.storage.load_alerts()
        except Exception as e:
            logger.error(f"Failed to load alerts from storage: {e}")
            return

        # Фильтруем только активные алерты, которые могут сработать
        active_alerts = [alert for alert in all_alerts if alert.can_trigger()]
        if not active_alerts:
            logger.info("No active alerts to check.")
            return
        
        # 2. Группируем алерты, чтобы эффективно получать цены
        # Структура: {exchange: {symbol: [alert1, alert2, ...]}}
        alerts_to_check = defaultdict(lambda: defaultdict(list))
        for alert in active_alerts:
            alerts_to_check[alert.exchange][alert.symbol].append(alert)

        # 3. Асинхронно получаем все необходимые цены
        price_tasks = []
        for exchange, symbols in alerts_to_check.items():
            price_tasks.append(
                self.price_checker.get_prices_for_exchange(exchange, list(symbols.keys()))
            )
        
        # Результат будет списком списков [ [price_data1, price_data2], [price_data3] ]
        price_results_list = await asyncio.gather(*price_tasks, return_exceptions=True)
        
        # Преобразуем результат в удобный словарь { (exchange, symbol): price }
        current_prices = {}
        for result in price_results_list:
            if isinstance(result, list):
                for price_data in result:
                    key = (price_data.exchange, price_data.symbol)
                    current_prices[key] = price_data.price
            elif isinstance(result, Exception):
                logger.error(f"Error fetching prices: {result}")


        # 4. Проверяем условия для каждого алерта
        triggered_results = []
        for alert in active_alerts:
            price_key = (alert.exchange, alert.symbol)
            current_price = current_prices.get(price_key)

            if current_price is None:
                logger.warning(f"Could not get price for {alert.symbol} on {alert.exchange}. Skipping alert '{alert.name}'.")
                continue

            triggered = False
            if alert.condition == AlertCondition.ABOVE and current_price > alert.target_price:
                triggered = True
            elif alert.condition == AlertCondition.BELOW and current_price < alert.target_price:
                triggered = True
            elif alert.condition == AlertCondition.EQUAL and current_price == alert.target_price:
                triggered = True
            
            if triggered:
                logger.info(f"Alert '{alert.name}' triggered for {alert.symbol} at price {current_price}")
                result = AlertResult(
                    alert=alert,
                    current_price=current_price,
                    triggered=True
                )
                triggered_results.append(result)

        # 5. Если есть сработавшие алерты, отправляем уведомления и обновляем их
        if not triggered_results:
            logger.info("Alert check cycle completed. No alerts were triggered.")
            return

        # Асинхронно отправляем все уведомления
        notification_tasks = [
            self.notification_service.send_alert_notification(result)
            for result in triggered_results
        ]
        await asyncio.gather(*notification_tasks, return_exceptions=True)
        
        # Асинхронно обновляем алерты в базе данных
        update_tasks = []
        for result in triggered_results:
            alert_to_update = result.alert
            alert_to_update.triggered_count += 1
            alert_to_update.last_triggered_at = datetime.now(timezone.utc)
            # Если алерт одноразовый, деактивируем его
            if alert_to_update.max_triggers == 1:
                alert_to_update.active = False
            
            update_tasks.append(self.storage.update_alert(alert_to_update))
            
        await asyncio.gather(*update_tasks, return_exceptions=True)
        
        logger.info(f"Alert check cycle completed. {len(triggered_results)} alerts were triggered and processed.")

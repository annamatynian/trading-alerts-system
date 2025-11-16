# Это файл src/services/signal_manager.py

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

# --- Импорты ваших моделей и сервисов ---
from models.signal import SignalTarget, SignalResult, SignalCondition
from services.price_checker import PriceChecker
from services.notification import NotificationService
from storage.base import StorageBase

logger = logging.getLogger(__name__)

class SignalManager:
    """
    Главный сервис, который управляет жизненным циклом сигналов:
    1. Загружает активные сигналы из хранилища.
    2. Получает актуальные цены с бирж.
    3. Проверяет, сработали ли условия сигналов.
    4. Отправляет уведомления через NotificationService.
    5. Обновляет состояние сработавших сигналов.
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

    async def check_all_signals(self):
        """
        Основной метод для выполнения одного цикла проверки всех сигналов.
        
        Returns:
            List[SignalResult]: Список результатов проверки ДЛЯ ВСЕХ сигналов (включая triggered=false)
        """
        logger.info("Starting new signal check cycle...")
        
        # 1. Загружаем все сигналы из хранилища
        try:
            all_signals = await self.storage.load_signals()
        except Exception as e:
            logger.error(f"Failed to load signals from storage: {e}")
            return []

        # Фильтруем только активные сигналы, которые могут сработать
        active_signals = [signal for signal in all_signals if signal.can_trigger()]
        if not active_signals:
            logger.info("No active signals to check.")
            return []
        
        # 2. Группируем сигналы, чтобы эффективно получать цены
        # Структура: {exchange: {symbol: [signal1, signal2, ...]}}
        signals_to_check = defaultdict(lambda: defaultdict(list))
        for signal in active_signals:
            signals_to_check[signal.exchange][signal.symbol].append(signal)

        # 3. Асинхронно получаем все необходимые цены
        price_tasks = []
        for exchange, symbols in signals_to_check.items():
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


        # 4. Проверяем условия для каждого сигнала
        all_results = []  # ВСЕ результаты (для CSV)
        triggered_results = []  # Только сработавшие (для notifications)
        
        for signal in active_signals:
            price_key = (signal.exchange, signal.symbol)
            current_price = current_prices.get(price_key)

            if current_price is None:
                logger.warning(f"Could not get price for {signal.symbol} on {signal.exchange}. Skipping signal '{signal.name}'.")
                continue

            triggered = False
            if signal.condition == SignalCondition.ABOVE and current_price > signal.target_price:
                triggered = True
            elif signal.condition == SignalCondition.BELOW and current_price < signal.target_price:
                triggered = True
            elif signal.condition == SignalCondition.EQUAL and current_price == signal.target_price:
                triggered = True
            
            # Создаем результат (вне зависимости от triggered)
            result = SignalResult(
                signal=signal,
                current_price=current_price,
                triggered=triggered
            )
            all_results.append(result)
            
            if triggered:
                logger.info(f"Signal '{signal.name}' triggered for {signal.symbol} at price {current_price}")
                triggered_results.append(result)

        # 5. Если есть сработавшие сигналы, отправляем уведомления и обновляем их
        if not triggered_results:
            logger.info("Signal check cycle completed. No signals were triggered.")
            return all_results  # Возвращаем все результаты

        # Асинхронно отправляем все уведомления
        notification_tasks = [
            self.notification_service.send_alert_notification(result)
            for result in triggered_results
        ]
        await asyncio.gather(*notification_tasks, return_exceptions=True)
        
        # Асинхронно обновляем сигналы в базе данных
        update_tasks = []
        for result in triggered_results:
            signal_to_update = result.signal
            signal_to_update.triggered_count += 1
            signal_to_update.last_triggered_at = datetime.now(timezone.utc)
            # ВАРИАНТ 1: Один раз НАВСЕГДА - деактивируем после первого срабатывания
            signal_to_update.active = False
            
            update_tasks.append(self.storage.update_signal(signal_to_update))
            
        await asyncio.gather(*update_tasks, return_exceptions=True)
        
        logger.info(f"Signal check cycle completed. {len(triggered_results)} signals were triggered and processed.")
        return all_results  # Возвращаем ВСЕ результаты для CSV

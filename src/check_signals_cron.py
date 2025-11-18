"""
Скрипт для проверки сигналов из Google Sheets
запускается по расписанию (Cron Job)
"""
import sys
import os
import asyncio
import logging

# --- Настройка путей ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(PROJECT_ROOT, 'src')
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from utils.logger import setup_logging
from utils.config import load_config
from services.sheets_reader import SheetsReader
from services.price_checker import PriceChecker
from services.notification import NotificationService
from services.signal_manager import SignalManager
from storage.json_storage import JSONStorage
from models.signal import SignalTarget, ExchangeType, SignalCondition
from exchanges.binance import BinanceExchange
from exchanges.bybit import BybitExchange

logger = logging.getLogger(__name__)


async def main():
    """Главная функция для проверки сигналов"""
    setup_logging(logging.INFO)  # Вернули INFO
    
    # Отключаем шумные логгеры сторонних библиотек
    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Уменьшаем шум от внутренних модулей
    logging.getLogger('storage.json_storage').setLevel(logging.WARNING)
    logging.getLogger('services.sheets_reader').setLevel(logging.WARNING)
    
    logger.info("=" * 60)
    logger.info("Starting signal check from Google Sheets")
    logger.info("=" * 60)
    
    exchanges = {}  # Инициализируем exchanges в начале
    notification_service = None  # Инициализируем notification_service в начале
    
    try:
        # 1. Загружаем конфигурацию
        env_path = os.path.join(PROJECT_ROOT, '.env')
        config = load_config(env_path=env_path)
        logger.info("Configuration loaded successfully")
        
        # 2. Инициализируем биржи
        # Binance
        if ExchangeType.BINANCE in config.exchanges:
            binance_config = config.get_exchange_config(ExchangeType.BINANCE)
            try:
                binance = BinanceExchange(
                    api_key=binance_config.api_key,
                    api_secret=binance_config.api_secret
                )
                await binance.connect()
                exchanges[ExchangeType.BINANCE] = binance
                logger.info("✅ Binance initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Binance: {e}")
        
        # Bybit
        if ExchangeType.BYBIT in config.exchanges:
            bybit_config = config.get_exchange_config(ExchangeType.BYBIT)
            try:
                bybit = BybitExchange(
                    api_key=bybit_config.api_key,
                    api_secret=bybit_config.api_secret
                )
                await bybit.connect()
                exchanges[ExchangeType.BYBIT] = bybit
                logger.info("✅ Bybit initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Bybit: {e}")
        
        if not exchanges:
            logger.error("❌ No exchanges initialized - cannot check prices")
            return
        
        # 3. Читаем сигналы из Google Sheets
        sheets_reader = SheetsReader()
        
        if not sheets_reader.test_connection():
            logger.error("❌ Failed to connect to Google Sheets")
            return
        
        signals_data = sheets_reader.read_signals()
        logger.info(f"📊 Read {len(signals_data)} signals from Google Sheets")
        
        if not signals_data:
            logger.info("ℹ️  No active signals found - nothing to check")
            return
        
        # 4. Конвертируем данные из Sheets в SignalTarget объекты
        signals = []
        for i, signal_dict in enumerate(signals_data, 1):
            try:
                # Парсим exchange
                exchange_str = signal_dict['exchange'].lower()
                exchange = ExchangeType.BINANCE if 'binance' in exchange_str else ExchangeType.BYBIT
                
                # Парсим condition
                condition_str = signal_dict['condition'].lower()
                if 'above' in condition_str or '>' in condition_str:
                    condition = SignalCondition.ABOVE
                elif 'below' in condition_str or '<' in condition_str:
                    condition = SignalCondition.BELOW
                elif 'equal' in condition_str or '=' in condition_str or '==' in condition_str:
                    condition = SignalCondition.EQUAL
                elif 'percent' in condition_str or '%' in condition_str:
                    condition = SignalCondition.PERCENT_CHANGE
                else:
                    logger.warning(f"⚠️  Signal {i}: Unknown condition '{condition_str}' - skipping")
                    continue
                
                # Создаём имя для сигнала
                symbol = signal_dict['symbol'].upper()
                target_price = float(signal_dict['target_price'])
                signal_name = f"{exchange.value.upper()} {symbol} {condition.value} ${target_price}"
                
                # Создаём SignalTarget
                signal = SignalTarget(
                    name=signal_name,
                    exchange=exchange,
                    symbol=symbol,
                    condition=condition,
                    target_price=target_price,
                    user_id=signal_dict.get('pushover_user_key'),
                    active=signal_dict.get('active', True)
                )
                
                signals.append(signal)
                logger.info(f"📊 Trading Signal {i}: {exchange.value} {signal.symbol} {condition.value} {signal.target_price}")
                
            except Exception as e:
                logger.error(f"❌ Failed to parse signal {i}: {e}")
                continue
        
        if not signals:
            logger.warning("⚠️  No valid signals to check")
            return
        
        # 5. Инициализируем сервисы
        price_checker = PriceChecker(exchanges)
        
        # Используем хранилище в папке проекта (сохраняет историю срабатываний)
        storage_path = os.path.join(PROJECT_ROOT, 'signals_state.json')
        storage = JSONStorage(storage_path)
        logger.info(f"💾 Storage: {storage_path}")
        
        # Создаём NotificationService с правильными параметрами
        notification_service = NotificationService(
            config=config.notifications,
            storage=storage
        )
        
        # Инициализируем NotificationService
        await notification_service.initialize()
        
        # Сохраняем сигналы в storage для SignalManager
        for signal in signals:
            await storage.save_signal(signal)
            
            # Сохраняем данные пользователя для уведомлений
            if signal.user_id:
                await storage.save_user_data(signal.user_id, {
                    "pushover_key": signal.user_id
                })
        
        signal_manager = SignalManager(
            price_checker=price_checker,
            notification_service=notification_service,
            storage_service=storage
        )
        
        # 6. Запускаем проверку сигналов
        logger.info("🔍 Starting signal checks...")
        await signal_manager.check_all_signals()
        
        logger.info("=" * 60)
        logger.info("✅ Signal check completed successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Critical error in main: {e}", exc_info=True)
    finally:
        # Закрываем соединения
        logger.info("📌 Closing connections...")
        
        # Закрываем биржи
        if exchanges:
            for exchange_type, exchange in exchanges.items():
                try:
                    await exchange.disconnect()
                    logger.info(f"✅ Closed connection to {exchange_type.value}")
                except Exception as e:
                    logger.warning(f"⚠️ Error closing {exchange_type.value}: {e}")
        
        # Закрываем notification service
        if notification_service:
            try:
                await notification_service.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing notification service: {e}")


if __name__ == "__main__":
    asyncio.run(main())

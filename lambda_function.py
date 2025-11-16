"""
AWS Lambda handler для проверки сигналов из Google Sheets
Запускается по расписанию CloudWatch Events каждый час
"""
import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.signal import SignalTarget, ExchangeType, SignalCondition
from services.sheets_reader import SheetsReader
from services.price_checker import PriceChecker
from services.notification import NotificationService
from storage.dynamodb_storage import DynamoDBStorage
from exchanges.binance import BinanceExchange
from exchanges.coinbase import CoinbaseExchange
from services.signal_manager import SignalManager
from utils.config import load_config
from utils.logger import setup_logging

# Инициализация логирования
setup_logging()
logger = logging.getLogger(__name__)

# Глобальные переменные для переиспользования между вызовами (warm start optimization)
exchanges = {}
storage = None
notification_service = None


def init_exchanges(config):
    """Инициализация бирж (переиспользуется между вызовами Lambda)"""
    global exchanges
    
    if exchanges:
        logger.info("Reusing existing exchange connections")
        return exchanges
    
    logger.info("Initializing exchanges...")
    
    # Binance
    if ExchangeType.BINANCE in config.exchanges:
        binance_config = config.get_exchange_config(ExchangeType.BINANCE)
        try:
            binance = BinanceExchange(
                api_key=binance_config.api_key,
                api_secret=binance_config.api_secret
            )
            # Для Lambda используем синхронное подключение
            loop = asyncio.get_event_loop()
            loop.run_until_complete(binance.connect())
            exchanges[ExchangeType.BINANCE] = binance
            logger.info("✅ Binance initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Binance: {e}")
    
    # Coinbase
    if ExchangeType.COINBASE in config.exchanges:
        coinbase_config = config.get_exchange_config(ExchangeType.COINBASE)
        try:
            coinbase = CoinbaseExchange(
                api_key=coinbase_config.api_key,
                api_secret=coinbase_config.api_secret
            )
            loop = asyncio.get_event_loop()
            loop.run_until_complete(coinbase.connect())
            exchanges[ExchangeType.COINBASE] = coinbase
            logger.info("✅ Coinbase initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Coinbase: {e}")
    
    return exchanges


async def check_signals_from_sheets():
    """
    Основная логика проверки сигналов из Google Sheets
    """
    global storage, notification_service
    
    try:
        logger.info("=" * 60)
        logger.info("🚀 AWS Lambda - Starting signal check from Google Sheets")
        logger.info(f"⏰ Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        # 1. Загружаем конфигурацию
        config = load_config()
        logger.info("✅ Configuration loaded from environment variables")
        
        # 2. Инициализируем биржи (переиспользуем если уже есть)
        exchanges_dict = init_exchanges(config)
        
        if not exchanges_dict:
            logger.error("❌ No exchanges initialized - aborting")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'No exchanges available'})
            }
        
        # 3. Читаем сигналы из Google Sheets
        sheets_reader = SheetsReader()
        
        if not sheets_reader.test_connection():
            logger.error("❌ Failed to connect to Google Sheets")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Google Sheets connection failed'})
            }
        
        signals_data = sheets_reader.read_signals()
        logger.info(f"📊 Read {len(signals_data)} trading signals from Google Sheets")
        
        if not signals_data:
            logger.info("ℹ️  No active trading signals found")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No active signals to check'})
            }
        
        # 4. Конвертируем данные из Sheets в SignalTarget объекты
        signals = []
        for i, signal_dict in enumerate(signals_data, 1):
            try:
                # Парсим exchange
                exchange_str = signal_dict['exchange'].lower()
                if 'binance' in exchange_str:
                    exchange = ExchangeType.BINANCE
                elif 'coinbase' in exchange_str:
                    exchange = ExchangeType.COINBASE
                else:
                    exchange = ExchangeType.BINANCE
                
                # Парсим condition
                condition_str = signal_dict['condition'].lower()
                if 'above' in condition_str or '>' in condition_str:
                    condition = SignalCondition.ABOVE
                elif 'below' in condition_str or '<' in condition_str:
                    condition = SignalCondition.BELOW
                else:
                    logger.warning(f"⚠️  Signal {i}: Unknown condition '{condition_str}' - skipping")
                    continue
                
                symbol = signal_dict['symbol'].upper()
                target_price = float(signal_dict['target_price'])
                signal_name = f"{exchange.value.upper()} {symbol} {condition.value} ${target_price}"
                
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
            logger.warning("⚠️  No valid trading signals to check")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No valid signals found'})
            }
        
        # 5. Инициализируем storage (DynamoDB)
        if storage is None:
            table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-signals')
            storage = DynamoDBStorage(table_name=table_name)
            logger.info(f"✅ DynamoDB storage initialized: {table_name}")
        
        # 6. Инициализируем сервисы
        price_checker = PriceChecker(exchanges_dict)
        
        if notification_service is None:
            notification_service = NotificationService(
                config=config.notifications,
                storage=storage
            )
            await notification_service.initialize()
            logger.info("✅ Notification service initialized")
        
        # Сохраняем сигналы в DynamoDB
        for signal in signals:
            await storage.save_signal(signal)
            if signal.user_id:
                await storage.save_user_data(signal.user_id, {
                    "pushover_key": signal.user_id
                })
        
        # 7. Создаем SignalManager и запускаем проверку
        signal_manager = SignalManager(
            price_checker=price_checker,
            notification_service=notification_service,
            storage_service=storage
        )
        
        # 8. Проверяем все сигналы
        await signal_manager.check_all_signals()
        
        logger.info("=" * 60)
        logger.info("✅ Signal check completed successfully")
        logger.info("=" * 60)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Signal check completed',
                'signals_checked': len(signals),
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Error in check_signals_from_sheets: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }


def lambda_handler(event, context):
    """
    AWS Lambda entry point
    Вызывается CloudWatch Events по расписанию
    
    Args:
        event: EventBridge event (содержит информацию о триггере)
        context: Lambda context (request_id, timeout, etc)
    
    Returns:
        dict: Response с statusCode и body
    """
    logger.info(f"🚀 Lambda invoked. Request ID: {context.request_id}")
    logger.info(f"📦 Event: {json.dumps(event)}")
    logger.info(f"⏱️  Time remaining: {context.get_remaining_time_in_millis()} ms")
    
    # Запускаем асинхронную проверку
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(check_signals_from_sheets())
    
    logger.info(f"✅ Lambda execution completed. Result: {result['statusCode']}")
    
    return result
"""
AWS Lambda WORKER - Fan-Out Architecture  
Обрабатывает один сигнал из SQS очереди
Запускается автоматически при появлении сообщения в SQS
"""
import os
import json
import asyncio
import logging
from datetime import datetime

# Добавляем src в path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.signal import SignalTarget, ExchangeType, SignalCondition
from services.price_checker import PriceChecker
from services.notification import NotificationService
from storage.dynamodb_storage import DynamoDBStorage
from exchanges.binance import BinanceExchange
from exchanges.coinbase import CoinbaseExchange
from utils.config import load_config

# Инициализация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные для warm start optimization
exchanges = {}
storage = None
notification_service = None


def init_exchanges(config):
    """Инициализация бирж (переиспользуется между вызовами)"""
    global exchanges
    
    if exchanges:
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


async def process_signal(signal_dict: dict):
    """
    Обрабатывает один сигнал:
    1. Парсит данные из SQS
    2. Получает текущую цену
    3. Проверяет условие
    4. Отправляет уведомление если сработал
    """
    global storage, notification_service
    
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Инициализируем биржи
        exchanges_dict = init_exchanges(config)
        
        if not exchanges_dict:
            logger.error("❌ No exchanges available")
            return False
        
        # Парсим сигнал из SQS сообщения
        exchange_str = signal_dict['exchange'].lower()
        if 'binance' in exchange_str:
            exchange = ExchangeType.BINANCE
        elif 'coinbase' in exchange_str:
            exchange = ExchangeType.COINBASE
        else:
            exchange = ExchangeType.BINANCE
        
        condition_str = signal_dict['condition'].lower()
        if 'above' in condition_str or '>' in condition_str:
            condition = SignalCondition.ABOVE
        elif 'below' in condition_str or '<' in condition_str:
            condition = SignalCondition.BELOW
        else:
            logger.warning(f"⚠️  Unknown condition '{condition_str}'")
            return False
        
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
        
        logger.info(f"📊 Processing signal: {signal.name}")
        
        # Инициализируем storage (DynamoDB)
        if storage is None:
            table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-signals')
            storage = DynamoDBStorage(table_name=table_name)
        
        # Сохраняем сигнал в DynamoDB
        await storage.save_signal(signal)
        if signal.user_id:
            await storage.save_user_data(signal.user_id, {
                "pushover_key": signal.user_id
            })
        
        # Инициализируем сервисы
        price_checker = PriceChecker(exchanges_dict)
        
        if notification_service is None:
            notification_service = NotificationService(
                config=config.notifications,
                storage=storage
            )
            await notification_service.initialize()
        
        # Получаем текущую цену
        price_data = await price_checker.get_price(exchange, symbol)
        
        if not price_data:
            logger.warning(f"⚠️  Could not get price for {symbol}")
            return False
        
        current_price = price_data.price
        logger.info(f"💰 Current price: ${current_price:,.4f}")
        
        # Проверяем условие
        triggered = False
        if signal.condition == SignalCondition.ABOVE and current_price > signal.target_price:
            triggered = True
        elif signal.condition == SignalCondition.BELOW and current_price < signal.target_price:
            triggered = True
        
        if triggered:
            logger.info(f"🚨 Signal TRIGGERED for {symbol} at ${current_price:,.4f}")
            
            # Создаем SignalResult
            from models.signal import SignalResult
            result = SignalResult(
                signal=signal,
                current_price=current_price,
                triggered=True
            )
            
            # Отправляем уведомление
            await notification_service.send_alert_notification(result)
            
            # Обновляем сигнал (деактивируем после срабатывания)
            signal.triggered_count += 1
            signal.last_triggered_at = datetime.now()
            signal.active = False
            await storage.update_signal(signal)
            
            logger.info(f"✅ Signal processed and deactivated")
            return True
        else:
            logger.info(f"ℹ️  Signal not triggered (price: ${current_price:,.4f}, target: ${signal.target_price:,.4f})")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error processing signal: {e}", exc_info=True)
        return False


def lambda_handler(event, context):
    """
    Lambda Worker - обрабатывает одно сообщение из SQS
    
    Args:
        event: SQS event с одним или несколькими сообщениями
        context: Lambda context
    """
    logger.info(f"🚀 Lambda WORKER invoked. Request ID: {context.request_id}")
    
    # SQS может отправить несколько сообщений в одном event
    # Но обычно это одно сообщение на Lambda
    records = event.get('Records', [])
    logger.info(f"📦 Processing {len(records)} messages")
    
    results = []
    
    for record in records:
        try:
            # Парсим сообщение из SQS
            message_body = json.loads(record['body'])
            logger.info(f"📨 Message: {message_body}")
            
            # Обрабатываем сигнал асинхронно
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(process_signal(message_body))
            
            results.append({
                'messageId': record['messageId'],
                'success': success
            })
            
        except Exception as e:
            logger.error(f"❌ Failed to process message: {e}", exc_info=True)
            results.append({
                'messageId': record.get('messageId', 'unknown'),
                'success': False,
                'error': str(e)
            })
    
    logger.info(f"✅ Lambda WORKER completed. Processed {len(results)} messages")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Messages processed',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    }

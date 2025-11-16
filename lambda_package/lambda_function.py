"""
AWS Lambda handler для проверки сигналов из Google Sheets
Запускается по расписанию CloudWatch Events каждый час
"""
import os
import sys
import json
import asyncio
import logging
import csv
import io
from datetime import datetime
import boto3

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.signal import SignalTarget, ExchangeType, SignalCondition
from services.sheets_reader import SheetsReader
from services.price_checker import PriceChecker
from services.notification import NotificationService
from storage.dynamodb_storage import DynamoDBStorage
from exchanges.binance import BinanceExchange
from exchanges.bybit import BybitExchange
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


async def init_exchanges(config):
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
            await binance.connect()
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
            await coinbase.connect()
            exchanges[ExchangeType.COINBASE] = coinbase
            logger.info("✅ Coinbase initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Coinbase: {e}")
    
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
    
    return exchanges


async def save_results_to_csv_s3(results: list, bucket: str = "trading-signals-lambda-eu", region: str = "eu-west-1"):
    """
    Сохраняет результаты проверки в CSV файл на S3
    1 файл в день: history/YYYY-MM-DD.csv
    Lambda дописывает (append) в конец файла
    """
    if not results:
        logger.debug("ℹ️  No results to save to CSV")
        return
    
    try:
        s3_client = boto3.client('s3', region_name=region)
        
        # Имя файла: history/2025-11-14.csv
        date_str = datetime.now().strftime("%Y-%m-%d")
        s3_key = f"history/{date_str}.csv"
        
        # Проверяем существует ли файл
        existing_content = ""
        file_exists = False
        try:
            response = await asyncio.to_thread(
                s3_client.get_object,
                Bucket=bucket,
                Key=s3_key
            )
            existing_content = response['Body'].read().decode('utf-8')
            file_exists = True
            logger.debug(f"📝 Found existing CSV file: s3://{bucket}/{s3_key}")
        except s3_client.exceptions.NoSuchKey:
            logger.debug(f"✨ Creating new CSV file: s3://{bucket}/{s3_key}")
        
        # Создаем CSV в памяти
        output = io.StringIO()
        
        # Если файл уже есть - добавляем старое содержимое
        if file_exists:
            output.write(existing_content)
            # Убираем последний \n если есть
            if existing_content and not existing_content.endswith('\n'):
                output.write('\n')
        
        # CSV writer
        writer = csv.writer(output)
        
        # Заголовок (только для нового файла)
        if not file_exists:
            writer.writerow([
                'timestamp',
                'signal_id',
                'signal_name',
                'exchange',
                'symbol',
                'condition',
                'target_price',
                'current_price',
                'triggered',
                'user_id'
            ])
        
        # Добавляем новые результаты
        timestamp = datetime.now().isoformat()
        for result in results:
            writer.writerow([
                timestamp,
                result.signal.id,
                result.signal.name,
                result.signal.exchange.value if result.signal.exchange else 'any',
                result.signal.symbol,
                result.signal.condition.value,
                f"{result.signal.target_price:.8f}",
                f"{result.current_price:.8f}",
                str(result.triggered).upper(),
                result.signal.user_id or ''
            ])
        
        # Загружаем на S3
        csv_content = output.getvalue()
        await asyncio.to_thread(
            s3_client.put_object,
            Bucket=bucket,
            Key=s3_key,
            Body=csv_content.encode('utf-8'),
            ContentType='text/csv'
        )
        
        logger.info(f"📊 Saved {len(results)} check results to s3://{bucket}/{s3_key}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save results to CSV on S3: {e}", exc_info=True)


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
        exchanges_dict = await init_exchanges(config)
        
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
        # Определяем дефолтную биржу (первая доступная)
        default_exchange = list(exchanges_dict.keys())[0] if exchanges_dict else ExchangeType.BYBIT
        logger.info(f"🔧 Default exchange (if not specified): {default_exchange.value}")
        
        for i, signal_dict in enumerate(signals_data, 1):
            try:
                # Парсим exchange (опционально)
                exchange = default_exchange
                if 'exchange' in signal_dict and signal_dict['exchange']:
                    exchange_str = signal_dict['exchange'].lower()
                    if 'binance' in exchange_str:
                        exchange = ExchangeType.BINANCE
                    elif 'bybit' in exchange_str:
                        exchange = ExchangeType.BYBIT
                    elif 'coinbase' in exchange_str:
                        exchange = ExchangeType.COINBASE
                
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
                
                # Генерируем уникальный ID (для upsert логики)
                signal.id = signal.generate_id()
                
                signals.append(signal)
                logger.info(f"📊 Signal {i}: {exchange.value} {signal.symbol} {condition.value} ${signal.target_price} (ID: {signal.id[:8]}...)")
                
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
            table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-alerts')
            region = os.getenv('DYNAMODB_REGION', 'us-east-2') 
            storage = DynamoDBStorage(table_name=table_name, region=region)
            logger.info(f"✅ DynamoDB storage initialized: {table_name} in {region}")
        
        # 6. Инициализируем сервисы
        price_checker = PriceChecker(exchanges_dict)
        
        if notification_service is None:
            notification_service = NotificationService(
                config=config.notifications,
                storage=storage
            )
            await notification_service.initialize()
            logger.info("✅ Notification service initialized")
        
        # Сохраняем или обновляем сигналы в DynamoDB (UPSERT)
        logger.info(f"💾 Saving {len(signals)} signals to DynamoDB (upsert logic)...")
        for signal in signals:
            success = await storage.save_signal(signal)
            if not success:
                logger.error(f"❌ Failed to save signal {signal.name}")
            if signal.user_id:
                await storage.save_user_data(signal.user_id, {
                    "pushover_key": signal.user_id
                })
        logger.info("✅ All signals saved/updated")
        
        # 7. Создаем SignalManager и запускаем проверку
        signal_manager = SignalManager(
            price_checker=price_checker,
            notification_service=notification_service,
            storage_service=storage
        )
        
        # 8. Проверяем все сигналы (загружаются из DynamoDB)
        check_results = await signal_manager.check_all_signals()
        
        # 9. Сохраняем результаты в CSV на S3 (для статистики)
        await save_results_to_csv_s3(
            results=check_results,
            bucket=os.getenv('S3_HISTORY_BUCKET', 'trading-signals-lambda-eu'),
            region=os.getenv('AWS_REGION', 'eu-west-1')
        )
        
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
    # ========================================
    # 🧪 ДИАГНОСТИКА: v10 - FIXED BROKEN CODE STRUCTURE!
    # ========================================
    logger.info("="*80)
    logger.info("🧪 v10: UPSERT + CSV + FIXED CODE (init_exchanges was broken!)")
    logger.info("="*80)
    
    logger.info(f"🚀 Lambda invoked. Request ID: {context.aws_request_id}")
    logger.info(f"📦 Event: {json.dumps(event)}")
    logger.info(f"⏱️  Time remaining: {context.get_remaining_time_in_millis()} ms")
    
    # Запускаем асинхронную проверку
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(check_signals_from_sheets())
    
    logger.info(f"✅ Lambda execution completed. Result: {result['statusCode']}")
    
    return result
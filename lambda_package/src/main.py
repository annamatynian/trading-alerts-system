import sys
import os
import asyncio
import aiohttp
import logging
from aiohttp import web

# --- Настройка путей ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(PROJECT_ROOT, 'src')
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

# --- Импорты ---
from storage.json_storage import JSONStorage
from utils.config import load_config
from utils.logger import setup_logging
from services.sheets_reader import SheetsReader
from services.price_checker import PriceChecker
from services.notification import NotificationService
from services.signal_manager import SignalManager
from models.signal import SignalTarget, ExchangeType, SignalCondition
from exchanges.binance import BinanceExchange
from exchanges.coinbase import CoinbaseExchange

logger = logging.getLogger(__name__)

async def check_signals_background(config, storage):
    """
    Фоновая задача для проверки торговых сигналов из Google Sheets
    Запускается каждый час
    Когда цена достигает цели - отправляет алерт (push-уведомление)
    """
    CHECK_INTERVAL = 3600  # 1 час в секундах
    
    exchanges = {}
    notification_service = None
    
    # Отключаем шумные логгеры
    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    
    # <--- НАЧАЛО ИСПРАВЛЕНИЯ ("БЕССМЕРТНЫЙ" ЦИКЛ) ---
    while True:
        try:
            # Этот try-блок теперь отвечает за сам цикл работы
            logger.info("=" * 60)
            # У вас здесь была "сигнальная" строка, давайте ее оставим
            logger.info("🚀 VERSION 4.0-FIXED-TERMINOLOGY - Starting background signal check")
            # logger.info("🔍 Starting background alert check from Google Sheets") # Эта строка дублируется
            logger.info("=" * 60)
            
            # 1. Инициализируем биржи (только если ещё не инициализированы)
            if not exchanges:
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
            
            if not exchanges:
                logger.error("❌ No exchanges initialized - skipping check")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            # 2. Читаем сигналы из Google Sheets
            sheets_reader = SheetsReader()
            
            if not sheets_reader.test_connection():
                logger.error("❌ Failed to connect to Google Sheets - skipping check")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            signals_data = sheets_reader.read_signals()
            logger.info(f"📊 Read {len(signals_data)} trading signals from Google Sheets")
            
            if not signals_data:
                logger.info("ℹ️  No active trading signals found")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            # 3. Конвертируем данные из Sheets в SignalTarget объекты
            signals = []
            for i, signal_dict in enumerate(signals_data, 1):
                try:
                    # ... (весь ваш код парсинга алертов... без изменений) ...
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
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            # 4. Инициализируем сервисы
            price_checker = PriceChecker(exchanges)
            
            if notification_service is None:
                notification_service = NotificationService(
                    config=config.notifications,
                    storage=storage
                )
                await notification_service.initialize()
            
            for signal in signals:
                await storage.save_signal(signal)
                if signal.user_id:
                    await storage.save_user_data(signal.user_id, {
                        "pushover_key": signal.user_id
                    })
            
            signal_manager = SignalManager(
                price_checker=price_checker,
                notification_service=notification_service,
                storage_service=storage
            )
            
            # 5. Запускаем проверку сигналов
            await signal_manager.check_all_signals()
            
            logger.info("=" * 60)
            logger.info(f"✅ Signal check completed. Next check in {CHECK_INTERVAL // 60} minutes")
            logger.info("=" * 60)
            
        except BaseException as e:
            # ЭТОТ БЛОК ПОЙМАЕТ АБСОЛЮТНО ВСЕ (Exception, TimeoutError, SystemExit, и т.д.)
            # Это гарантирует, что цикл 'while True:' НИКОГДА не умрет.
            logger.critical(f"❌ CRITICAL UNHANDLED ERROR in background task: {e}", exc_info=True)
        
        # Ждём до следующей проверки (этот код теперь ВНЕ try-блока)
        logger.info(f"--- Waiting {CHECK_INTERVAL} seconds for next cycle ---")
        await asyncio.sleep(CHECK_INTERVAL)
    # <--- КОНЕЦ ИСПРАВЛЕНИЯ ---
    
async def health_check(request):
    """Health check endpoint для Leapcell"""
    logger.info("✅ HEALTHCHECK ВЕРСИИ 4.0-FIXED-TERMINOLOGY")
    return web.Response(text="OK", status=200)

async def test_sheets(request):
    """Тестовый endpoint для проверки Google Sheets"""
    try:
        reader = SheetsReader()
        
        # Тест подключения
        if not reader.test_connection():
            return web.json_response({"error": "Failed to connect to Google Sheets"}, status=500)
        
        # Читаем сигналы
        signals = reader.read_signals()
        
        return web.json_response({
            "success": True,
            "signals_count": len(signals),
            "signals": signals
        })
    except Exception as e:
        logging.error(f"Error in test_sheets: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)
    

async def check_my_ip(request):
    """Тестовый endpoint для проверки исходящего IP сервера"""
    try:
        async with aiohttp.ClientSession() as session:
            # Используем сервис, который вернет IP
            async with session.get('https://api.ipify.org') as response:
                ip = await response.text()
                logger.info(f"Checking Egress IP. My IP is: {ip}")
                return web.Response(text=f"My Egress IP is: {ip}", status=200)
    except Exception as e:
        logger.error(f"Error checking IP: {e}")
        return web.Response(text=f"Error checking IP: {e}", status=500)


async def start_http_server(storage, config):
    """Запускает простой HTTP сервер для Health Checks и фоновую проверку сигналов"""
    app = web.Application()
    
    # Health check endpoints
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/kaithhealthcheck', health_check)
    app.router.add_get('/kaithheathcheck', health_check)
    app.router.add_get('/test_sheets', test_sheets)
    app.router.add_get('/myip', check_my_ip)
    
    # Запускаем фоновую задачу для проверки сигналов
    asyncio.create_task(check_signals_background(config, storage))
    logger.info("🚀 Background signal checker started")

    # Запускаем сервер на порту 8080
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("✅ HTTP server started on port 8080")
    
    # Держим сервер запущенным
    while True:
        await asyncio.sleep(3600)

async def main():
    """Главная функция"""
    setup_logging(logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("🚀 ЗАПУСК ВЕРСИИ 4.0-FIXED-TERMINOLOGY")

    try:
        # 1. Загружаем конфигурацию
        env_path = os.path.join(PROJECT_ROOT, '.env')
        config = load_config(env_path=env_path)
        logger.info("✅ Configuration loaded successfully")

        # 2. Инициализируем storage
        storage_path = '/tmp/signals.json'
        logger.info(f"💾 Using storage path: {storage_path}")
        storage = JSONStorage(storage_path)
        
        # 3. Запускаем HTTP сервер + фоновую проверку сигналов
        logger.info("🚀 Starting signal system without Telegram bot...")
        logger.info("📊 Using Google Sheets for signal management")
        logger.info("📨 Using Pushover for notifications")
        await start_http_server(storage, config)

    except (KeyboardInterrupt, SystemExit):
        logger.info("System stopped by user")
    except Exception as e:
        logger.critical(f"Critical error in main: {e}", exc_info=True)
    finally:
        logger.info("Shutting down...")
        logger.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())

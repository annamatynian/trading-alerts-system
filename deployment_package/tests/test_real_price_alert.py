"""
Тест с реальной ценой BTC
Создаёт сигнал близко к текущей цене и ждёт триггера

Использование:
    python test_real_price_alert.py

Что делает:
1. Получает текущую цену BTC
2. Создаёт сигнал чуть выше/ниже текущей цены
3. Запускает проверку каждые 10 секунд
4. Отправляет Pushover когда цена достигает target
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.signal import SignalTarget, ExchangeType, SignalCondition
from exchanges.binance import BinanceExchange
from services.price_checker import PriceChecker
from services.notification import NotificationService
from services.signal_manager import SignalManager
from storage.json_storage import JSONStorage
from utils.config import NotificationConfig

# Загружаем .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_real_price_alert():
    """Тест с реальной ценой"""

    print("=" * 80)
    print("🧪 REAL PRICE ALERT TEST")
    print("=" * 80)
    print()

    # 1. Проверяем credentials
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_user_key = os.getenv('PUSHOVER_USER_KEY')

    if not pushover_token or not pushover_user_key:
        print("❌ ERROR: Missing Pushover credentials")
        return False

    print("✅ Pushover credentials found")
    print()

    # 2. Инициализируем Binance
    print("🔌 Connecting to Binance...")
    binance = BinanceExchange(api_key=None, api_secret=None)
    await binance.connect()
    exchanges = {ExchangeType.BINANCE: binance}
    print("   ✅ Connected")
    print()

    # 3. Получаем текущую цену BTC
    print("📊 Getting current BTC price...")
    price_checker = PriceChecker(exchanges)
    current_price_data = await price_checker.get_price(ExchangeType.BINANCE, "BTC/USDT")

    if not current_price_data:
        print("❌ Failed to get BTC price")
        return False

    current_price = current_price_data.price
    print(f"   Current BTC Price: ${current_price:,.2f}")
    print()

    # 4. Создаём тестовый сигнал
    # Вариант A: Чуть выше текущей цены
    target_price = current_price + 50  # +$50 выше
    condition = SignalCondition.ABOVE

    # Вариант B: Чуть ниже текущей цены (раскомментируйте для теста)
    # target_price = current_price - 50  # -$50 ниже
    # condition = SignalCondition.BELOW

    print("📝 Creating test signal...")
    print(f"   Symbol: BTCUSDT")
    print(f"   Current Price: ${current_price:,.2f}")
    print(f"   Target Price: ${target_price:,.2f}")
    print(f"   Condition: {condition.value}")
    print(f"   Difference: ${abs(target_price - current_price):,.2f}")
    print()

    test_signal = SignalTarget(
        signal_id="test-real-price-001",
        name=f"TEST BTCUSDT {condition.value} {target_price}",
        exchange=ExchangeType.BINANCE,
        symbol="BTC/USDT",
        condition=condition,
        target_price=target_price,
        user_id=pushover_user_key,
        active=True
    )

    # 5. Инициализируем storage
    print("💾 Initializing storage...")
    storage_path = '/tmp/test_real_price_signals.json'
    storage = JSONStorage(storage_path)
    await storage.save_signal(test_signal)
    await storage.save_user_data(pushover_user_key, {
        "pushover_key": pushover_user_key
    })
    print("   ✅ Signal saved")
    print()

    # 6. Инициализируем Notification Service
    print("📨 Initializing Notification Service...")
    notification_config = NotificationConfig(
        pushover_enabled=True,
        pushover_api_token=pushover_token
    )
    notification_service = NotificationService(
        config=notification_config,
        storage=storage
    )
    await notification_service.initialize()
    print("   ✅ Notification Service ready")
    print()

    # 7. Инициализируем Signal Manager
    signal_manager = SignalManager(
        price_checker=price_checker,
        notification_service=notification_service,
        storage_service=storage
    )

    # 8. Запускаем проверку в цикле
    print("=" * 80)
    print("🔄 Starting price monitoring...")
    print("=" * 80)
    print(f"⏱️  Will check every 10 seconds")
    print(f"🎯 Waiting for price to reach ${target_price:,.2f}")
    print(f"📱 Notification will be sent when triggered")
    print()
    print("Press Ctrl+C to stop")
    print()

    check_count = 0
    try:
        while True:
            check_count += 1
            print(f"--- Check #{check_count} ---")

            # Проверяем все сигналы
            await signal_manager.check_all_signals()

            # Получаем обновлённый сигнал
            updated_signal = await storage.get_signal(test_signal.signal_id)

            if updated_signal and updated_signal.triggered_count > 0:
                print()
                print("=" * 80)
                print("🎉 SIGNAL TRIGGERED!")
                print("=" * 80)
                print(f"✅ Notification sent!")
                print(f"📱 Check your Pushover app")
                print()
                break

            # Ждём 10 секунд
            await asyncio.sleep(10)

    except KeyboardInterrupt:
        print()
        print("⏸️  Stopped by user")
        print()

    finally:
        # Закрываем сервисы
        await notification_service.close()
        print("✅ Test completed")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_real_price_alert())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏸️  Interrupted by user")
        sys.exit(0)

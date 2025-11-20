"""
Полный тест Price Alert → Pushover flow
Использует mock цены для симуляции триггера

Использование:
    python test_full_flow.py

Что тестируется:
1. Создание сигнала
2. Mock проверка цены (симуляция достижения target_price)
3. Отправка Pushover уведомления
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.signal import SignalTarget, ExchangeType, SignalCondition, SignalResult
from models.price import PriceData
from services.notification import NotificationService
from storage.json_storage import JSONStorage
from utils.config import load_config, NotificationConfig

# Загружаем .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_full_flow():
    """Тестирует полный flow от создания сигнала до отправки уведомления"""

    print("=" * 80)
    print("🧪 FULL FLOW TEST: Price Alert → Pushover Notification")
    print("=" * 80)
    print()

    # 1. Проверяем наличие credentials
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_user_key = os.getenv('PUSHOVER_USER_KEY')

    if not pushover_token or not pushover_user_key:
        print("❌ ERROR: Missing Pushover credentials in .env")
        print("   Required:")
        print("   - PUSHOVER_APP_TOKEN")
        print("   - PUSHOVER_USER_KEY")
        return False

    print("✅ Pushover credentials found")
    print()

    # 2. Создаём тестовый сигнал
    print("📊 Creating test signal...")
    test_signal = SignalTarget(
        signal_id="test-signal-001",
        name="TEST BTCUSDT > 95000",
        exchange=ExchangeType.BINANCE,
        symbol="BTCUSDT",
        condition=SignalCondition.ABOVE,
        target_price=95000.0,
        user_id=pushover_user_key,  # user_id используется как pushover_key
        active=True
    )
    print(f"   Signal: {test_signal.name}")
    print(f"   Exchange: {test_signal.exchange.value}")
    print(f"   Symbol: {test_signal.symbol}")
    print(f"   Condition: {test_signal.condition.value}")
    print(f"   Target Price: ${test_signal.target_price:,.2f}")
    print()

    # 3. Инициализируем storage
    print("💾 Initializing storage...")
    storage_path = '/tmp/test_signals.json'
    storage = JSONStorage(storage_path)

    # Сохраняем сигнал
    await storage.save_signal(test_signal)

    # Сохраняем данные пользователя
    await storage.save_user_data(pushover_user_key, {
        "pushover_key": pushover_user_key
    })
    print("   ✅ Storage initialized")
    print()

    # 4. Инициализируем Notification Service
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
    print("   ✅ Notification Service initialized")
    print()

    # 5. MOCK: Симулируем достижение цены
    print("🎯 MOCK: Simulating price trigger...")
    print(f"   Current Price: $95,234.50 (MOCKED)")
    print(f"   Target Price: ${test_signal.target_price:,.2f}")
    print(f"   Condition: {test_signal.condition.value}")
    print()

    # Создаём mock PriceData
    mock_price_data = PriceData(
        symbol="BTCUSDT",
        price=95234.50,  # Цена выше target_price
        timestamp=1700000000
    )

    # Создаём SignalResult (симулируем триггер)
    signal_result = SignalResult(
        signal=test_signal,
        current_price=mock_price_data.price,
        is_triggered=True  # Условие выполнено
    )

    print(f"✅ Signal triggered! Current price ${mock_price_data.price:,.2f} is ABOVE target ${test_signal.target_price:,.2f}")
    print()

    # 6. Отправляем уведомление
    print("📤 Sending Pushover notification...")
    print()

    try:
        await notification_service.send_alert_notification(signal_result)
        print()
        print("=" * 80)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("📱 Check your Pushover app - you should receive an EMERGENCY notification")
        print("   (Priority 2 - requires acknowledgment)")
        print()

        # Закрываем notification service
        await notification_service.close()

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED!")
        print("=" * 80)
        print(f"Error: {e}")
        print()

        # Закрываем notification service
        await notification_service.close()

        return False


if __name__ == "__main__":
    success = asyncio.run(test_full_flow())
    sys.exit(0 if success else 1)

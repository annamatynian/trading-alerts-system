"""
ЁЯЪА Скрипт для генерации тестовых сигналов для пользователей anna и tomas

Создаёт несколько разнообразных тестовых сигналов в DynamoDB
"""
import os
import sys
import asyncio
from datetime import datetime

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.signal import SignalTarget, ExchangeType, SignalCondition
from storage.dynamodb_storage import DynamoDBStorage
from utils.logger import setup_logging
import logging

# Инициализация
setup_logging()
logger = logging.getLogger(__name__)


# Тестовые данные для anna
ANNA_SIGNALS = [
    {
        "name": "Anna BTC Moon Alert",
        "exchange": ExchangeType.BINANCE,
        "symbol": "BTCUSDT",
        "condition": SignalCondition.ABOVE,
        "target_price": 95000.0,
        "user_id": "anna",
        "notes": "Bitcoin to the moon! 🚀"
    },
    {
        "name": "Anna ETH Target",
        "exchange": ExchangeType.BYBIT,
        "symbol": "ETHUSDT",
        "condition": SignalCondition.ABOVE,
        "target_price": 3500.0,
        "user_id": "anna",
        "notes": "Ethereum price target"
    },
    {
        "name": "Anna SOL Dip Alert",
        "exchange": ExchangeType.BINANCE,
        "symbol": "SOLUSDT",
        "condition": SignalCondition.BELOW,
        "target_price": 180.0,
        "user_id": "anna",
        "notes": "Buy the dip opportunity"
    },
    {
        "name": "Anna XRP Watch",
        "exchange": ExchangeType.COINBASE,
        "symbol": "XRPUSDT",
        "condition": SignalCondition.ABOVE,
        "target_price": 2.5,
        "user_id": "anna",
        "notes": "Ripple breakout alert"
    }
]

# Тестовые данные для tomas
TOMAS_SIGNALS = [
    {
        "name": "Tomas BTC Support",
        "exchange": ExchangeType.BYBIT,
        "symbol": "BTCUSDT",
        "condition": SignalCondition.BELOW,
        "target_price": 85000.0,
        "user_id": "tomas",
        "notes": "Bitcoin support level watch"
    },
    {
        "name": "Tomas ETH Sell",
        "exchange": ExchangeType.BINANCE,
        "symbol": "ETHUSDT",
        "condition": SignalCondition.ABOVE,
        "target_price": 4000.0,
        "user_id": "tomas",
        "notes": "Take profit at 4k"
    },
    {
        "name": "Tomas BNB Alert",
        "exchange": ExchangeType.BINANCE,
        "symbol": "BNBUSDT",
        "condition": SignalCondition.ABOVE,
        "target_price": 650.0,
        "user_id": "tomas",
        "notes": "Binance Coin breakout"
    },
    {
        "name": "Tomas MATIC Entry",
        "exchange": ExchangeType.COINBASE,
        "symbol": "MATICUSDT",
        "condition": SignalCondition.BELOW,
        "target_price": 0.85,
        "user_id": "tomas",
        "notes": "Good entry point for Polygon"
    },
    {
        "name": "Tomas ADA Target",
        "exchange": ExchangeType.BYBIT,
        "symbol": "ADAUSDT",
        "condition": SignalCondition.ABOVE,
        "target_price": 0.95,
        "user_id": "tomas",
        "notes": "Cardano price target"
    }
]


async def create_test_signals():
    """Создание тестовых сигналов в DynamoDB"""

    # Инициализируем DynamoDB
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-signals-eu')
    region = os.getenv('DYNAMODB_REGION', 'eu-west-1')

    print(f"\n{'='*60}")
    print(f"ЁЯЪА ГЕНЕРАЦИЯ ТЕСТОВЫХ СИГНАЛОВ")
    print(f"{'='*60}")
    print(f"DynamoDB Table: {table_name}")
    print(f"Region: {region}")
    print(f"{'='*60}\n")

    storage = DynamoDBStorage(table_name=table_name, region=region)
    logger.info(f"✅ Connected to DynamoDB: {table_name}")

    # Счетчики
    anna_count = 0
    tomas_count = 0
    total_count = 0

    # Создаём сигналы для anna
    print(f"\nЁЯСй Создание сигналов для anna...")
    print(f"{'-'*60}")

    for signal_data in ANNA_SIGNALS:
        try:
            signal = SignalTarget(**signal_data)
            signal.id = signal.generate_id()

            success = await storage.save_signal(signal)

            if success:
                anna_count += 1
                total_count += 1
                print(f"  ✅ {signal.name}")
                print(f"     └─ {signal.exchange.value} | {signal.symbol} | {signal.condition.value} ${signal.target_price}")
            else:
                print(f"  ❌ Failed: {signal.name}")

        except Exception as e:
            print(f"  ❌ Error creating signal: {e}")

    # Создаём сигналы для tomas
    print(f"\nЁЯСи Создание сигналов для tomas...")
    print(f"{'-'*60}")

    for signal_data in TOMAS_SIGNALS:
        try:
            signal = SignalTarget(**signal_data)
            signal.id = signal.generate_id()

            success = await storage.save_signal(signal)

            if success:
                tomas_count += 1
                total_count += 1
                print(f"  ✅ {signal.name}")
                print(f"     └─ {signal.exchange.value} | {signal.symbol} | {signal.condition.value} ${signal.target_price}")
            else:
                print(f"  ❌ Failed: {signal.name}")

        except Exception as e:
            print(f"  ❌ Error creating signal: {e}")

    # Итоги
    print(f"\n{'='*60}")
    print(f"ЁЯМР РЕЗУЛЬТАТЫ:")
    print(f"{'='*60}")
    print(f"  ЁЯМЛ Anna's signals: {anna_count}/{len(ANNA_SIGNALS)}")
    print(f"  ЁЯМЛ Tomas's signals: {tomas_count}/{len(TOMAS_SIGNALS)}")
    print(f"  ЁЯМН Total created: {total_count}/{len(ANNA_SIGNALS) + len(TOMAS_SIGNALS)}")
    print(f"{'='*60}\n")

    # Проверяем что сигналы сохранены
    print("ЁЯФ Проверка сохранённых сигналов...")
    print(f"{'-'*60}")

    all_signals = await storage.get_all_signals()

    anna_signals_db = [s for s in all_signals if s.user_id == "anna"]
    tomas_signals_db = [s for s in all_signals if s.user_id == "tomas"]

    print(f"  ЁЯСй Anna's signals in DB: {len(anna_signals_db)}")
    print(f"  ЁЯСи Tomas's signals in DB: {len(tomas_signals_db)}")
    print(f"  ЁЯМН Total signals in DB: {len(all_signals)}")
    print(f"{'='*60}\n")

    # Инструкции по тестированию
    print("ЁЯМР ИНСТРУКЦИИ ПО ТЕСТИРОВАНИЮ:")
    print(f"{'-'*60}")
    print("1. Откройте Gradio интерфейс: http://localhost:7860")
    print("2. Перейдите в 'ЁЯУи View Signals'")
    print("3. Попробуйте фильтры:")
    print("   • Оставьте 'Filter by User ID' пустым → Нажмите 'ЁЯМД Refresh All'")
    print(f"     (должно быть {len(all_signals)} сигналов)")
    print("   • Введите 'anna' → Нажмите 'ЁЯМР Filter'")
    print(f"     (должно быть {len(anna_signals_db)} сигналов)")
    print("   • Введите 'tomas' → Нажмите 'ЁЯМР Filter'")
    print(f"     (должно быть {len(tomas_signals_db)} сигналов)")
    print(f"{'='*60}\n")

    print("✅ Тестовые данные успешно созданы!\n")


if __name__ == "__main__":
    # Пытаемся загрузить .env если он есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass

    # Запускаем создание тестовых сигналов
    # AWS credentials будут взяты из окружения, .env или AWS CLI config
    try:
        asyncio.run(create_test_signals())
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nПроверьте:")
        print("  1. AWS credentials настроены (через .env, AWS CLI или переменные окружения)")
        print("  2. DynamoDB table существует")
        print("  3. У вас есть доступ к таблице")
        sys.exit(1)

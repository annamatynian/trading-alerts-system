"""
Hugging Face Spaces Entry Point
Запускает Gradio UI + Price Checker в фоновом потоке
"""

import os
import sys
import asyncio
import threading
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import after path setup
from app_with_auth import create_gradio_interface
from src.main import check_signals_background
from utils.config import load_config
from storage.dynamodb_storage import DynamoDBStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_background_price_checker():
    """
    Запускает price checker в отдельном asyncio loop
    (работает в отдельном потоке)
    """
    logger.info("🚀 Starting background price checker thread...")

    # Создаём новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Загружаем конфигурацию
        config = load_config()

        # Инициализируем DynamoDB
        table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-alerts')
        region = os.getenv('DYNAMODB_REGION', 'eu-west-1')
        storage = DynamoDBStorage(table_name=table_name, region=region)

        logger.info("✅ Background storage initialized")

        # Запускаем фоновую проверку сигналов
        loop.run_until_complete(check_signals_background(config, storage))

    except Exception as e:
        logger.error(f"❌ Background price checker error: {e}", exc_info=True)
    finally:
        loop.close()


def main():
    """
    Main entry point for Hugging Face Spaces
    1. Запускает price checker в отдельном потоке
    2. Запускает Gradio UI в главном потоке
    """

    logger.info("=" * 80)
    logger.info("🚀 Starting Trading Alerts System on Hugging Face Spaces")
    logger.info("=" * 80)

    # Проверяем наличие необходимых secrets
    required_secrets = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'DYNAMODB_TABLE_NAME',
        'PUSHOVER_APP_TOKEN',
        'GOOGLE_SERVICE_ACCOUNT_JSON',
        'JWT_SECRET_KEY'
    ]

    missing_secrets = [s for s in required_secrets if not os.getenv(s)]

    if missing_secrets:
        logger.error("=" * 80)
        logger.error("❌ MISSING REQUIRED SECRETS!")
        logger.error("=" * 80)
        logger.error("Please configure the following secrets in HF Spaces settings:")
        for secret in missing_secrets:
            logger.error(f"  - {secret}")
        logger.error("")
        logger.error("Go to: Settings → Repository Secrets")
        logger.error("=" * 80)

        # Возвращаем простой Gradio интерфейс с ошибкой
        import gradio as gr

        def error_message():
            return f"""
# ❌ Configuration Error

Missing required secrets: {', '.join(missing_secrets)}

Please configure secrets in **Settings → Repository Secrets**
"""

        demo = gr.Interface(
            fn=lambda: error_message(),
            inputs=[],
            outputs=gr.Markdown(),
            title="Trading Alerts System - Configuration Error"
        )
        demo.launch()
        return

    logger.info("✅ All required secrets found")

    # 1. Запускаем price checker в отдельном потоке (daemon)
    price_checker_thread = threading.Thread(
        target=run_background_price_checker,
        daemon=True,  # Поток закроется когда main поток завершится
        name="PriceCheckerThread"
    )
    price_checker_thread.start()
    logger.info("✅ Background price checker thread started")

    # 2. Создаём и запускаем Gradio интерфейс
    logger.info("🎨 Creating Gradio interface...")
    demo = create_gradio_interface()

    # Запускаем Gradio (блокирующий вызов)
    logger.info("🚀 Launching Gradio UI...")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,  # Стандартный порт для HF Spaces
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()

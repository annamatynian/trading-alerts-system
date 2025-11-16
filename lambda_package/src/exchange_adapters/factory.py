"""
Этот модуль отвечает за создание экземпляров адаптеров для всех бирж,
указанных в конфигурации.
"""
import logging
from typing import Dict

from utils.config import ExchangeConfig
from models.signal import ExchangeType
from exchanges.base import ExchangeBase
from exchanges.bybit import BybitExchange
from exchanges.binance import BinanceExchange

# Словарь, который сопоставляет тип биржи с ее классом-адаптером
ADAPTER_MAP = {
    ExchangeType.BYBIT: BybitExchange,
    ExchangeType.BINANCE: BinanceExchange,
    # Добавьте сюда другие биржи, когда реализуете их
}

logger = logging.getLogger(__name__)

async def create_exchange_adapters(
    exchanges_config: Dict[ExchangeType, ExchangeConfig]
) -> Dict[ExchangeType, ExchangeBase]:
    """
    Создает и инициализирует адаптеры для всех включенных в конфиге бирж.
    """
    adapters: Dict[ExchangeType, ExchangeBase] = {}
    for exchange_type, config in exchanges_config.items():
        adapter_class = ADAPTER_MAP.get(exchange_type)
        if adapter_class:
            logger.info(f"Creating adapter for {exchange_type.value}...")
            adapter = adapter_class(
                api_key=config.api_key,
                api_secret=config.api_secret,
                testnet=config.testnet
            )
            if await adapter.connect():
                adapters[exchange_type] = adapter
                logger.info(f"Successfully connected to {exchange_type.value}")
            else:
                logger.error(f"Failed to connect to {exchange_type.value}")
        else:
            logger.warning(f"No adapter found for exchange type: {exchange_type.value}")
    
    return adapters

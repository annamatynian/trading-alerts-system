"""Настройка логирования"""
import logging
import sys


def setup_logging(level=logging.INFO):
    """
    Настраивает базовое логирование для приложения
    
    Args:
        level: Уровень логирования (по умолчанию INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Подавляем лишние логи от библиотек
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

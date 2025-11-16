#!/usr/bin/env python3
"""
Тест работы бота без API ключей (только публичные данные)
"""
import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.exchanges.bybit import BybitExchange
from src.models.alert import AlertTarget, ExchangeType, AlertCondition

async def test_without_api_keys():
    """Тест получения цен без API ключей"""
    print("🧪 Тестирование Bybit без API ключей...")
    
    # Создаем экземпляр без ключей
    exchange = BybitExchange()
    
    try:
        # Подключаемся
        connected = await exchange.connect()
        if not connected:
            print("❌ Не удалось подключиться к Bybit")
            return False
        
        print("✅ Подключение к Bybit успешно!")
        
        # Тестируем получение цены BTC
        print("🔍 Получаем цену BTCUSDT...")
        price_data = await exchange.get_price("BTCUSDT")
        
        if price_data:
            print(f"✅ Цена BTC: ${price_data.price:,.2f}")
            print(f"   Объем 24ч: {price_data.volume_24h:,.0f}")
            return True
        else:
            print("❌ Не удалось получить цену BTC")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        return False
    
    finally:
        await exchange.disconnect()

def test_alert_models():
    """Тест моделей алертов"""
    print("\n🧪 Тестирование моделей алертов...")
    
    try:
        # Создаем тестовый алерт
        alert = AlertTarget(
            name="BTC Alert Test",
            exchange=ExchangeType.BYBIT,
            symbol="BTCUSDT", 
            target_price=70000.0,
            condition=AlertCondition.ABOVE
        )
        
        print(f"✅ Алерт создан: {alert.name}")
        print(f"   Биржа: {alert.exchange}")
        print(f"   Пара: {alert.symbol}")
        print(f"   Цель: ${alert.target_price:,.0f}")
        print(f"   Условие: {alert.condition}")
        print(f"   Активен: {alert.can_trigger()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте моделей: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print("🚀 Запуск базового тестирования системы...")
    print("=" * 50)
    
    # Тест моделей
    models_ok = test_alert_models()
    
    # Тест API без ключей  
    api_ok = await test_without_api_keys()
    
    print("=" * 50)
    if models_ok and api_ok:
        print("🎉 Все тесты прошли успешно!")
        print("✅ Система готова к работе без API ключей")
    else:
        print("⚠️  Некоторые тесты не прошли")
        print("ℹ️  Проверьте зависимости: pip install -r requirements.txt")

if __name__ == "__main__":
    asyncio.run(main())

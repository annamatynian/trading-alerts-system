"""
Простой скрипт для проверки цены одного актива
Без Google Sheets, без хранилища, без сложностей
"""
import os
import requests
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# ========== НАСТРОЙКИ ==========
SYMBOL = "ALGOUSDT"              # Торговая пара
TARGET_PRICE = 0.1867            # Целевая цена
CONDITION = "above"              # "above" или "below"

PUSHOVER_TOKEN = os.getenv("TRADING_ALERT_PUSHOVER_API_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER_KEY")
# ===============================


def get_binance_price(symbol):
    """Получить текущую цену с Binance"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"❌ Ошибка получения цены: {e}")
        return None


def send_pushover_alert(title, message):
    """Отправить Pushover уведомление"""
    try:
        url = "https://api.pushover.net/1/messages.json"
        data = {
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "title": title,
            "message": message,
            "sound": "persistent",
            "priority": 2,      # Emergency priority
            "retry": 30,
            "expire": 3600
        }
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        
        if response.json().get("status") == 1:
            print("✅ Pushover уведомление отправлено!")
            return True
        else:
            print(f"❌ Ошибка Pushover: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        return False


def main():
    """Главная функция"""
    print("=" * 50)
    print(f"🔍 Проверка цены {SYMBOL}")
    print(f"🎯 Целевая цена: ${TARGET_PRICE}")
    print(f"📊 Условие: {CONDITION}")
    print("=" * 50)
    
    # Проверяем настройки
    if not PUSHOVER_TOKEN or not PUSHOVER_USER:
        print("❌ Ошибка: не настроены PUSHOVER_TOKEN или PUSHOVER_USER в .env")
        return
    
    # Получаем текущую цену
    current_price = get_binance_price(SYMBOL)
    
    if current_price is None:
        print("❌ Не удалось получить цену")
        return
    
    print(f"💰 Текущая цена: ${current_price}")
    
    # Проверяем условие
    triggered = False
    
    if CONDITION == "above" and current_price > TARGET_PRICE:
        triggered = True
        print(f"✅ АЛЕРТ! Цена ${current_price} выше целевой ${TARGET_PRICE}")
        
    elif CONDITION == "below" and current_price < TARGET_PRICE:
        triggered = True
        print(f"✅ АЛЕРТ! Цена ${current_price} ниже целевой ${TARGET_PRICE}")
        
    else:
        print(f"ℹ️  Условие не выполнено. Алерт не сработал.")
    
    # Отправляем уведомление если сработал
    if triggered:
        title = f"🚨 Алерт: {SYMBOL}"
        message = (
            f"Цена: ${current_price}\n"
            f"Целевая: ${TARGET_PRICE}\n"
            f"Условие: {CONDITION}"
        )
        send_pushover_alert(title, message)
    
    print("=" * 50)


if __name__ == "__main__":
    main()

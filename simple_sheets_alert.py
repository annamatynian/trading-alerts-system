"""
Простой скрипт для проверки сигналов из Google Sheets
Читает сигналы из таблицы, проверяет цены, отправляет Pushover уведомления
"""
import os
import requests
import json
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Загружаем .env
load_dotenv()

# ========== НАСТРОЙКИ ==========
SHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
SERVICE_ACCOUNT_JSON = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
PUSHOVER_TOKEN = os.getenv("TRADING_ALERT_PUSHOVER_API_TOKEN")

SHEET_RANGE = "Sheet1!A2:F100"  # Читаем со 2-й строки (пропускаем заголовки)
# ===============================


def get_google_sheets_data():
    """Читает данные из Google Sheets"""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            SERVICE_ACCOUNT_JSON,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=SHEET_RANGE
        ).execute()
        
        rows = result.get('values', [])
        
        # Преобразуем в список словарей
        alerts = []
        for row in rows:
            if len(row) >= 4 and row[4].lower() == 'true':  # Проверяем active=true
                alerts.append({
                    'exchange': row[0],
                    'symbol': row[1],
                    'condition': row[2],
                    'target_price': float(row[3]),
                    'pushover_user_key': row[5] if len(row) > 5 else None
                })
        
        return alerts
        
    except Exception as e:
        print(f"❌ Ошибка чтения Google Sheets: {e}")
        return []


def get_binance_price(symbol):
    """Получить текущую цену с Binance"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"❌ Ошибка получения цены {symbol}: {e}")
        return None


def get_bybit_price(symbol):
    """Получить текущую цену с Bybit"""
    try:
        url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('result') and data['result'].get('list'):
            return float(data['result']['list'][0]['lastPrice'])
        return None
        
    except Exception as e:
        print(f"❌ Ошибка получения цены {symbol} с Bybit: {e}")
        return None


def send_pushover_alert(user_key, title, message):
    """Отправить Pushover уведомление"""
    try:
        url = "https://api.pushover.net/1/messages.json"
        data = {
            "token": PUSHOVER_TOKEN,
            "user": user_key,
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
            print(f"   ✅ Pushover уведомление отправлено!")
            return True
        else:
            print(f"   ❌ Ошибка Pushover: {response.json()}")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка отправки уведомления: {e}")
        return False


def check_alert(alert):
    """Проверить один алерт"""
    exchange = alert['exchange'].lower()
    symbol = alert['symbol']
    condition = alert['condition'].lower()
    target_price = alert['target_price']
    user_key = alert['pushover_user_key']
    
    print(f"\n🔍 Проверка: {exchange.upper()} {symbol} {condition} ${target_price}")
    
    # Получаем цену с нужной биржи
    if 'binance' in exchange:
        current_price = get_binance_price(symbol)
    elif 'bybit' in exchange:
        current_price = get_bybit_price(symbol)
    else:
        print(f"   ⚠️ Неизвестная биржа: {exchange}")
        return
    
    if current_price is None:
        print(f"   ❌ Не удалось получить цену")
        return
    
    print(f"   💰 Текущая цена: ${current_price}")
    
    # Проверяем условие
    triggered = False
    
    if 'above' in condition or '>' in condition:
        if current_price > target_price:
            triggered = True
            print(f"   🚨 АЛЕРТ! Цена выше целевой!")
            
    elif 'below' in condition or '<' in condition:
        if current_price < target_price:
            triggered = True
            print(f"   🚨 АЛЕРТ! Цена ниже целевой!")
    
    # Отправляем уведомление
    if triggered and user_key:
        title = f"🚨 {exchange.upper()} {symbol}"
        message = (
            f"Текущая цена: ${current_price:.4f}\n"
            f"Целевая цена: ${target_price:.4f}\n"
            f"Условие: {condition}"
        )
        send_pushover_alert(user_key, title, message)
    elif triggered and not user_key:
        print(f"   ⚠️ Алерт сработал, но не указан pushover_user_key")
    else:
        print(f"   ℹ️ Условие не выполнено")


def main():
    """Главная функция"""
    print("=" * 60)
    print("🚀 Проверка алертов из Google Sheets")
    print("=" * 60)
    
    # Проверяем настройки
    if not PUSHOVER_TOKEN:
        print("❌ Ошибка: не настроен PUSHOVER_TOKEN в .env")
        return
    
    if not SHEET_ID:
        print("❌ Ошибка: не настроен GOOGLE_SHEETS_SPREADSHEET_ID в .env")
        return
    
    # Читаем алерты из Google Sheets
    alerts = get_google_sheets_data()
    
    if not alerts:
        print("ℹ️ Нет активных алертов в таблице")
        return
    
    print(f"📊 Найдено алертов: {len(alerts)}")
    
    # Проверяем каждый алерт
    for alert in alerts:
        check_alert(alert)
    
    print("\n" + "=" * 60)
    print("✅ Проверка завершена")
    print("=" * 60)


if __name__ == "__main__":
    main()

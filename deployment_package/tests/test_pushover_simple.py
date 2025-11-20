"""
Простой тест отправки Pushover уведомления
Использование:
    python test_pushover_simple.py

Перед запуском укажите в .env:
    PUSHOVER_APP_TOKEN=your_app_token
    PUSHOVER_USER_KEY=your_user_key
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

def test_pushover_notification():
    """Отправить тестовое уведомление через Pushover"""

    PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"

    # Получаем credentials из .env
    app_token = os.getenv('PUSHOVER_APP_TOKEN')
    user_key = os.getenv('PUSHOVER_USER_KEY')

    if not app_token:
        print("❌ ERROR: PUSHOVER_APP_TOKEN not found in .env file")
        print("   Add: PUSHOVER_APP_TOKEN=your_token_here")
        return False

    if not user_key:
        print("❌ ERROR: PUSHOVER_USER_KEY not found in .env file")
        print("   Add: PUSHOVER_USER_KEY=your_user_key_here")
        return False

    print("=" * 60)
    print("🧪 Testing Pushover Notification")
    print("=" * 60)
    print(f"App Token: {app_token[:10]}...")
    print(f"User Key: {user_key[:10]}...")
    print()

    # Создаём тестовое сообщение
    title = "🧪 Test Alert from Trading System"
    message = """This is a test notification!

Symbol: BTCUSDT
Exchange: BINANCE
Current Price: $95,234.50
Target: $95,000.00

If you received this - Pushover is working correctly! ✅"""

    # Pushover API payload
    payload = {
        "token": app_token,
        "user": user_key,
        "title": title,
        "message": message,
        "sound": "persistent",
        "priority": 2,      # Emergency priority - requires acknowledgment
        "retry": 30,        # Retry every 30 seconds
        "expire": 3600      # Expire after 1 hour
    }

    print("📤 Sending test notification...")

    try:
        response = requests.post(PUSHOVER_API_URL, data=payload)
        response_data = response.json()

        print()
        print("Response Status:", response.status_code)
        print("Response Data:", response_data)
        print()

        if response.status_code == 200 and response_data.get("status") == 1:
            print("=" * 60)
            print("✅ SUCCESS! Pushover notification sent!")
            print("=" * 60)
            print("📱 Check your Pushover app on your phone/device")
            print("   You should receive an EMERGENCY notification")
            print("   (requires acknowledgment)")
            print()
            return True
        else:
            print("=" * 60)
            print("❌ FAILED! Pushover API returned error")
            print("=" * 60)
            print("Error:", response_data.get("errors", "Unknown error"))
            print()
            return False

    except Exception as e:
        print("=" * 60)
        print("❌ EXCEPTION occurred!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        return False


if __name__ == "__main__":
    success = test_pushover_notification()
    sys.exit(0 if success else 1)

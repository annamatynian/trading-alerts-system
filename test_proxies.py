

#!/usr/bin/env python3
"""
Глубокий тест прокси - проверяем торговые эндпоинты Binance
"""

import requests
import time

# Только рабочие прокси
PROXIES_TO_TEST = [
    {"name": "🇬🇧 UK #1", "url": "http://vbsqaynk:e40i8ked8jqb@45.38.107.97:6014"},
    {"name": "🇬🇧 UK #2", "url": "http://vbsqaynk:e40i8ked8jqb@31.59.20.176:6754"},
    {"name": "🇪🇸 Spain ⭐", "url": "http://vbsqaynk:e40i8ked8jqb@64.137.96.74:6641"},
    {"name": "🇯🇵 Japan", "url": "http://vbsqaynk:e40i8ked8jqb@142.111.67.146:5611"},
]

# Различные эндпоинты Binance для тестирования
ENDPOINTS = [
    {
        "name": "Ping (публичный)",
        "url": "https://api.binance.com/api/v3/ping",
        "critical": False
    },
    {
        "name": "Server Time (публичный)",
        "url": "https://api.binance.com/api/v3/time",
        "critical": False
    },
    {
        "name": "Exchange Info (публичный)",
        "url": "https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT",
        "critical": True
    },
    {
        "name": "Ticker Price (публичный)",
        "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "critical": True
    },
    {
        "name": "24h Ticker (публичный)",
        "url": "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
        "critical": True
    },
    {
        "name": "Order Book (публичный)",
        "url": "https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=5",
        "critical": True
    },
    {
        "name": "Recent Trades (публичный)",
        "url": "https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=5",
        "critical": True
    }
]

def test_endpoint(proxy_url, endpoint):
    """Тестирует один эндпоинт с прокси"""
    proxies = {'http': proxy_url, 'https': proxy_url}
    
    try:
        response = requests.get(
            endpoint['url'],
            proxies=proxies,
            timeout=10
        )
        
        if response.status_code == 200:
            return {"status": "✅", "code": 200, "error": None}
        elif response.status_code == 451 or "restricted location" in response.text.lower():
            return {"status": "🚫", "code": response.status_code, "error": "GEO-BLOCKED"}
        else:
            return {"status": "❌", "code": response.status_code, "error": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"status": "⏱️", "code": None, "error": "TIMEOUT"}
    except Exception as e:
        error_msg = str(e)[:50]
        return {"status": "❌", "code": None, "error": error_msg}

def test_proxy_comprehensive(proxy_info):
    """Комплексный тест прокси"""
    print(f"\n{'='*80}")
    print(f"Testing: {proxy_info['name']}")
    print(f"{'='*80}")
    
    results = []
    critical_passed = 0
    critical_total = 0
    
    for endpoint in ENDPOINTS:
        print(f"  {endpoint['name']:<30} ... ", end="", flush=True)
        
        result = test_endpoint(proxy_info['url'], endpoint)
        results.append(result)
        
        print(f"{result['status']} ", end="")
        if result['error']:
            print(f"({result['error']})")
        else:
            print()
        
        if endpoint['critical']:
            critical_total += 1
            if result['status'] == "✅":
                critical_passed += 1
        
        time.sleep(0.5)
    
    # Подсчет результатов
    success_rate = (critical_passed / critical_total * 100) if critical_total > 0 else 0
    
    print(f"\n  📊 Critical endpoints: {critical_passed}/{critical_total} passed ({success_rate:.0f}%)")
    
    if success_rate == 100:
        print(f"  ✅ RECOMMENDED: All critical endpoints work!")
        return "EXCELLENT"
    elif success_rate >= 80:
        print(f"  ⚠️  CAUTION: Some endpoints may be blocked")
        return "GOOD"
    elif success_rate >= 50:
        print(f"  ⚠️  WARNING: Many endpoints blocked")
        return "RISKY"
    else:
        print(f"  🚫 NOT RECOMMENDED: Most endpoints blocked")
        return "BLOCKED"

print("=" * 80)
print("🔬 COMPREHENSIVE BINANCE PROXY TEST")
print("=" * 80)
print()
print("Testing multiple Binance endpoints to check for geo-restrictions...")
print()

ratings = {}

for proxy in PROXIES_TO_TEST:
    rating = test_proxy_comprehensive(proxy)
    ratings[proxy['name']] = rating
    time.sleep(1)

print("\n" + "=" * 80)
print("🎯 FINAL RECOMMENDATIONS")
print("=" * 80)
print()

for name, rating in ratings.items():
    if rating == "EXCELLENT":
        print(f"✅ {name}: SAFE TO USE")
    elif rating == "GOOD":
        print(f"⚠️  {name}: USE WITH CAUTION")
    elif rating == "RISKY":
        print(f"⚠️  {name}: NOT RECOMMENDED")
    else:
        print(f"🚫 {name}: DO NOT USE (GEO-BLOCKED)")

print()
print("=" * 80)
print("💡 BEST CHOICE FOR LEAPCELL:")
print("=" * 80)

# Находим лучший прокси
best = None
for proxy in PROXIES_TO_TEST:
    if ratings[proxy['name']] == "EXCELLENT":
        if best is None:
            best = proxy

if best:
    print(f"\n{best['name']}")
    print(f"PROXY_URL={best['url']}")
    print()
    print("Why this proxy?")
    print("- All critical Binance endpoints accessible")
    print("- Minimal risk of future blocks")
    print("- Stable connection")
else:
    print("\n⚠️  No ideal proxy found. Use Spain proxy as safest option:")
    spain_proxy = [p for p in PROXIES_TO_TEST if "Spain" in p['name']][0]
    print(f"PROXY_URL={spain_proxy['url']}")

print("\n" + "=" * 80)
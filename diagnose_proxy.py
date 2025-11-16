#!/usr/bin/env python3
"""
Диагностический скрипт для проверки прокси
"""

import requests
import socket

# Берем испанский прокси как пример
PROXY_IP = "64.137.96.74"
PROXY_PORT = "6641"
USERNAME = "vbsqaynk"
PASSWORD = "e40j8ked8jqb"

print("=" * 80)
print("🔍 PROXY DIAGNOSTICS")
print("=" * 80)
print()

# Тест 1: Проверка DNS
print(f"1️⃣ Testing DNS resolution for {PROXY_IP}...")
try:
    socket.gethostbyname(PROXY_IP)
    print(f"   ✅ DNS OK: {PROXY_IP} is reachable")
except socket.gaierror as e:
    print(f"   ❌ DNS Failed: {e}")
print()

# Тест 2: Проверка TCP подключения
print(f"2️⃣ Testing TCP connection to {PROXY_IP}:{PROXY_PORT}...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((PROXY_IP, int(PROXY_PORT)))
    sock.close()
    
    if result == 0:
        print(f"   ✅ TCP connection OK: Port {PROXY_PORT} is open")
    else:
        print(f"   ❌ TCP connection FAILED: Port {PROXY_PORT} is closed or filtered")
except Exception as e:
    print(f"   ❌ TCP test failed: {e}")
print()

# Тест 3: Попытка подключения без авторизации
print("3️⃣ Testing proxy connection WITHOUT authentication...")
try:
    proxies = {
        'http': f'http://{PROXY_IP}:{PROXY_PORT}',
        'https': f'http://{PROXY_IP}:{PROXY_PORT}'
    }
    response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
    print(f"   ✅ No auth worked! Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}")
except requests.exceptions.ProxyError as e:
    print(f"   ❌ Proxy error (expected if auth required): {str(e)[:100]}")
except Exception as e:
    print(f"   ❌ Error: {str(e)[:100]}")
print()

# Тест 4: С авторизацией Username/Password
print("4️⃣ Testing proxy connection WITH username/password authentication...")
try:
    proxies = {
        'http': f'http://{USERNAME}:{PASSWORD}@{PROXY_IP}:{PROXY_PORT}',
        'https': f'http://{USERNAME}:{PASSWORD}@{PROXY_IP}:{PROXY_PORT}'
    }
    response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
    print(f"   ✅ Auth worked! Status: {response.status_code}")
    print(f"   Your IP through proxy: {response.json().get('origin', 'unknown')}")
except requests.exceptions.ProxyError as e:
    error_msg = str(e)
    print(f"   ❌ Proxy error: {error_msg[:200]}")
    
    if "407" in error_msg:
        print(f"   💡 407 = Proxy requires authentication (credentials might be wrong)")
    elif "Connection refused" in error_msg:
        print(f"   💡 Connection refused = Proxy server is not accepting connections")
    elif "timed out" in error_msg:
        print(f"   💡 Timeout = Proxy server is not responding")
except Exception as e:
    print(f"   ❌ Error: {str(e)[:200]}")
print()

# Тест 5: Проверка через простой HTTP сайт
print("5️⃣ Testing with simple HTTP site (example.com)...")
try:
    proxies = {
        'http': f'http://{USERNAME}:{PASSWORD}@{PROXY_IP}:{PROXY_PORT}',
        'https': f'http://{USERNAME}:{PASSWORD}@{PROXY_IP}:{PROXY_PORT}'
    }
    response = requests.get('http://example.com', proxies=proxies, timeout=10)
    print(f"   ✅ HTTP request OK! Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Failed: {str(e)[:200]}")
print()

# Тест 6: Проверка HTTPS через прокси
print("6️⃣ Testing HTTPS through proxy...")
try:
    proxies = {
        'http': f'http://{USERNAME}:{PASSWORD}@{PROXY_IP}:{PROXY_PORT}',
        'https': f'http://{USERNAME}:{PASSWORD}@{PROXY_IP}:{PROXY_PORT}'
    }
    response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
    print(f"   ✅ HTTPS through proxy OK! Status: {response.status_code}")
    print(f"   Your IP: {response.json().get('origin', 'unknown')}")
except Exception as e:
    print(f"   ❌ Failed: {str(e)[:200]}")
print()

print("=" * 80)
print("📋 WEBSHARE CONFIGURATION CHECKLIST")
print("=" * 80)
print()
print("Please verify in your Webshare dashboard:")
print()
print("1. ✓ Proxy List Status:")
print("   - Are proxies shown as 'Active' or 'Working'?")
print("   - Check 'Last Checked' time - should be recent")
print()
print("2. ✓ IP Whitelist:")
print("   - Go to Webshare Dashboard → Settings")
print("   - Check if there's 'IP Whitelist' or 'Authorized IPs'")
print("   - Your current public IP might need to be whitelisted")
print()
print("3. ✓ Authentication Method:")
print("   - Confirm it's set to 'Username/Password'")
print("   - Some free plans use 'IP Authorization' instead")
print()
print("4. ✓ Proxy Type:")
print("   - Should be 'HTTP/HTTPS' proxies")
print("   - NOT 'SOCKS4' or 'SOCKS5'")
print()
print("5. ✓ Download Configuration:")
print("   - Try downloading proxy list from Webshare")
print("   - Check if format matches what we're using")
print()
print("=" * 80)
print("🔗 NEXT STEPS:")
print("=" * 80)
print()
print("If all tests failed, likely causes:")
print("1. Your IP needs to be whitelisted in Webshare settings")
print("2. Free proxy list has expired/rotated")
print("3. Webshare changed authentication method")
print()
print("Alternative solutions:")
print("1. Try downloading fresh proxy list from Webshare")
print("2. Check Webshare documentation for connection format")
print("3. Consider alternative proxy provider (see below)")
print()
print("=" * 80)
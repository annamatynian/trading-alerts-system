#!/usr/bin/env python3
"""
Тест персистентности пользователей в DynamoDB
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 80)
print("Testing User Persistence in DynamoDB")
print("=" * 80)
print()

async def test_user_persistence():
    """Тестируем сохранение и загрузку пользователей"""
    from storage.dynamodb_storage import DynamoDBStorage
    from storage.session_storage import SessionStorage
    from services.auth_service import AuthService

    # Инициализация
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-alerts')
    region = os.getenv('DYNAMODB_REGION', 'eu-west-1')

    storage = DynamoDBStorage(table_name=table_name, region=region)
    session_storage = SessionStorage(table_name=table_name, region=region)

    # Создаем AuthService С user_storage
    auth_service = AuthService(
        session_storage=session_storage,
        secret_key="test-secret-key",
        user_storage=storage
    )

    print("1. Загружаем существующих пользователей из DynamoDB...")
    await auth_service.load_users_from_storage()
    print(f"   ✅ Загружено {len(auth_service.users)} пользователей")

    # Показываем список пользователей
    if auth_service.users:
        print("\n   Существующие пользователи:")
        for username in auth_service.users.keys():
            print(f"   - {username}")
    print()

    # Тест 1: Регистрация нового пользователя
    test_username = "test_persist_user"
    test_password = "SecurePass123!"

    print(f"2. Регистрируем нового пользователя: {test_username}...")
    try:
        user_info = await auth_service.register_user(test_username, test_password)
        print(f"   ✅ Пользователь зарегистрирован: {user_info['user_id']}")
    except ValueError as e:
        if "already exists" in str(e):
            print(f"   ℹ️  Пользователь уже существует (это OK для повторного теста)")
        else:
            print(f"   ❌ Ошибка регистрации: {e}")
            return False
    print()

    # Тест 2: Проверяем что пользователь в памяти
    print("3. Проверяем что пользователь в памяти...")
    if test_username in auth_service.users:
        print(f"   ✅ Пользователь найден в памяти")
    else:
        print(f"   ❌ Пользователь НЕ найден в памяти")
        return False
    print()

    # Тест 3: Проверяем что пользователь в DynamoDB
    print("4. Проверяем что пользователь в DynamoDB...")
    user_data = await storage.get_user_by_username(test_username)
    if user_data:
        print(f"   ✅ Пользователь найден в DynamoDB")
        print(f"   User ID: {user_data.get('user_id')}")
        print(f"   Created: {user_data.get('created_at')}")
    else:
        print(f"   ❌ Пользователь НЕ найден в DynamoDB")
        return False
    print()

    # Тест 4: Создаем НОВЫЙ AuthService (симулируем перезапуск)
    print("5. Симулируем перезапуск приложения...")
    print("   Создаем новый AuthService (без пользователей в памяти)...")

    auth_service_new = AuthService(
        session_storage=session_storage,
        secret_key="test-secret-key",
        user_storage=storage
    )

    print(f"   Пользователей в памяти ДО загрузки: {len(auth_service_new.users)}")

    # Загружаем пользователей из DynamoDB
    await auth_service_new.load_users_from_storage()
    print(f"   Пользователей в памяти ПОСЛЕ загрузки: {len(auth_service_new.users)}")
    print()

    # Тест 5: Проверяем что наш пользователь загружен
    print("6. Проверяем что пользователь загружен после 'перезапуска'...")
    if test_username in auth_service_new.users:
        print(f"   ✅ Пользователь найден в новом AuthService")
    else:
        print(f"   ❌ Пользователь НЕ найден в новом AuthService")
        return False
    print()

    # Тест 6: Пробуем залогиниться
    print("7. Тестируем логин с паролем...")
    try:
        result = await auth_service_new.login(test_username, test_password)
        print(f"   ✅ Логин успешен!")
        print(f"   Token: {result['access_token'][:50]}...")
        print(f"   Session ID: {result['session_id']}")
    except ValueError as e:
        print(f"   ❌ Логин failed: {e}")
        return False
    print()

    print("=" * 80)
    print("✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    print("=" * 80)
    print()
    print("Выводы:")
    print("  ✓ Пользователи сохраняются в DynamoDB при регистрации")
    print("  ✓ Пользователи загружаются из DynamoDB при старте")
    print("  ✓ Логин работает после 'перезапуска' приложения")
    print()
    return True

# Запуск
if __name__ == "__main__":
    result = asyncio.run(test_user_persistence())
    sys.exit(0 if result else 1)

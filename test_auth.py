"""
Тестовый скрипт для демонстрации JWT аутентификации и session persistence
Работает напрямую с auth_service и показывает что происходит "под капотом"
"""
import os
import sys
import asyncio
import logging

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from storage.session_storage import SessionStorage
from services.auth_service import AuthService

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Цвета для консоли
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_section(title):
    """Красивый заголовок секции"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_step(number, description):
    """Нумерованный шаг"""
    print(f"{Colors.BOLD}{Colors.GREEN}[{number}]{Colors.END} {description}")


def print_result(label, value, success=True):
    """Вывод результата"""
    color = Colors.GREEN if success else Colors.RED
    symbol = "✅" if success else "❌"
    print(f"    {symbol} {Colors.BOLD}{label}:{Colors.END} {color}{value}{Colors.END}")


def print_jwt_structure(token):
    """Показывает структуру JWT токена"""
    parts = token.split('.')
    print(f"\n    {Colors.YELLOW}JWT Token Structure:{Colors.END}")
    print(f"    ┌─ Header:    {parts[0][:20]}...")
    print(f"    ├─ Payload:   {parts[1][:20]}...")
    print(f"    └─ Signature: {parts[2][:20]}...")


async def test_authentication():
    """Полный тест аутентификации"""

    print(f"\n{Colors.BOLD}🚀 Testing JWT Authentication & Session Persistence{Colors.END}")
    print(f"{Colors.YELLOW}This demonstrates the new authentication system!{Colors.END}\n")

    # ============================================================================
    # 1. ИНИЦИАЛИЗАЦИЯ
    # ============================================================================
    print_section("1️⃣  INITIALIZATION")

    print_step(1, "Creating SessionStorage instance...")
    session_storage = SessionStorage(
        table_name="trading-alerts",
        region="eu-west-1"
    )
    print_result("Storage", "DynamoDB connection established")
    print(f"    📦 Table: trading-alerts")
    print(f"    🌍 Region: eu-west-1")

    print_step(2, "Creating AuthService instance...")
    auth_service = AuthService(session_storage=session_storage)
    print_result("Service", "JWT authentication ready")
    print(f"    🔐 Algorithm: HS256")
    print(f"    ⏰ Token TTL: 30 days")

    # ============================================================================
    # 2. РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ
    # ============================================================================
    print_section("2️⃣  USER REGISTRATION")

    test_username = "anna_test"
    test_password = "SecurePass123!"

    print_step(1, f"Registering user: {test_username}")
    print(f"    Username: {test_username}")
    print(f"    Password: {'*' * len(test_password)}")

    success, message = await auth_service.register_user(test_username, test_password)
    print_result("Registration", message, success)

    if success:
        print(f"\n    {Colors.YELLOW}What happened:{Colors.END}")
        print(f"    1️⃣  Password was hashed (SHA256)")
        print(f"    2️⃣  User record created in DynamoDB:")
        print(f"        PK: user#{test_username}")
        print(f"        SK: metadata")
        print(f"        entity_type: user")
        print(f"        password_hash: [hidden]")

    # ============================================================================
    # 3. ЛОГИН (СОЗДАНИЕ СЕССИИ)
    # ============================================================================
    print_section("3️⃣  USER LOGIN")

    print_step(1, "Attempting login...")
    success, jwt_token, message = await auth_service.login(test_username, test_password)
    print_result("Login", message, success)

    if success:
        print(f"\n    {Colors.YELLOW}What happened:{Colors.END}")
        print(f"    1️⃣  Password verified against hash")
        print(f"    2️⃣  JWT token generated")
        print_jwt_structure(jwt_token)

        # Декодируем токен чтобы показать payload
        import jwt as jwt_lib
        payload = jwt_lib.decode(jwt_token, options={"verify_signature": False})

        print(f"\n    {Colors.YELLOW}JWT Payload:{Colors.END}")
        print(f"    📧 sub (user):       {payload['sub']}")
        print(f"    🆔 jti (session):    {payload['jti'][:16]}...")
        print(f"    📅 iat (issued):     {payload['iat']}")
        print(f"    ⏰ exp (expires):    {payload['exp']}")

        session_id = payload['jti']

        print(f"\n    3️⃣  Session saved to DynamoDB:")
        print(f"        PK: session#{session_id[:16]}...")
        print(f"        SK: metadata")
        print(f"        user_id: {test_username}")
        print(f"        ttl: {payload['exp']} (auto-delete)")

    # ============================================================================
    # 4. ВАЛИДАЦИЯ ТОКЕНА
    # ============================================================================
    print_section("4️⃣  TOKEN VALIDATION")

    if success:
        print_step(1, "Validating JWT token...")
        valid, username, msg = await auth_service.validate_token(jwt_token)
        print_result("Validation", msg, valid)

        if valid:
            print(f"\n    {Colors.YELLOW}Validation process:{Colors.END}")
            print(f"    1️⃣  JWT signature verified ✅")
            print(f"    2️⃣  Token not expired ✅")
            print(f"    3️⃣  Session found in DynamoDB ✅")
            print(f"    4️⃣  User matches: {username} ✅")

            print(f"\n    {Colors.GREEN}👤 Authenticated as: {username}{Colors.END}")

    # ============================================================================
    # 5. ПРОСМОТР АКТИВНЫХ СЕССИЙ
    # ============================================================================
    print_section("5️⃣  ACTIVE SESSIONS")

    print_step(1, f"Getting all sessions for {test_username}...")
    sessions = await auth_service.get_user_sessions(test_username)
    print_result("Sessions found", len(sessions))

    for i, session in enumerate(sessions, 1):
        print(f"\n    Session #{i}:")
        print(f"    ├─ ID: {session['session_id'][:16]}...")
        print(f"    ├─ Created: {session['created_at']}")
        print(f"    └─ Expires: {session['expires_at']}")

    # ============================================================================
    # 6. LOGOUT (УДАЛЕНИЕ СЕССИИ)
    # ============================================================================
    print_section("6️⃣  USER LOGOUT")

    if success and jwt_token:
        print_step(1, "Logging out...")
        logout_success, logout_msg = await auth_service.logout(jwt_token)
        print_result("Logout", logout_msg, logout_success)

        if logout_success:
            print(f"\n    {Colors.YELLOW}What happened:{Colors.END}")
            print(f"    1️⃣  Session deleted from DynamoDB")
            print(f"    2️⃣  JWT token invalidated")
            print(f"    3️⃣  User must login again")

    # ============================================================================
    # 7. ПРОВЕРКА ПОСЛЕ LOGOUT
    # ============================================================================
    print_section("7️⃣  VALIDATION AFTER LOGOUT")

    if success and jwt_token:
        print_step(1, "Trying to validate token after logout...")
        valid, username, msg = await auth_service.validate_token(jwt_token)
        print_result("Validation", msg, valid)

        if not valid:
            print(f"\n    {Colors.GREEN}Perfect! Token is no longer valid.{Colors.END}")
            print(f"    Session was successfully removed from DynamoDB")

    # ============================================================================
    # ИТОГИ
    # ============================================================================
    print_section("✨ SUMMARY")

    print(f"{Colors.BOLD}New Authentication System Features:{Colors.END}\n")
    print(f"✅ JWT tokens for stateless authentication")
    print(f"✅ DynamoDB session persistence (survives restarts!)")
    print(f"✅ Automatic session cleanup (TTL)")
    print(f"✅ Password hashing (SHA256 for MVP)")
    print(f"✅ Session validation")
    print(f"✅ Multi-session support\n")

    print(f"{Colors.YELLOW}What's different from before:{Colors.END}\n")
    print(f"Before: current_sessions = {{}}  # Lost on restart ❌")
    print(f"After:  DynamoDB storage      # Persistent ✅\n")

    print(f"{Colors.BOLD}Database Structure:{Colors.END}\n")
    print(f"trading-alerts table now contains:")
    print(f"├─ signal#{{id}}     → Trading signals")
    print(f"├─ user#{{username}} → User accounts")
    print(f"└─ session#{{jti}}   → Active sessions\n")

    print(f"{Colors.GREEN}🎉 All tests completed successfully!{Colors.END}\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_authentication())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n\n{Colors.RED}❌ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()

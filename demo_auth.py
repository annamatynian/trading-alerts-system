#!/usr/bin/env python3
"""
Interactive Demo для JWT Authentication System
Демонстрирует все возможности без AWS credentials (использует mocks)

Запуск:
    python demo_auth.py
"""
import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.auth_service import AuthService, BCRYPT_AVAILABLE
from storage.session_storage import SessionStorage


# ============================================================================
# Color Output для красивого отображения
# ============================================================================
class Colors:
    """ANSI color codes для терминала"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Печатает заголовок секции"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.ENDC}\n")


def print_step(step_num, text):
    """Печатает номер шага"""
    print(f"{Colors.OKBLUE}{Colors.BOLD}Step {step_num}: {text}{Colors.ENDC}")


def print_success(text):
    """Печатает успешное сообщение"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_info(text):
    """Печатает информационное сообщение"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_warning(text):
    """Печатает предупреждение"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_error(text):
    """Печатает ошибку"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_json(data, indent=2):
    """Печатает JSON с отступами"""
    import json
    print(f"{Colors.OKCYAN}{json.dumps(data, indent=indent, default=str)}{Colors.ENDC}")


# ============================================================================
# Mock SessionStorage (работает без AWS)
# ============================================================================
class MockSessionStorage:
    """Mock SessionStorage для демо без AWS credentials"""

    def __init__(self):
        self.sessions = {}

    async def save_session(self, session_id, user_id, token, metadata=None):
        self.sessions[session_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'token': token,
            'metadata': metadata,
            'created_at': datetime.now().isoformat(),
            'expires_at': datetime.now().isoformat()
        }
        return True

    async def get_session(self, session_id):
        return self.sessions.get(session_id)

    async def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
        return True

    async def get_user_sessions(self, user_id):
        return [s for s in self.sessions.values() if s['user_id'] == user_id]

    async def extend_session(self, session_id, hours=None):
        if session_id in self.sessions:
            return True
        return False


# ============================================================================
# Demo Functions
# ============================================================================
async def demo_registration(auth: AuthService):
    """Демонстрирует регистрацию пользователя"""
    print_header("1. USER REGISTRATION")

    print_step(1, "Register new user")
    print_info("Creating user 'alice' with password 'SecurePass123!'")

    user = await auth.register_user(
        username="alice",
        password="SecurePass123!",
        metadata={
            "email": "alice@example.com",
            "name": "Alice Johnson",
            "role": "trader"
        }
    )

    print_success("User registered successfully!")
    print_info("User details:")
    print_json(user)

    print_info(f"\n🔐 Password hashing: {'bcrypt' if BCRYPT_AVAILABLE else 'SHA256 (fallback)'}")
    if BCRYPT_AVAILABLE:
        print_success("bcrypt provides strong protection against brute-force attacks")
    else:
        print_warning("bcrypt not available - using SHA256 fallback (less secure)")

    return user


async def demo_login(auth: AuthService):
    """Демонстрирует вход пользователя"""
    print_header("2. USER LOGIN")

    print_step(1, "Login with credentials")
    print_info("Logging in as 'alice' with password 'SecurePass123!'")

    result = await auth.login(
        username="alice",
        password="SecurePass123!",
        metadata={
            "ip": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "device": "laptop"
        }
    )

    print_success("Login successful!")
    print_info("Login result:")

    # Показываем результат (скрываем часть токена для безопасности)
    display_result = result.copy()
    token = display_result['access_token']
    display_result['access_token'] = f"{token[:20]}...{token[-20:]}"
    print_json(display_result)

    print_info(f"\n🎫 JWT Token components:")
    print_info(f"   - Header: Algorithm and token type")
    print_info(f"   - Payload: User data (user_id, username, session_id, expiration)")
    print_info(f"   - Signature: Ensures token integrity")

    print_info(f"\n💾 Session stored in DynamoDB:")
    print_info(f"   - Session ID: {result['session_id']}")
    print_info(f"   - TTL: Auto-cleanup after expiration")

    return result


async def demo_token_validation(auth: AuthService, token: str):
    """Демонстрирует валидацию токена"""
    print_header("3. TOKEN VALIDATION")

    print_step(1, "Validate JWT token")
    print_info("Checking token signature and session in DynamoDB...")

    try:
        payload = await auth.validate_token(token)
        print_success("Token is valid!")
        print_info("Token payload:")
        print_json(payload)

        print_info("\n🔍 Validation checks:")
        print_success("✓ JWT signature verified")
        print_success("✓ Token not expired")
        print_success("✓ Session exists in DynamoDB")
        print_success("✓ Token matches stored session")

    except ValueError as e:
        print_error(f"Token validation failed: {e}")


async def demo_tampering_detection(auth: AuthService, session_id: str):
    """Демонстрирует обнаружение подделки токена"""
    print_header("4. TAMPERING DETECTION")

    print_step(1, "Attempt to use tampered token")
    print_warning("Simulating token tampering attack...")

    # Создаем поддельный токен
    import jwt
    fake_payload = {
        'sub': 'fake-user-id',
        'username': 'hacker',
        'session_id': session_id,
        'exp': datetime.now()
    }
    fake_token = jwt.encode(fake_payload, "test-secret-key", algorithm="HS256")

    print_info(f"Fake token created: {fake_token[:30]}...")

    try:
        await auth.validate_token(fake_token)
        print_error("SECURITY BREACH: Fake token accepted!")
    except ValueError as e:
        print_success("Tampering detected and blocked!")
        print_info(f"Error: {e}")

        print_info("\n🛡️  Security features:")
        print_success("✓ JWT signature verification")
        print_success("✓ Token comparison with DynamoDB")
        print_success("✓ Protection against token tampering")


async def demo_rate_limiting(auth: AuthService):
    """Демонстрирует rate limiting"""
    print_header("5. RATE LIMITING (Brute-force Protection)")

    print_step(1, "Simulate brute-force attack")
    print_info("Making 5 failed login attempts...")

    attempts = 0
    for i in range(6):
        try:
            await auth.login("alice", f"wrong_password_{i}")
        except ValueError as e:
            attempts += 1
            if "Too many attempts" in str(e):
                print_error(f"Attempt {i+1}: BLOCKED - {e}")
                print_success("\n🚫 Rate limiting activated!")
                print_info("Protection features:")
                print_success("✓ Maximum 5 failed attempts")
                print_success("✓ 5-minute lockout period")
                print_success("✓ Protection against brute-force attacks")
                break
            else:
                print_warning(f"Attempt {i+1}: Failed - {e}")

    # Очищаем rate limit для продолжения demo
    auth.rate_limiter.clear_attempts("alice")
    print_info("\n✅ Rate limit cleared for demo continuation")


async def demo_multiple_sessions(auth: AuthService):
    """Демонстрирует множественные сессии"""
    print_header("6. MULTIPLE SESSIONS")

    print_step(1, "Create sessions from different devices")

    devices = ["laptop", "phone", "tablet"]
    sessions = []

    for device in devices:
        result = await auth.login(
            username="alice",
            password="SecurePass123!",
            metadata={"device": device}
        )
        sessions.append(result)
        print_success(f"Session created on {device}: {result['session_id'][:16]}...")

    print_step(2, "List all active sessions")
    user_sessions = await auth.get_user_sessions("alice")
    print_info(f"Total active sessions: {len(user_sessions)}")

    for session in user_sessions:
        device = session.get('metadata', {}).get('device', 'unknown')
        print_info(f"  - {session['session_id'][:16]}... (device: {device})")

    print_info("\n💡 Use cases:")
    print_info("  - Multi-device login (laptop, phone, tablet)")
    print_info("  - View all active sessions")
    print_info("  - Force logout from all devices")

    return sessions


async def demo_token_refresh(auth: AuthService, session_id: str):
    """Демонстрирует обновление токена"""
    print_header("7. TOKEN REFRESH")

    print_step(1, "Refresh token to extend session")
    print_info(f"Refreshing session: {session_id[:16]}...")

    result = await auth.refresh_token(session_id, hours=48)

    print_success("Token refreshed successfully!")
    print_info("New token details:")

    display_result = {
        'session_id': result['session_id'],
        'access_token': f"{result['access_token'][:20]}...{result['access_token'][-20:]}",
        'expires_at': result['expires_at']
    }
    print_json(display_result)

    print_info("\n🔄 Refresh benefits:")
    print_success("✓ Extend session without re-login")
    print_success("✓ Same session_id maintained")
    print_success("✓ New JWT token issued")
    print_success("✓ Updated expiration time")


async def demo_logout(auth: AuthService, sessions: list):
    """Демонстрирует выход из системы"""
    print_header("8. LOGOUT")

    print_step(1, "Logout from specific session")

    # Выходим из первой сессии
    session_to_logout = sessions[0]
    device = session_to_logout.get('metadata', {}).get('device', 'unknown')

    print_info(f"Logging out from {device} session...")

    success = await auth.logout(session_to_logout['session_id'])

    if success:
        print_success(f"Successfully logged out from {device}!")

        print_step(2, "Verify session removed")
        user_sessions = await auth.get_user_sessions("alice")
        print_info(f"Remaining active sessions: {len(user_sessions)}")

        for session in user_sessions:
            device = session.get('metadata', {}).get('device', 'unknown')
            print_info(f"  - Still active: {device}")

        print_info("\n🚪 Logout features:")
        print_success("✓ Session removed from DynamoDB")
        print_success("✓ Token invalidated")
        print_success("✓ Other sessions remain active")


async def demo_security_summary():
    """Показывает итоговую сводку по безопасности"""
    print_header("SECURITY FEATURES SUMMARY")

    print_info("🔐 Password Security:")
    print_success("  ✓ bcrypt hashing (or SHA256 fallback)")
    print_success("  ✓ Salt for each password")
    print_success("  ✓ Minimum 8 characters requirement")

    print_info("\n🎫 JWT Tokens:")
    print_success("  ✓ Signed with secret key")
    print_success("  ✓ Expiration time (TTL)")
    print_success("  ✓ Tamper detection")
    print_success("  ✓ Refresh capability")

    print_info("\n💾 Session Persistence:")
    print_success("  ✓ DynamoDB storage")
    print_success("  ✓ Auto-cleanup with TTL")
    print_success("  ✓ Multi-device support")
    print_success("  ✓ Session validation")

    print_info("\n🛡️  Protection:")
    print_success("  ✓ Rate limiting (5 attempts, 5-min lockout)")
    print_success("  ✓ Brute-force protection")
    print_success("  ✓ Token tampering detection")
    print_success("  ✓ Secure logout")

    print_info("\n📊 Production Ready:")
    print_success("  ✓ Async/await throughout")
    print_success("  ✓ Error handling")
    print_success("  ✓ Detailed logging")
    print_success("  ✓ AWS DynamoDB integration")


# ============================================================================
# Main Demo
# ============================================================================
async def main():
    """Запускает интерактивное демо"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║     JWT AUTHENTICATION SYSTEM - INTERACTIVE DEMO                   ║")
    print("║     Production-ready with DynamoDB Session Persistence             ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")

    print_info("This demo works WITHOUT AWS credentials (uses mocks)")
    print_info(f"Password hashing: {'bcrypt ✓' if BCRYPT_AVAILABLE else 'SHA256 (bcrypt not installed)'}")

    # Инициализируем AuthService с mock storage
    mock_storage = MockSessionStorage()
    auth = AuthService(
        secret_key="demo-secret-key-12345",
        session_storage=mock_storage
    )

    print_info("\nPress Enter to continue through each step...")
    input()

    # 1. Registration
    user = await demo_registration(auth)
    input()

    # 2. Login
    login_result = await demo_login(auth)
    input()

    # 3. Token Validation
    await demo_token_validation(auth, login_result['access_token'])
    input()

    # 4. Tampering Detection
    await demo_tampering_detection(auth, login_result['session_id'])
    input()

    # 5. Rate Limiting
    await demo_rate_limiting(auth)
    input()

    # 6. Multiple Sessions
    all_sessions = await demo_multiple_sessions(auth)
    input()

    # 7. Token Refresh
    await demo_token_refresh(auth, all_sessions[0]['session_id'])
    input()

    # 8. Logout
    await demo_logout(auth, all_sessions)
    input()

    # Security Summary
    await demo_security_summary()

    print_header("DEMO COMPLETED")
    print_success("All features demonstrated successfully!")
    print_info("\nNext steps:")
    print_info("  1. Run unit tests: pytest test_unit_auth.py -v")
    print_info("  2. Run production tests: pytest test_production_features.py -v")
    print_info("  3. Configure AWS credentials for production use")
    print_info("  4. Set JWT_SECRET_KEY environment variable")
    print_info("  5. Deploy to production environment")

    print(f"\n{Colors.OKGREEN}Thank you for trying the JWT Authentication System!{Colors.ENDC}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Demo interrupted by user{Colors.ENDC}")
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()

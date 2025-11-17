"""
DEMO: JWT Authentication без реального DynamoDB
Показывает логику работы с mock storage
"""
import sys
import asyncio
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import jwt

# Цвета для вывода
class C:
    G = '\033[92m'; B = '\033[94m'; Y = '\033[93m'
    R = '\033[91m'; BOLD = '\033[1m'; END = '\033[0m'


class MockSessionStorage:
    """Mock хранилище для демонстрации"""
    def __init__(self):
        self.sessions = {}  # В памяти для demo
        self.users = {}

    async def save_session(self, session_id, user_id, metadata=None):
        self.sessions[session_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
            'metadata': metadata or {}
        }
        return True

    async def get_session(self, session_id):
        return self.sessions.get(session_id)

    async def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    async def get_user_sessions(self, user_id):
        return [s for s in self.sessions.values() if s['user_id'] == user_id]

    async def save_user(self, username, password_hash):
        self.users[username] = {
            'username': username,
            'password_hash': password_hash,
            'created_at': datetime.now().isoformat()
        }
        return True

    async def get_user(self, username):
        return self.users.get(username)


def section(title):
    print(f"\n{C.BOLD}{C.B}{'='*70}{C.END}")
    print(f"{C.BOLD}{C.B}{title.center(70)}{C.END}")
    print(f"{C.BOLD}{C.B}{'='*70}{C.END}\n")


def step(num, text):
    print(f"{C.BOLD}{C.G}[Step {num}]{C.END} {text}")


async def main():
    print(f"\n{C.BOLD}🎭 JWT Authentication DEMO{C.END}")
    print(f"{C.Y}Demonstrating session persistence without real DynamoDB{C.END}\n")

    # ========================================================================
    # 1. ИНИЦИАЛИЗАЦИЯ
    # ========================================================================
    section("1️⃣  INITIALIZATION")

    step(1, "Creating Mock Session Storage")
    storage = MockSessionStorage()
    print(f"   ✅ Mock storage created (in-memory for demo)")
    print(f"   {C.Y}В production: DynamoDB with TTL auto-cleanup{C.END}")

    JWT_SECRET = secrets.token_urlsafe(32)
    print(f"\n   🔐 JWT Secret: {JWT_SECRET[:20]}... (randomly generated)")
    print(f"   {C.Y}В production: Set JWT_SECRET_KEY env variable!{C.END}")

    # ========================================================================
    # 2. РЕГИСТРАЦИЯ
    # ========================================================================
    section("2️⃣  USER REGISTRATION")

    username = "anna_demo"
    password = "MySecurePass123!"

    step(1, f"Registering user: {username}")
    print(f"   Username: {username}")
    print(f"   Password: {'*' * len(password)}")

    # Хешируем пароль
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    await storage.save_user(username, password_hash)

    print(f"\n   ✅ User registered successfully!")
    print(f"\n   {C.Y}What was saved:{C.END}")
    print(f"   {C.BOLD}DynamoDB Structure:{C.END}")
    print(f"   ┌─ PK: user#{username}")
    print(f"   ├─ SK: metadata")
    print(f"   ├─ username: {username}")
    print(f"   ├─ password_hash: {password_hash[:20]}...")
    print(f"   └─ created_at: {datetime.now().isoformat()}")

    # ========================================================================
    # 3. ЛОГИН
    # ========================================================================
    section("3️⃣  USER LOGIN")

    step(1, "Verifying password...")
    user = await storage.get_user(username)
    input_hash = hashlib.sha256(password.encode()).hexdigest()

    if user['password_hash'] == input_hash:
        print(f"   ✅ Password verified!")
    else:
        print(f"   ❌ Wrong password")
        return

    step(2, "Generating JWT token...")

    # Создаем JWT payload
    session_id = secrets.token_urlsafe(16)
    now = datetime.utcnow()
    expires = now + timedelta(days=30)

    payload = {
        'sub': username,        # Subject (who)
        'jti': session_id,      # JWT ID (session identifier)
        'iat': int(now.timestamp()),       # Issued at
        'exp': int(expires.timestamp()),   # Expiration
    }

    jwt_token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')

    print(f"   ✅ JWT token created!")
    print(f"\n   {C.Y}JWT Token Structure:{C.END}")

    parts = jwt_token.split('.')
    print(f"   {jwt_token[:60]}...")
    print(f"   ↑")
    print(f"   ├─ Header (base64):    {parts[0][:30]}...")
    print(f"   ├─ Payload (base64):   {parts[1][:30]}...")
    print(f"   └─ Signature (HMAC):   {parts[2][:30]}...")

    print(f"\n   {C.Y}Decoded Payload:{C.END}")
    for key, value in payload.items():
        if key in ['iat', 'exp']:
            dt = datetime.fromtimestamp(value)
            print(f"   {key}: {value} ({dt.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            val_str = str(value)[:50]
            print(f"   {key}: {val_str}")

    step(3, "Saving session to database...")
    await storage.save_session(session_id, username, {'login_time': datetime.now().isoformat()})

    print(f"   ✅ Session saved!")
    print(f"\n   {C.Y}DynamoDB Structure:{C.END}")
    print(f"   ┌─ PK: session#{session_id[:16]}...")
    print(f"   ├─ SK: metadata")
    print(f"   ├─ user_id: {username}")
    print(f"   ├─ created_at: {now.isoformat()}")
    print(f"   ├─ expires_at: {expires.isoformat()}")
    print(f"   └─ ttl: {int(expires.timestamp())} ← DynamoDB auto-deletes")

    # ========================================================================
    # 4. ВАЛИДАЦИЯ ТОКЕНА
    # ========================================================================
    section("4️⃣  TOKEN VALIDATION")

    step(1, "Client sends JWT token in request...")
    print(f"   Token: {jwt_token[:40]}...")

    step(2, "Server validates token...")

    try:
        # Проверяем signature и expiration
        decoded = jwt.decode(jwt_token, JWT_SECRET, algorithms=['HS256'])
        print(f"   ✅ JWT signature valid")
        print(f"   ✅ Token not expired")

        # Проверяем сессию в базе
        session = await storage.get_session(decoded['jti'])
        if session:
            print(f"   ✅ Session found in database")
            print(f"   ✅ User matches: {session['user_id']}")

            print(f"\n   {C.G}{C.BOLD}🎉 Authentication successful!{C.END}")
            print(f"   {C.G}User {username} is now authenticated{C.END}")

    except jwt.ExpiredSignatureError:
        print(f"   ❌ Token expired")
    except jwt.InvalidTokenError:
        print(f"   ❌ Invalid token")

    # ========================================================================
    # 5. АКТИВНЫЕ СЕССИИ
    # ========================================================================
    section("5️⃣  VIEWING ACTIVE SESSIONS")

    step(1, f"Getting all sessions for {username}...")
    sessions = await storage.get_user_sessions(username)

    print(f"   Found {len(sessions)} active session(s)")

    for i, sess in enumerate(sessions, 1):
        print(f"\n   Session #{i}:")
        print(f"   ├─ ID: {sess['session_id'][:20]}...")
        print(f"   ├─ Created: {sess['created_at']}")
        print(f"   └─ Expires: {sess['expires_at']}")

    # ========================================================================
    # 6. LOGOUT
    # ========================================================================
    section("6️⃣  USER LOGOUT")

    step(1, "Extracting session_id from JWT...")
    payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=['HS256'])
    session_id_to_delete = payload['jti']
    print(f"   Session ID: {session_id_to_delete[:20]}...")

    step(2, "Deleting session from database...")
    success = await storage.delete_session(session_id_to_delete)

    if success:
        print(f"   ✅ Session deleted!")
        print(f"\n   {C.Y}What happened:{C.END}")
        print(f"   1️⃣  Session removed from DynamoDB")
        print(f"   2️⃣  JWT token still exists but...")
        print(f"   3️⃣  ...validation will fail (no session in DB)")

    # ========================================================================
    # 7. ПРОВЕРКА ПОСЛЕ LOGOUT
    # ========================================================================
    section("7️⃣  VALIDATION AFTER LOGOUT")

    step(1, "Trying to validate same token...")

    try:
        decoded = jwt.decode(jwt_token, JWT_SECRET, algorithms=['HS256'])
        print(f"   ✅ JWT signature still valid (token structure OK)")

        session = await storage.get_session(decoded['jti'])
        if not session:
            print(f"   ❌ Session not found in database")
            print(f"\n   {C.G}Perfect! User is logged out.{C.END}")
            print(f"   {C.G}Token is invalidated by deleting session.{C.END}")

    except jwt.InvalidTokenError as e:
        print(f"   ❌ Token invalid: {e}")

    # ========================================================================
    # ИТОГИ
    # ========================================================================
    section("✨ SUMMARY")

    print(f"{C.BOLD}What we demonstrated:{C.END}\n")

    print(f"1️⃣  {C.BOLD}Registration:{C.END}")
    print(f"   - Password hashing (SHA256)")
    print(f"   - User data stored in DynamoDB")
    print(f"   - Structure: user#{{username}}")

    print(f"\n2️⃣  {C.BOLD}Login:{C.END}")
    print(f"   - Password verification")
    print(f"   - JWT token generation (3 parts)")
    print(f"   - Session creation in DynamoDB")
    print(f"   - Structure: session#{{jti}}")

    print(f"\n3️⃣  {C.BOLD}Validation:{C.END}")
    print(f"   - JWT signature check")
    print(f"   - Expiration check")
    print(f"   - Session lookup in DynamoDB")
    print(f"   - User matching")

    print(f"\n4️⃣  {C.BOLD}Logout:{C.END}")
    print(f"   - Session deletion from DynamoDB")
    print(f"   - Token invalidation")
    print(f"   - Future requests rejected")

    print(f"\n{C.Y}Database Structure:{C.END}")
    print(f"trading-alerts table:")
    print(f"├─ signal#{{id}}      → Trading signals")
    print(f"├─ user#{{username}}  → User accounts (password_hash)")
    print(f"└─ session#{{jti}}    → Active sessions (with TTL)")

    print(f"\n{C.G}{C.BOLD}🎉 That's how JWT + DynamoDB persistence works!{C.END}\n")

    print(f"{C.Y}Key Benefits:{C.END}")
    print(f"✅ Sessions survive server restarts")
    print(f"✅ Automatic cleanup via DynamoDB TTL")
    print(f"✅ Stateless authentication (JWT)")
    print(f"✅ Server-side session validation")
    print(f"✅ Multi-device support (multiple sessions per user)")

    print(f"\n{C.Y}What's missing for full page refresh persistence:{C.END}")
    print(f"⏳ Store JWT token in browser cookies")
    print(f"⏳ Check cookies on page load")
    print(f"⏳ Auto-restore session if valid")
    print(f"\n{C.B}See docs/AUTHENTICATION.md for implementation details!{C.END}\n")


if __name__ == "__main__":
    asyncio.run(main())

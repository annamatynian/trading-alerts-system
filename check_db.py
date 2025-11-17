"""
Проверка содержимого DynamoDB таблицы
Показывает все записи: пользователей, сессии, сигналы
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add src to path
sys.path.insert(0, 'src')

from storage.dynamodb_storage import DynamoDBStorage
import asyncio

print("=" * 80)
print("Checking DynamoDB Table Contents")
print("=" * 80)
print()

# Initialize storage
table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-alerts')
region = os.getenv('DYNAMODB_REGION', 'eu-west-1')

print(f"Table: {table_name}")
print(f"Region: {region}")
print()

storage = DynamoDBStorage(table_name=table_name, region=region)

# Scan table
print("Scanning table...")
response = storage.table.scan()

total_items = response['Count']
print(f"Total items: {total_items}")
print()

# Group by entity type
users = []
sessions = []
signals = []
other = []

for item in response.get('Items', []):
    pk = item.get('PK', 'unknown')
    sk = item.get('SK', 'unknown')
    entity = item.get('entity_type', 'unknown')

    if pk.startswith('user#'):
        users.append(item)
    elif pk.startswith('session#'):
        sessions.append(item)
    elif pk.startswith('signal#'):
        signals.append(item)
    else:
        other.append(item)

# Display results
print("=" * 80)
print(f"USERS: {len(users)}")
print("=" * 80)
if users:
    for item in users:
        username = item.get('PK', '').replace('user#', '')
        created = item.get('created_at', 'unknown')
        print(f"  ✓ {username} (created: {created})")
else:
    print("  ❌ No users found in DynamoDB!")
    print("  💡 Users are stored in memory (self.users = {}) and lost on restart")
print()

print("=" * 80)
print(f"SESSIONS: {len(sessions)}")
print("=" * 80)
if sessions:
    for item in sessions[:5]:  # Show first 5
        session_id = item.get('session_id', 'unknown')
        user_id = item.get('user_id', 'unknown')
        expires = item.get('expires_at', 'unknown')
        print(f"  ✓ Session {session_id[:8]}... | User: {user_id} | Expires: {expires}")
    if len(sessions) > 5:
        print(f"  ... and {len(sessions) - 5} more")
else:
    print("  ⊘ No active sessions")
print()

print("=" * 80)
print(f"SIGNALS: {len(signals)}")
print("=" * 80)
if signals:
    for item in signals[:5]:  # Show first 5
        signal_id = item.get('PK', '').replace('signal#', '')
        symbol = item.get('symbol', 'unknown')
        user_id = item.get('user_id', 'unknown')
        print(f"  ✓ {symbol} | User: {user_id} | ID: {signal_id[:8]}...")
    if len(signals) > 5:
        print(f"  ... and {len(signals) - 5} more")
else:
    print("  ⊘ No signals")
print()

if other:
    print("=" * 80)
    print(f"OTHER: {len(other)}")
    print("=" * 80)
    for item in other[:5]:
        pk = item.get('PK', 'unknown')
        sk = item.get('SK', 'unknown')
        print(f"  ? {pk} | {sk}")
    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total items: {total_items}")
print(f"  Users:    {len(users)}")
print(f"  Sessions: {len(sessions)}")
print(f"  Signals:  {len(signals)}")
print(f"  Other:    {len(other)}")
print()

if len(users) == 0:
    print("⚠️  WARNING: No users in DynamoDB!")
    print()
    print("Root cause: auth_service.py stores users in memory (self.users = {})")
    print("Solution: Need to add DynamoDB persistence for users")
    print()
    print("Would you like me to fix this?")

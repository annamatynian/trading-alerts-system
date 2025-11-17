#!/usr/bin/env python3
"""
Быстрый тест AWS DynamoDB подключения
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
print("Testing AWS DynamoDB Connection")
print("=" * 80)
print()

# Check environment variables
print("1. Checking environment variables...")
aws_key = os.getenv('AWS_ACCESS_KEY_ID', '')
aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY', '')
table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-alerts')
region = os.getenv('DYNAMODB_REGION', 'eu-west-1')

print(f"   AWS_ACCESS_KEY_ID: {'✓ Set' if aws_key else '✗ Not set'}")
print(f"   AWS_SECRET_ACCESS_KEY: {'✓ Set' if aws_secret else '✗ Not set'}")
print(f"   DYNAMODB_TABLE_NAME: {table_name}")
print(f"   DYNAMODB_REGION: {region}")
print()

if not aws_key or not aws_secret:
    print("❌ AWS credentials not found in .env file!")
    print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    sys.exit(1)

# Test boto3 connection
print("2. Testing boto3 DynamoDB connection...")
try:
    import boto3
    from botocore.exceptions import ClientError

    # Create DynamoDB client
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=region,
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret
    )

    # Try to access the table
    table = dynamodb.Table(table_name)

    # Get table metadata (this will fail if credentials are wrong)
    table.load()

    print(f"   ✅ Successfully connected to DynamoDB!")
    print(f"   Table: {table.name}")
    print(f"   Status: {table.table_status}")
    print(f"   Item count: {table.item_count}")
    print()

except ClientError as e:
    error_code = e.response['Error']['Code']
    print(f"   ❌ DynamoDB error: {error_code}")
    print(f"   Message: {e.response['Error']['Message']}")
    print()

    if error_code == 'ResourceNotFoundException':
        print("   💡 Table doesn't exist yet - this is OK for new setup")
    elif error_code in ['UnrecognizedClientException', 'InvalidSignatureException']:
        print("   💡 AWS credentials are invalid or incorrect")
    elif error_code == 'AccessDeniedException':
        print("   💡 AWS credentials don't have DynamoDB permissions")

    sys.exit(1)

except Exception as e:
    print(f"   ❌ Unexpected error: {e}")
    sys.exit(1)

# Test SessionStorage
print("3. Testing SessionStorage...")
try:
    from storage.session_storage import SessionStorage

    session_storage = SessionStorage(
        table_name=table_name,
        region=region,
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret
    )

    print("   ✅ SessionStorage initialized successfully!")
    print()

except Exception as e:
    print(f"   ❌ SessionStorage error: {e}")
    sys.exit(1)

# Test AuthService
print("4. Testing AuthService...")
try:
    from services.auth_service import AuthService

    auth_service = AuthService(
        session_storage=session_storage,
        secret_key="test-secret-key-for-jwt"
    )

    print("   ✅ AuthService initialized successfully!")
    print()

except Exception as e:
    print(f"   ❌ AuthService error: {e}")
    sys.exit(1)

print("=" * 80)
print("✅ ALL CHECKS PASSED!")
print("=" * 80)
print()
print("Your AWS credentials are working correctly!")
print("You can now:")
print("  1. Run the full test suite: python test_all.py")
print("  2. Integrate authentication into app.py")
print("  3. Start using the system in production")
print()

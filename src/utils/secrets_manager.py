"""
AWS Secrets Manager Helper
Получение user mapping для multiuser поддержки
"""
import json
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SecretsManager:
    """Helper для работы с AWS Secrets Manager"""

    def __init__(self, secret_name: str = "trading-alerts/users", region: str = "eu-west-1"):
        """
        Инициализация Secrets Manager client

        Args:
            secret_name: Имя секрета в AWS Secrets Manager
            region: AWS регион
        """
        self.secret_name = secret_name
        self.region = region
        self.client = boto3.client('secretsmanager', region_name=region)
        self._cache: Optional[Dict] = None

    def get_secret(self) -> Dict:
        """
        Получить секрет из AWS Secrets Manager с кешированием

        Returns:
            Dict с структурой:
            {
                "pushover_api_token": "...",
                "users": {
                    "anna": {"pushover_user_key": "...", "name": "Anna"},
                    "tomas": {"pushover_user_key": "...", "name": "Tomas"}
                }
            }
        """
        # Используем кеш для Lambda warm starts
        if self._cache is not None:
            logger.info(f"Using cached secret: {self.secret_name}")
            return self._cache

        try:
            logger.info(f"Fetching secret from AWS Secrets Manager: {self.secret_name}")
            response = self.client.get_secret_value(SecretId=self.secret_name)

            # Парсим JSON
            if 'SecretString' in response:
                secret_data = json.loads(response['SecretString'])
                self._cache = secret_data
                logger.info(f"✅ Secret loaded successfully with {len(secret_data.get('users', {}))} users")
                return secret_data
            else:
                raise ValueError("Secret does not contain SecretString")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"❌ Failed to fetch secret: {error_code}")

            if error_code == 'ResourceNotFoundException':
                logger.error(f"Secret '{self.secret_name}' not found in region {self.region}")
            elif error_code == 'AccessDeniedException':
                logger.error("Lambda role doesn't have permission to read secret")
            elif error_code == 'InvalidRequestException':
                logger.error("Invalid request to Secrets Manager")

            raise

        except Exception as e:
            logger.error(f"❌ Unexpected error fetching secret: {e}")
            raise

    def get_user_config(self, user_id: str) -> Optional[Dict]:
        """
        Получить конфигурацию конкретного пользователя

        Args:
            user_id: ID пользователя (например: "anna", "tomas")

        Returns:
            Dict с конфигурацией пользователя или None если не найден
            {
                "pushover_user_key": "uQiRzpo4...",
                "name": "Anna",
                "phone": "iPhone",
                "enabled": true
            }
        """
        secret_data = self.get_secret()
        users = secret_data.get('users', {})

        # Ищем пользователя
        user_config = users.get(user_id)

        if user_config:
            # Проверяем что пользователь активен
            if user_config.get('enabled', True):
                logger.info(f"✅ Found config for user '{user_id}': {user_config.get('name', 'Unknown')}")
                return user_config
            else:
                logger.warning(f"⚠️  User '{user_id}' is disabled")
                return None
        else:
            # Пробуем fallback на default пользователя
            logger.warning(f"⚠️  User '{user_id}' not found, trying 'default'")
            default_config = users.get('default')

            if default_config:
                logger.info(f"✅ Using default user config")
                return default_config
            else:
                logger.error(f"❌ No config found for user '{user_id}' and no default user")
                return None

    def get_pushover_api_token(self) -> str:
        """
        Получить Pushover API Token для приложения

        Returns:
            Pushover API token
        """
        secret_data = self.get_secret()
        api_token = secret_data.get('pushover_api_token')

        if not api_token:
            raise ValueError("pushover_api_token not found in secret")

        return api_token

    def get_user_pushover_key(self, user_id: str) -> Optional[str]:
        """
        Получить Pushover User Key для конкретного пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Pushover user key или None
        """
        user_config = self.get_user_config(user_id)

        if user_config:
            return user_config.get('pushover_user_key')
        else:
            return None

    def list_users(self) -> list:
        """
        Получить список всех пользователей

        Returns:
            Список user_id
        """
        secret_data = self.get_secret()
        users = secret_data.get('users', {})
        return list(users.keys())

    def clear_cache(self):
        """Очистить кеш секрета"""
        self._cache = None
        logger.info("Cache cleared")


# Singleton instance для переиспользования в Lambda
_secrets_manager_instance: Optional[SecretsManager] = None


def get_secrets_manager(secret_name: str = "trading-alerts/users", region: str = "eu-west-1") -> SecretsManager:
    """
    Получить singleton instance SecretsManager
    Переиспользуется между Lambda warm starts

    Args:
        secret_name: Имя секрета
        region: AWS регион

    Returns:
        SecretsManager instance
    """
    global _secrets_manager_instance

    if _secrets_manager_instance is None:
        _secrets_manager_instance = SecretsManager(secret_name=secret_name, region=region)
        logger.info("Created new SecretsManager instance")
    else:
        logger.info("Reusing existing SecretsManager instance")

    return _secrets_manager_instance

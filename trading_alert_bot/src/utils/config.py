"""
Configuration data models
"""
import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
from models.alert import ExchangeType


class ExchangeConfig(BaseModel):
    """Configuration for a specific exchange"""
    exchange: ExchangeType
    api_key: Optional[str] = Field(None, description="API Key (for private endpoints)")
    api_secret: Optional[str] = Field(None, description="API Secret")
    api_passphrase: Optional[str] = Field(None, description="API Passphrase (for some exchanges)")
    testnet: bool = Field(False, description="Use testnet/sandbox")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(60, gt=0, description="Max requests per minute")
    rate_limit_per_second: int = Field(10, gt=0, description="Max requests per second")
    
    # Retry configuration
    max_retries: int = Field(3, ge=0, description="Max retry attempts")
    retry_delay: float = Field(1.0, gt=0, description="Delay between retries (seconds)")
    
    # Exchange-specific settings
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Exchange-specific parameters")
    
    @validator('api_secret')
    def validate_credentials(cls, v, values):
        """Validate that if api_key is provided, api_secret is also provided"""
        api_key = values.get('api_key')
        if api_key and not v:
            raise ValueError('api_secret required when api_key is provided')
        return v


class NotificationConfig(BaseModel):
    """Notification settings"""
    # Telegram settings
    telegram_enabled: bool = Field(True, description="Enable Telegram notifications")
    telegram_bot_token: Optional[str] = Field(None, description="Telegram bot token")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID")
    
    pushover_enabled: bool = Field(True, description="Enable Pushover notifications")
    pushover_api_token: Optional[str] = Field(None, description="Pushover API Token for your application")
    
    # Email settings (future)
    email_enabled: bool = Field(False, description="Enable email notifications")
    email_smtp_server: Optional[str] = None
    email_smtp_port: Optional[int] = None
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_to: Optional[str] = None
    
    # Webhook settings (future)
    webhook_enabled: bool = Field(False, description="Enable webhook notifications")
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = Field(default_factory=dict)
    
    # Notification formatting
    include_price_chart: bool = Field(False, description="Include price chart in notifications")
    include_volume_info: bool = Field(True, description="Include volume information")
    custom_message_template: Optional[str] = Field(None, description="Custom message template")
    
    @validator('telegram_chat_id')
    def validate_telegram_config(cls, v, values):
        """Validate Telegram configuration"""
        if values.get('telegram_enabled'):
            bot_token = values.get('telegram_bot_token')
            if not bot_token or not v:
                raise ValueError('telegram_bot_token and telegram_chat_id required when telegram_enabled=True')
        return v


class AppConfig(BaseModel):
    """Main application configuration"""
    
    # Basic settings
    app_name: str = Field("Trading Alert System", description="Application name")
    environment: str = Field("development", description="Environment (development/production)")
    debug: bool = Field(False, description="Enable debug mode")
    
    # Scheduling
    check_interval_seconds: int = Field(3600, gt=0, description="Check interval in seconds")
    timezone: str = Field("UTC", description="Timezone for scheduling")
    
    # Storage settings
    storage_type: str = Field("firestore", description="Storage backend (firestore/sheets/json)")
    firestore_project_id: Optional[str] = Field(None, description="Google Cloud project ID")
    firestore_collection: str = Field("alerts", description="Firestore collection name")
    
    # Google Sheets settings (alternative storage)
    sheets_spreadsheet_id: Optional[str] = None
    sheets_worksheet_name: str = Field("alerts", description="Worksheet name")
    
    # Local JSON storage settings (for testing)
    json_file_path: str = Field("alerts.json", description="Path to JSON file")
    
    # Security
    secret_manager_project_id: Optional[str] = Field(None, description="Project ID for Secret Manager")
    encryption_key: Optional[str] = Field(None, description="Encryption key for sensitive data")
    
    # Performance
    max_concurrent_checks: int = Field(10, gt=0, description="Maximum concurrent price checks")
    request_timeout_seconds: int = Field(30, gt=0, description="HTTP request timeout")
    
    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field("json", description="Log format (json/text)")
    
    # Feature flags
    enable_price_history: bool = Field(False, description="Store price history")
    enable_technical_indicators: bool = Field(False, description="Calculate technical indicators")
    enable_multi_exchange_arbitrage: bool = Field(False, description="Track arbitrage opportunities")
    
    # Config class removed - using load_dotenv() instead


class SystemConfig(BaseModel):
    """Complete system configuration"""
    app: AppConfig
    exchanges: Dict[ExchangeType, ExchangeConfig] = Field(default_factory=dict)
    notifications: NotificationConfig
    
    # Runtime settings
    alerts: List[Any] = Field(default_factory=list, description="Will be List[AlertTarget] at runtime")
    
    def get_enabled_exchanges(self) -> List[ExchangeType]:
        """Get list of enabled exchanges"""
        return list(self.exchanges.keys())
    
    def get_exchange_config(self, exchange: ExchangeType) -> Optional[ExchangeConfig]:
        """Get configuration for specific exchange"""
        return self.exchanges.get(exchange)
    
    def is_exchange_enabled(self, exchange: ExchangeType) -> bool:
        """Check if exchange is enabled"""
        return exchange in self.exchanges
    
    @validator('exchanges')
    def validate_at_least_one_exchange(cls, v):
        """Ensure at least one exchange is configured"""
        if not v:
            raise ValueError('At least one exchange must be configured')
        return v


def load_config(env_path: Optional[str] = None) -> SystemConfig:
    """
    Загружает конфигурацию из .env файла
    
    Args:
        env_path: Путь к .env файлу
    
    Returns:
        SystemConfig: Объект конфигурации системы
    """
    # Загружаем .env файл
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()
    
    # Создаем конфигурацию приложения
    app = AppConfig()
    
    # Создаем конфигурацию бирж
    exchanges = {}
    
    # Binance
    binance_key = os.getenv("BINANCE_API_KEY", "")
    binance_secret = os.getenv("BINANCE_API_SECRET", "")
    if binance_key and binance_secret:
        exchanges[ExchangeType.BINANCE] = ExchangeConfig(
            exchange=ExchangeType.BINANCE,
            api_key=binance_key,
            api_secret=binance_secret
        )
    
    # Bybit
    bybit_key = os.getenv("BYBIT_API_KEY", "")
    bybit_secret = os.getenv("BYBIT_API_SECRET", "")
    if bybit_key and bybit_secret:
        exchanges[ExchangeType.BYBIT] = ExchangeConfig(
            exchange=ExchangeType.BYBIT,
            api_key=bybit_key,
            api_secret=bybit_secret
        )
    
    # Создаем конфигурацию уведомлений
    notifications = NotificationConfig(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "")
    )
    
    # Создаем системную конфигурацию
    system_config = SystemConfig(
        app=app,
        exchanges=exchanges,
        notifications=notifications
    )
    
    return system_config

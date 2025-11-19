"""
Gradio Web Interface для Trading Alert System с JWT Authentication
Работает с DynamoDB и Google Sheets одновременно
"""
import os
import sys
import asyncio
import re
import logging
from datetime import datetime
from typing import List, Tuple, Optional
import pandas as pd

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import gradio as gr
from models.signal import SignalTarget, ExchangeType, SignalCondition, SignalStatus
from services.sheets_reader import SheetsReader
from storage.dynamodb_storage import DynamoDBStorage
from storage.session_storage import SessionStorage
from services.auth_service import AuthService
from exchanges.binance import BinanceExchange
from exchanges.bybit import BybitExchange
from exchanges.coinbase import CoinbaseExchange
from services.price_checker import PriceChecker
from utils.config import load_config
from utils.logger import setup_logging

# Инициализация
setup_logging()
logger = logging.getLogger(__name__)

# Глобальные переменные
storage = None
sheets_reader = None
exchanges = {}
price_checker = None
auth_service = None
session_storage = None


def init_services():
    """Инициализация всех сервисов включая authentication"""
    global storage, sheets_reader, exchanges, price_checker, auth_service, session_storage

    try:
        # Загружаем конфигурацию
        config = load_config()

        # Инициализируем DynamoDB
        table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-alerts')
        region = os.getenv('DYNAMODB_REGION', 'eu-west-1')
        storage = DynamoDBStorage(table_name=table_name, region=region)
        logger.info(f"✅ DynamoDB initialized: {table_name} in {region}")

        # Инициализируем Session Storage для JWT
        session_storage = SessionStorage(table_name=table_name, region=region)
        logger.info(f"✅ Session Storage initialized")

        # Инициализируем Auth Service
        jwt_secret = os.getenv('JWT_SECRET_KEY', 'default-secret-change-me-in-production')
        auth_service = AuthService(
            session_storage=session_storage,
            secret_key=jwt_secret,
            user_storage=storage  # Передаем DynamoDB для персистентности пользователей
        )
        logger.info(f"✅ Auth Service initialized")

        # Инициализируем Google Sheets
        sheets_reader = SheetsReader()
        if sheets_reader.test_connection():
            logger.info("✅ Google Sheets initialized")
        else:
            logger.warning("⚠️  Google Sheets connection failed")

        # Инициализируем биржи
        async def init_exchanges_async():
            global exchanges, price_checker

            # Загружаем пользователей из DynamoDB в память
            await auth_service.load_users_from_storage()
            logger.info(f"✅ Loaded {len(auth_service.users)} users from DynamoDB")

            # Binance
            if ExchangeType.BINANCE in config.exchanges:
                binance_config = config.get_exchange_config(ExchangeType.BINANCE)
                try:
                    binance = BinanceExchange(
                        api_key=binance_config.api_key,
                        api_secret=binance_config.api_secret
                    )
                    await binance.connect()
                    exchanges[ExchangeType.BINANCE] = binance
                    logger.info("✅ Binance initialized")
                except Exception as e:
                    logger.error(f"❌ Binance failed: {e}")

            # Bybit
            if ExchangeType.BYBIT in config.exchanges:
                bybit_config = config.get_exchange_config(ExchangeType.BYBIT)
                try:
                    bybit = BybitExchange(
                        api_key=bybit_config.api_key,
                        api_secret=bybit_config.api_secret
                    )
                    await bybit.connect()
                    exchanges[ExchangeType.BYBIT] = bybit
                    logger.info("✅ Bybit initialized")
                except Exception as e:
                    logger.error(f"❌ Bybit failed: {e}")

            # Coinbase
            if ExchangeType.COINBASE in config.exchanges:
                coinbase_config = config.get_exchange_config(ExchangeType.COINBASE)
                try:
                    coinbase = CoinbaseExchange(
                        api_key=coinbase_config.api_key,
                        api_secret=coinbase_config.api_secret
                    )
                    await coinbase.connect()
                    exchanges[ExchangeType.COINBASE] = coinbase
                    logger.info("✅ Coinbase initialized")
                except Exception as e:
                    logger.error(f"❌ Coinbase failed: {e}")

            # Price Checker
            price_checker = PriceChecker(exchanges)

        # Запускаем async инициализацию
        asyncio.run(init_exchanges_async())

        return "✅ All services initialized successfully (including JWT Auth)!"

    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return f"❌ Initialization failed: {e}"


# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

async def register_user_async(username: str, password: str) -> str:
    """Регистрация нового пользователя"""
    try:
        if not username or not password:
            return "❌ Username and password are required"

        if len(password) < 8:
            return "❌ Password must be at least 8 characters"

        user = await auth_service.register_user(username, password)

        if user:
            return f"✅ User '{username}' registered successfully! You can now login."
        else:
            return f"❌ Registration failed. User '{username}' may already exist."

    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        return f"❌ Error: {str(e)}"


def register_user(username: str, password: str):
    """Wrapper для регистрации"""
    return asyncio.run(register_user_async(username, password))


async def login_user_async(username: str, password: str) -> Tuple[str, str, bool, str]:
    """
    Логин пользователя

    Returns:
        (message, username, is_authenticated, token)
    """
    try:
        if not username or not password:
            return "❌ Username and password are required", "", False, ""

        # auth_service.login() raises ValueError on failure
        result = await auth_service.login(username, password)

        # Если дошли сюда - логин успешен
        token = result['access_token']
        session_id = result['session_id']
        logger.info(f"✅ User '{username}' logged in successfully (session: {session_id[:8]}...)")

        return f"✅ Welcome, {username}!", username, True, token

    except ValueError as e:
        # Invalid credentials or rate limit
        logger.warning(f"❌ Login failed for '{username}': {e}")
        return f"❌ Login failed: {str(e)}", "", False, ""

    except Exception as e:
        logger.error(f"❌ Unexpected login error: {e}")
        return f"❌ Error: {str(e)}", "", False, ""


def login_user(username: str, password: str):
    """Wrapper для логина"""
    return asyncio.run(login_user_async(username, password))  # Returns (msg, user, is_auth, token)


async def auto_login_async(token: str) -> Tuple[str, str, bool, str]:
    """
    Автоматический логин по сохраненному токену

    Returns:
        (message, username, is_authenticated, token)
    """
    try:
        if not token or token.strip() == "":
            return "", "", False, ""

        # Проверяем токен через auth_service
        payload = await auth_service.validate_token(token)
        username = payload.get('username', '')

        logger.info(f"✅ Auto-login successful for user: {username}")
        return f"✅ Welcome back, {username}!", username, True, token

    except Exception as e:
        # Токен невалиден или истек
        logger.debug(f"Auto-login failed: {e}")
        return "", "", False, ""


def auto_login(token: str):
    """Wrapper для auto-login"""
    return asyncio.run(auto_login_async(token))


def logout_user(current_user: str) -> Tuple[str, str, bool, str]:
    """
    Логаут пользователя

    Returns:
        (message, username, is_authenticated, token)
    """
    try:
        logger.info(f"✅ User '{current_user}' logged out")
        return f"✅ Goodbye, {current_user}!", "", False, ""
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        return f"❌ Error: {str(e)}", "", False


# ============================================================================
# CRUD ОПЕРАЦИИ ДЛЯ СИГНАЛОВ
# ============================================================================

async def create_signal_async(
    exchange: str,
    symbol: str,
    condition: str,
    target_price: float,
    user_id: Optional[str] = None,
    notes: Optional[str] = None,
    save_to_sheets: bool = True
) -> Tuple[str, pd.DataFrame]:
    """Создание нового сигнала"""
    try:
        # Валидация: User ID обязателен
        if not user_id or user_id.strip() == "":
            return "❌ User ID is required! Please enter your username.", get_signals_table()

        # Валидация и автокоррекция символа
        symbol = symbol.strip().upper()  # Автоматически в uppercase

        # Автоматическая обрезка лишних символов после USDT/USDC/USD
        # Если пользователь ввел "BTCUSDTXYZ" → обрезаем до "BTCUSDT"
        for ending in ['USDT', 'USDC', 'USD']:
            idx = symbol.find(ending)
            if idx != -1:
                # Нашли ending, обрезаем всё после него
                symbol = symbol[:idx + len(ending)]
                break

        # Проверка формата символа: BTCUSDT, ETHUSDC, SOLUSD и т.д.
        symbol_pattern = r'^[A-Z]{2,10}(USDT|USDC|USD)$'
        if not re.match(symbol_pattern, symbol):
            return (
                f"❌ Invalid symbol format: '{symbol}'\n"
                f"Expected format: BTCUSDT, ETHUSDC, SOLUSD, etc.\n"
                f"(2-10 letters + USDT/USDC/USD)",
                get_signals_table()
            )

        # Автогенерация имени сигнала: "BTCUSDT > 50000 (Bybit)"
        if condition.lower() == "above":
            condition_symbol = ">"
        elif condition.lower() == "below":
            condition_symbol = "<"
        elif condition.lower() == "equal":
            condition_symbol = "="
        else:
            condition_symbol = "?"
        auto_name = f"{symbol} {condition_symbol} {target_price} ({exchange.capitalize()})"

        # Создаем SignalTarget
        signal = SignalTarget(
            name=auto_name,
            exchange=ExchangeType(exchange.lower()),
            symbol=symbol,  # Уже в uppercase после валидации
            condition=SignalCondition(condition.lower()),
            target_price=target_price,
            user_id=user_id,
            notes=notes
        )

        # Генерируем ID
        signal.id = signal.generate_id()

        # Сохраняем в DynamoDB
        success = await storage.save_signal(signal)

        if not success:
            return "❌ Failed to save to DynamoDB", get_signals_table()

        # Опционально сохраняем в Google Sheets
        if save_to_sheets and sheets_reader:
            try:
                # Формируем данные для Sheets
                row_data = [
                    signal.symbol,
                    signal.condition.value,
                    str(signal.target_price),
                    signal.exchange.value if signal.exchange else '',
                    'TRUE' if signal.active else 'FALSE',
                    user_id or '',
                    notes or ''
                ]

                logger.info("📊 Signal also saved to Google Sheets")
            except Exception as e:
                logger.warning(f"⚠️  Failed to save to Sheets: {e}")

        return f"✅ Signal created: {signal.name} (ID: {signal.id[:8]}...)", get_signals_table(user_id)

    except Exception as e:
        logger.error(f"❌ Error creating signal: {e}")
        return f"❌ Error: {e}", get_signals_table()


def create_signal(
    exchange: str,
    symbol: str,
    condition: str,
    target_price: float,
    user_id: str = "",
    notes: str = "",
    save_to_sheets: bool = True
):
    """Wrapper для создания сигнала (синхронный)"""
    return asyncio.run(
        create_signal_async(exchange, symbol, condition, target_price,
                          user_id or None, notes or None, save_to_sheets)
    )


    import nest_asyncio
    nest_asyncio.apply()
def get_signals_table(user_id: str = "") -> pd.DataFrame:
    """Получение сигналов из DynamoDB с опциональным фильтром по user_id"""
    try:
        signals = asyncio.run(storage.get_all_signals())

        # Фильтруем по user_id если указан
        if user_id and user_id.strip():
            signals = [s for s in signals if s.user_id and s.user_id.strip() == user_id.strip()]

        if not signals:
            return pd.DataFrame(columns=[
                'Name', 'Exchange', 'Symbol', 'Condition',
                'Target Price', 'Status', 'Created', 'Triggered Count'
            ])

        # Формируем DataFrame
        data = []
        for signal in signals:
            data.append({
                'Name': signal.name,
                'Exchange': signal.exchange.value if signal.exchange else 'any',
                'Symbol': signal.symbol,
                'Condition': signal.condition.value,
                'Target Price': f"${signal.target_price:.2f}",
                'Status': 'Active' if signal.active else 'Inactive',
                'Created': signal.created_at.strftime('%Y-%m-%d %H:%M'),
                'Triggered Count': signal.triggered_count
            })

        return pd.DataFrame(data)

    except Exception as e:
        logger.error(f"❌ Error getting signals: {e}")
        return pd.DataFrame(columns=['Error'], data=[[str(e)]])


async def delete_signal_async(signal_id: str, user_id: str = "") -> Tuple[str, pd.DataFrame]:
    """Удаление сигнала"""
    try:
        # Находим сигнал
        signals = await storage.get_all_signals()
        signal_to_delete = None

        for signal in signals:
            if signal.id.startswith(signal_id.replace('...', '')):
                signal_to_delete = signal
                break

        if not signal_to_delete:
            return f"❌ Signal not found: {signal_id}", get_signals_table(user_id)

        # Удаляем
        success = await storage.delete_signal(signal_to_delete.id)

        if success:
            return f"✅ Signal deleted: {signal_to_delete.name}", get_signals_table(user_id)
        else:
            return f"❌ Failed to delete signal", get_signals_table(user_id)

    except Exception as e:
        logger.error(f"❌ Error deleting signal: {e}")
        return f"❌ Error: {e}", get_signals_table(user_id)


def delete_signal(signal_id: str, user_id: str = ""):
    """Wrapper для удаления сигнала"""
    return asyncio.run(delete_signal_async(signal_id, user_id))


async def update_pushover_key_async(username: str, pushover_key: str) -> Tuple[str, dict]:
    """Обновление Pushover ключа пользователя (async)"""
    try:
        if not storage:
            return "❌ Storage not initialized", gr.update()

        if not username:
            return "❌ Please login first", gr.update()

        if not pushover_key or not pushover_key.strip():
            return "❌ Please enter a valid Pushover User Key", gr.update()

        # Сохраняем pushover key в DynamoDB
        await storage.save_user_data(username, {
            "pushover_key": pushover_key.strip()
        })

        # Маскируем ключ для отображения
        masked_key = pushover_key[:4] + "..." + pushover_key[-4:] if len(pushover_key) > 8 else "***"

        return (
            f"✅ Pushover key updated successfully for user: {username}",
            gr.update(value=masked_key, visible=True)  # Показываем поле с замаскированным ключом
        )

    except Exception as e:
        logger.error(f"Error updating Pushover key: {e}")
        return f"❌ Error: {str(e)}", gr.update()


def update_pushover_key(username: str, pushover_key: str):
    """Wrapper для обновления Pushover ключа"""
    return asyncio.run(update_pushover_key_async(username, pushover_key))


def get_user_settings(username: str) -> Tuple[str, str, bool]:
    """Получение настроек пользователя"""
    try:
        if not storage or not username:
            return username or "", "", False

        # Получаем данные пользователя из DynamoDB
        user_data = asyncio.run(storage.get_user_data(username))
        pushover_key = user_data.get('pushover_key', '')

        # Маскируем pushover key для отображения
        if pushover_key:
            masked_key = pushover_key[:4] + "..." + pushover_key[-4:] if len(pushover_key) > 8 else "***"
            show_current_key = True  # Показываем поле если ключ есть
        else:
            masked_key = ""
            show_current_key = False  # Скрываем поле если ключа нет

        return username, masked_key, show_current_key

    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        return username or "", "", False


async def delete_user_account_async(username: str, confirm: bool) -> Tuple[str, bool, bool, bool, str, bool]:
    """Удаление аккаунта пользователя (async)"""
    try:
        if not auth_service or not storage:
            return "❌ Services not initialized", gr.update(), gr.update(), gr.update(), "", False

        if not username:
            return "❌ Please login first", gr.update(), gr.update(), gr.update(), "", False

        if not confirm:
            return "❌ Please confirm by checking the checkbox", gr.update(), gr.update(), gr.update(), username, True

        # 1. Удаляем все сигналы пользователя
        all_signals = await storage.load_signals()
        user_signals = [s for s in all_signals if s.user_id == username]

        for signal in user_signals:
            await storage.delete_signal(signal.id)

        deleted_count = len(user_signals)
        logger.info(f"Deleted {deleted_count} signals for user: {username}")

        # 2. Удаляем данные пользователя
        await auth_service.delete_user(username)

        # Logout - показываем auth форму, скрываем main app
        return (
            f"✅ Account deleted successfully. Deleted {deleted_count} signals.",
            gr.update(visible=True),   # auth_row - показать
            gr.update(visible=False),  # user_info_row - скрыть
            gr.update(visible=False),  # main_app - скрыть
            "",                        # current_user - очистить
            False                      # is_authenticated - false
        )

    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        return f"❌ Error: {str(e)}", gr.update(), gr.update(), gr.update(), username, True


def delete_user_account(username: str, confirm: bool):
    """Wrapper для удаления аккаунта"""
    return asyncio.run(delete_user_account_async(username, confirm))


async def check_price_async(exchange: str, symbol: str) -> str:
    """Проверка текущей цены"""
    try:
        if not price_checker:
            return "❌ Price checker not initialized"

        # Получаем цену
        price_data = await price_checker.get_price(
            ExchangeType(exchange.lower()),
            symbol.upper()
        )

        if not price_data:
            return f"❌ Failed to get price for {symbol} on {exchange}"

        return f"""
✅ Current Price Data:
📊 Symbol: {symbol}
💱 Exchange: {exchange}
💰 Price: ${price_data.price:.8f}
📈 24h Volume: ${price_data.volume_24h:,.2f}
⏰ Time: {price_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""

    except Exception as e:
        logger.error(f"❌ Error checking price: {e}")
        return f"❌ Error: {e}"


def check_price(exchange: str, symbol: str):
    """Wrapper для проверки цены"""
    return asyncio.run(check_price_async(exchange, symbol))


def sync_from_sheets(user_id: str = "") -> Tuple[str, pd.DataFrame]:
    """Синхронизация из Google Sheets в DynamoDB"""
    try:
        if not sheets_reader:
            return "❌ Google Sheets not initialized", get_signals_table(user_id)

        # Читаем из Sheets
        signals_data = sheets_reader.read_signals()

        if not signals_data:
            return "⚠️  No signals found in Google Sheets", get_signals_table(user_id)

        # Сохраняем в DynamoDB
        saved_count = 0
        for signal_dict in signals_data:
            try:
                # Парсим exchange
                exchange = ExchangeType.BYBIT  # default
                if 'exchange' in signal_dict and signal_dict['exchange']:
                    exchange_str = signal_dict['exchange'].lower()
                    if 'binance' in exchange_str:
                        exchange = ExchangeType.BINANCE
                    elif 'bybit' in exchange_str:
                        exchange = ExchangeType.BYBIT
                    elif 'coinbase' in exchange_str:
                        exchange = ExchangeType.COINBASE

                # Парсим condition
                condition_str = signal_dict['condition'].lower()
                if 'above' in condition_str or '>' in condition_str:
                    condition = SignalCondition.ABOVE
                elif 'below' in condition_str or '<' in condition_str:
                    condition = SignalCondition.BELOW
                else:
                    continue

                signal = SignalTarget(
                    name=f"{exchange.value.upper()} {signal_dict['symbol']} {condition.value} ${signal_dict['target_price']}",
                    exchange=exchange,
                    symbol=signal_dict['symbol'].upper(),
                    condition=condition,
                    target_price=float(signal_dict['target_price']),
                    user_id=signal_dict.get('pushover_user_key'),
                    active=signal_dict.get('active', True)
                )

                signal.id = signal.generate_id()

                success = asyncio.run(storage.save_signal(signal))
                if success:
                    saved_count += 1

            except Exception as e:
                logger.error(f"❌ Failed to sync signal: {e}")
                continue

        return f"✅ Synced {saved_count} signals from Google Sheets to DynamoDB", get_signals_table(user_id)

    except Exception as e:
        logger.error(f"❌ Error syncing from sheets: {e}")
        return f"❌ Error: {e}", get_signals_table(user_id)


# ============================================================================
# GRADIO INTERFACE WITH AUTHENTICATION
# ============================================================================

def create_interface():
    """Создание Gradio интерфейса с JWT аутентификацией"""

    # Инициализация при старте
    init_services()  # Initialize all services (DynamoDB, Auth, Exchanges, etc.)

    # Helper function for loading signals into dropdown
    def load_signals_to_dropdown(user_id: str):
        """Загружает сигналы текущего пользователя в dropdown"""
        try:
            import nest_asyncio
            nest_asyncio.apply()
            logger.info(f"🔍 [DROPDOWN] Loading signals for user: '{user_id}'")

            signals = asyncio.run(storage.get_all_signals())
            logger.info(f"📊 [DROPDOWN] Total signals in DB: {len(signals)}")

            # Фильтруем только сигналы текущего пользователя
            if user_id and user_id.strip():
                before_filter = len(signals)
                signals = [s for s in signals if s.user_id and s.user_id.strip() == user_id.strip()]
                logger.info(f"✅ [DROPDOWN] Filtered from {before_filter} to {len(signals)} signals for user '{user_id}'")
            else:
                logger.warning(f"⚠️ [DROPDOWN] user_id is empty!")

            if not signals:
                logger.warning(f"⚠️ [DROPDOWN] No signals found for user: '{user_id}'")
                return gr.update(choices=[], value=None), {}

            # Формируем список и mapping
            choices = []
            mapping = {}
            for signal in signals:
                label = f"{signal.name} ({signal.symbol}, {signal.condition.value}, ${signal.target_price:.2f})"
                choices.append(label)
                mapping[label] = signal.id

            logger.info(f"✅ [DROPDOWN] Successfully loaded {len(choices)} signals into dropdown")
            return gr.update(choices=choices, value=None), mapping

        except Exception as e:
            logger.error(f"❌ [DROPDOWN] Error loading signals: {e}", exc_info=True)
            return gr.update(choices=[], value=None), {}

    with gr.Blocks(title="Trading Signal System with Auth", theme=gr.themes.Soft()) as app:

        gr.Markdown("""
        # 🚀 Trading Signal System
        ### DynamoDB + Google Sheets + JWT Authentication

        Secure access to trading signals with user authentication
        """)

        # State для аутентификации
        current_user = gr.State("")  # Текущий залогиненный пользователь
        is_authenticated = gr.State(False)  # Флаг аутентификации
        auth_token = gr.Textbox(value="", visible=False, elem_id="auth_token")  # JWT токен (скрытый)
        signal_mapping = gr.State({})  # Mapping: label -> signal_id для dropdown

        # ============================================================================
        # AUTHENTICATION UI
        # ============================================================================
        with gr.Row(visible=True) as auth_row:
            with gr.Column(scale=1):
                gr.Markdown("### 🔐 Login")
                login_username = gr.Textbox(label="Username", placeholder="Enter your username")
                login_password = gr.Textbox(label="Password", type="password", placeholder="Enter your password")
                login_btn = gr.Button("Login", variant="primary")
                login_output = gr.Textbox(label="Login Status", interactive=False)

            with gr.Column(scale=1):
                gr.Markdown("### 📝 Register")
                register_username = gr.Textbox(label="Username", placeholder="Choose a username")
                register_password = gr.Textbox(label="Password", type="password", placeholder="Choose a password (min 8 chars)")
                register_btn = gr.Button("Register", variant="secondary")
                register_output = gr.Textbox(label="Registration Status", interactive=False)

        # User info bar (видно только после логина)
        with gr.Row(visible=False) as user_info_row:
            with gr.Column(scale=4):
                user_display = gr.Markdown("**🟢 Logged in as:** Guest")
            with gr.Column(scale=1):
                logout_btn = gr.Button("Logout 🚪", size="sm", variant="secondary")

        # ============================================================================
        # MAIN APP (видно только после логина)
        # ============================================================================
        with gr.Column(visible=False) as main_app:

            # TAB 1: CREATE SIGNAL
            with gr.Tab("📝 Create Signal"):
                gr.Markdown("### Create New Trading Signal")

                with gr.Row():
                    with gr.Column():
                        signal_user_id = gr.Textbox(
                            label="User ID (Auto-filled)",
                            placeholder="Filled automatically after login",
                            info="Your username (auto-filled)",
                            value="",
                            interactive=False  # Read-only, заполняется автоматически
                        )

                        signal_exchange = gr.Dropdown(
                            choices=["binance", "bybit", "coinbase"],
                            label="Exchange",
                            value="bybit",
                            info="Target exchange"
                        )

                        signal_symbol = gr.Textbox(
                            label="Symbol",
                            placeholder="BTCUSDT",
                            info="Trading pair (e.g., BTCUSDT, ETHUSDT)",
                            max_length=15,  # Ограничение длины
                            elem_id="signal_symbol"  # Для JavaScript
                        )

                    with gr.Column():
                        signal_condition = gr.Dropdown(
                            choices=["above", "below", "equal"],
                            label="Condition",
                            value="above",
                            info="Trigger condition: above (>), below (<), equal \(=\)"
                        )

                        signal_target_price = gr.Number(
                            label="Target Price",
                            value=None,
                            info="Price threshold"
                        )

                        signal_notes = gr.Textbox(
                            label="Notes (Optional)",
                            placeholder="Additional information...",
                            lines=1
                        )

                save_to_sheets_check = gr.Checkbox(
                    label="Also save to Google Sheets",
                    value=True,
                    info="Sync to Google Sheets for manual editing"
                )

                create_btn = gr.Button("Create Signal", variant="primary")
                create_output = gr.Textbox(label="Result", lines=2)
                create_table = gr.Dataframe(label="Your Signals")

                create_btn.click(
                    fn=create_signal,
                    inputs=[
                        signal_exchange,
                        signal_symbol,
                        signal_condition,
                        signal_target_price,
                        signal_user_id,
                        signal_notes,
                        save_to_sheets_check
                    ],
                    outputs=[create_output, create_table]
                )

            # TAB 2: VIEW SIGNALS
            with gr.Tab("📊 View Signals"):
                gr.Markdown("### Your Trading Signals")

                refresh_btn = gr.Button("🔄 Refresh", variant="secondary")

                signals_table = gr.Dataframe(
                    label="Trading Signals",
                    value=get_signals_table()
                )

                refresh_btn.click(
                    fn=lambda user: get_signals_table(user),
                    inputs=[current_user],
                    outputs=signals_table
                )

            # TAB 3: DELETE SIGNAL
            with gr.Tab("🗑️ Delete Signal"):
                gr.Markdown("### Delete Trading Signal")

                with gr.Row():
                    load_signals_btn = gr.Button("🔄 Update My Signals", variant="secondary")

                signal_dropdown = gr.Dropdown(
                    label="Select Signal to Delete",
                    choices=[],
                    interactive=True,
                    info="Auto-loaded on login. Click 'Update' to refresh."
                )

                delete_btn = gr.Button("Delete Signal", variant="stop")
                delete_output = gr.Textbox(label="Result", lines=2)
                delete_table = gr.Dataframe(label="Your Signals")

                # Удаление выбранного сигнала
                def delete_selected_signal(selected_label: str, mapping: dict, user_id: str):
                    if not selected_label:
                        return "⚠️ Please select a signal first", get_signals_table(user_id)

                    signal_id = mapping.get(selected_label)
                    if not signal_id:
                        return "❌ Signal not found in mapping", get_signals_table(user_id)

                    return delete_signal(signal_id, user_id)

                load_signals_btn.click(
                    fn=load_signals_to_dropdown,
                    inputs=[current_user],
                    outputs=[signal_dropdown, signal_mapping]
                )

                delete_btn.click(
                    fn=delete_selected_signal,
                    inputs=[signal_dropdown, signal_mapping, current_user],
                    outputs=[delete_output, delete_table]
                )

            # TAB 4: CHECK PRICE
            with gr.Tab("💰 Check Price"):
                gr.Markdown("### Get Current Price from Exchange")

                with gr.Row():
                    price_exchange = gr.Dropdown(
                        choices=["binance", "bybit", "coinbase"],
                        label="Exchange",
                        value="bybit"
                    )

                    price_symbol = gr.Textbox(
                        label="Symbol",
                        placeholder="BTCUSDT",
                        value="BTCUSDT"
                    )

                price_btn = gr.Button("Check Price", variant="primary")
                price_output = gr.Textbox(label="Price Data", lines=8)

                price_btn.click(
                    fn=check_price,
                    inputs=[price_exchange, price_symbol],
                    outputs=price_output
                )

            # TAB 5: SYNC FROM SHEETS
            with gr.Tab("🔄 Sync from Sheets"):
                gr.Markdown("""
                ### Sync Signals from Google Sheets to DynamoDB

                This will read all signals from Google Sheets and save them to DynamoDB.
                """)

                sync_btn = gr.Button("Sync from Google Sheets", variant="primary")
                sync_output = gr.Textbox(label="Result", lines=2)
                sync_table = gr.Dataframe(label="Synced Signals")

                sync_btn.click(
                    fn=sync_from_sheets,
                    inputs=[current_user],
                    outputs=[sync_output, sync_table]
                )

            # TAB 6: SETTINGS
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("### User Settings")

                with gr.Row():
                    with gr.Column():
                        settings_username_display = gr.Textbox(
                            label="Username",
                            value="",
                            interactive=False,
                            info="Your username (read-only)"
                        )

                        settings_pushover_key = gr.Textbox(
                            label="Pushover User Key",
                            placeholder="Enter your Pushover User Key",
                            info="Get your User Key from https://pushover.net",
                            type="password"
                        )

                        settings_current_pushover = gr.Textbox(
                            label="Current Pushover Key",
                            value="",
                            interactive=False,
                            info="Your current Pushover key (masked)",
                            visible=False  # Скрыто по умолчанию, показывается только если ключ уже сохранён
                        )

                        save_pushover_btn = gr.Button("💾 Save Pushover Key", variant="primary")
                        settings_output = gr.Textbox(label="Result", lines=2)

                gr.Markdown("---")
                gr.Markdown("### ⚠️ Danger Zone")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("""
                        **Delete Account**

                        ⚠️ Warning: This action will permanently delete:
                        - Your account
                        - All your signals
                        - All your settings

                        This action **cannot be undone**.
                        """)

                        delete_account_confirm = gr.Checkbox(
                            label="I understand this action cannot be undone",
                            value=False
                        )

                        delete_account_btn = gr.Button("🗑️ Delete My Account", variant="stop")
                        delete_account_output = gr.Textbox(label="Result", lines=2)

                save_pushover_btn.click(
                    fn=lambda user, key: update_pushover_key(user, key),
                    inputs=[current_user, settings_pushover_key],
                    outputs=[settings_output, settings_current_pushover]  # Обновляем и сообщение, и поле Current Pushover Key
                )

                delete_account_btn.click(
                    fn=lambda user, confirm: delete_user_account(user, confirm),
                    inputs=[current_user, delete_account_confirm],
                    outputs=[delete_account_output, auth_row, user_info_row, main_app, current_user, is_authenticated]
                )

        # ============================================================================
        # EVENT HANDLERS - Authentication
        # ============================================================================

        def handle_login(username, password):
            """Обработчик логина"""
            msg, user, is_auth, token = login_user(username, password)

            # Получаем settings для пользователя
            settings_user, masked_pushover, show_pushover_field = get_user_settings(user if is_auth else "")

            return (
                msg,  # login_output
                user,  # current_user (State)
                is_auth,  # is_authenticated (State)
                token,  # auth_token (будет сохранен в localStorage через JS)
                gr.update(visible=not is_auth),  # auth_row
                gr.update(visible=is_auth),  # user_info_row
                gr.update(visible=is_auth),  # main_app
                f"**🟢 Logged in as:** {user}" if is_auth else "**🔴 Not logged in**",  # user_display
                user if is_auth else "",  # signal_user_id (auto-fill)
                get_signals_table(user if is_auth else ""),  # signals_table
                settings_user,  # settings_username_display
                gr.update(value=masked_pushover, visible=show_pushover_field)  # settings_current_pushover - показываем только если ключ сохранён
            )

        def handle_logout(user):
            """Обработчик логаута"""
            msg, empty_user, is_auth, token = logout_user(user)

            return (
                msg,  # Сообщение в login_output
                empty_user,  # current_user (State)
                is_auth,  # is_authenticated (State)
                token,  # auth_token (пустой - будет удален из localStorage через JS)
                gr.update(visible=True),  # auth_row
                gr.update(visible=False),  # user_info_row
                gr.update(visible=False),  # main_app
                "**🔴 Not logged in**",  # user_display
                "",  # signal_user_id (clear)
                get_signals_table(),  # signals_table (show all)
                "",  # settings_username_display (clear)
                gr.update(value="", visible=False)  # settings_current_pushover (скрыть при logout)
            )

        def handle_auto_login(token):
            """Обработчик auto-login при загрузке страницы"""
            msg, user, is_auth, validated_token = auto_login(token)

            # Если auto-login не удался - возвращаем состояние "не залогинен"
            if not is_auth:
                return (
                    "",  # login_output (no message)
                    "",  # current_user
                    False,  # is_authenticated
                    "",  # auth_token (clear)
                    gr.update(visible=True),  # auth_row
                    gr.update(visible=False),  # user_info_row
                    gr.update(visible=False),  # main_app
                    "**🔴 Not logged in**",  # user_display
                    "",  # signal_user_id
                    get_signals_table(),  # signals_table
                    "",  # settings_username_display
                    gr.update(value="", visible=False)  # settings_current_pushover - скрыть при ошибке
                )

            # Auto-login успешен
            settings_user, masked_pushover, show_pushover_field = get_user_settings(user)

            return (
                msg,  # login_output
                user,  # current_user
                is_auth,  # is_authenticated
                validated_token,  # auth_token
                gr.update(visible=False),  # auth_row (hide)
                gr.update(visible=True),  # user_info_row (show)
                gr.update(visible=True),  # main_app (show)
                f"**🟢 Logged in as:** {user}",  # user_display
                user,  # signal_user_id (auto-fill)
                get_signals_table(user),  # signals_table
                settings_user,  # settings_username_display
                gr.update(value=masked_pushover, visible=show_pushover_field)  # settings_current_pushover - показываем только если ключ сохранён
            )

        def handle_register(username, password):
            """Обработчик регистрации"""
            return register_user(username, password)

        # Привязка событий
        login_result = login_btn.click(
            fn=handle_login,
            inputs=[login_username, login_password],
            outputs=[
                login_output,
                current_user,
                is_authenticated,
                auth_token,  # JWT токен
                auth_row,
                user_info_row,
                main_app,
                user_display,
                signal_user_id,
                signals_table,
                settings_username_display,
                settings_current_pushover
            ]
        )

        # После логина - сохраняем токен в localStorage через JavaScript
        login_result.then(
            fn=None,
            inputs=[auth_token],
            outputs=None,
            js="""(token) => {
                if (token && token.trim() !== "") {
                    localStorage.setItem('jwt_token', token);
                    console.log('✅ Token saved to localStorage');
                } else {
                    localStorage.removeItem('jwt_token');
                    console.log('🗑️ Token cleared from localStorage');
                }
                return token;
            }"""
        ).then(
            fn=load_signals_to_dropdown,
            inputs=[current_user],
            outputs=[signal_dropdown, signal_mapping]
        )

        logout_result = logout_btn.click(
            fn=handle_logout,
            inputs=[current_user],
            outputs=[
                login_output,
                current_user,
                is_authenticated,
                auth_token,  # Очищается
                auth_row,
                user_info_row,
                main_app,
                user_display,
                signal_user_id,
                signals_table,
                settings_username_display,
                settings_current_pushover
            ]
        )

        # После logout - удаляем токен из localStorage
        logout_result.then(
            fn=None,
            inputs=[auth_token],
            outputs=None,
            js="""(token) => {
                localStorage.removeItem('jwt_token');
                console.log('🗑️ Token cleared from localStorage (logout)');
                return "";
            }"""
        ).then(
            fn=lambda: (gr.update(choices=[], value=None), {}),
            outputs=[signal_dropdown, signal_mapping]
        )

        register_btn.click(
            fn=handle_register,
            inputs=[register_username, register_password],
            outputs=register_output
        )

        # Auto-load: триггерим загрузку токена при загрузке страницы
        app.load(
            fn=handle_auto_login,
            inputs=[auth_token],
            outputs=[
                login_output,
                current_user,
                is_authenticated,
                auth_token,
                auth_row,
                user_info_row,
                main_app,
                user_display,
                signal_user_id,
                signals_table,
                settings_username_display,
                settings_current_pushover
            ],
            js="""() => {
                const token = localStorage.getItem('jwt_token') || "";
                console.log('📥 [app.load] Token loaded from localStorage:', token ? 'exists (length: ' + token.length + ')' : 'none');
                return token;
            }"""
        ).then(
            fn=load_signals_to_dropdown,
            inputs=[current_user],
            outputs=[signal_dropdown, signal_mapping]
        )

    return app


# ============================================================================
# LAUNCH
# ============================================================================

if __name__ == "__main__":
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # Установите True для публичного доступа
        debug=True
    )



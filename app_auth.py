"""
Gradio Web Interface с системой аутентификации
Полноценная регистрация и вход для пользователей
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict
import pandas as pd
from dotenv import load_dotenv

# Загружаем .env файл ПЕРВЫМ ДЕЛОМ!
load_dotenv()

# Добавляем src в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import gradio as gr
from models.signal import SignalTarget, ExchangeType, SignalCondition
from models.user import UserCreate, UserLogin
from services.auth_service import AuthService
from storage.dynamodb_storage import DynamoDBStorage
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
auth_service = None
exchanges = {}
price_checker = None
current_sessions: Dict[str, str] = {}  # request_id -> session_id mapping


def init_services():
    """Инициализация всех сервисов"""
    global storage, auth_service, exchanges, price_checker

    try:
        # Инициализируем DynamoDB
        table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-alerts')
        region = os.getenv('DYNAMODB_REGION', 'eu-west-1')
        storage = DynamoDBStorage(table_name=table_name, region=region)
        logger.info(f"✅ DynamoDB initialized: {table_name} in {region}")

        # Инициализируем Auth Service
        auth_service = AuthService(storage)
        logger.info("✅ Auth Service initialized")

        # Инициализируем биржи
        async def init_exchanges_async():
            global exchanges, price_checker

            config = load_config()

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

        return "✅ All services initialized successfully!"

    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return f"❌ Initialization failed: {e}"


# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

def register_user(username: str, password: str, email: str = "", full_name: str = "") -> Tuple[str, str]:
    """Регистрация нового пользователя"""
    try:
        logger.info(f"🔍 REGISTRATION ATTEMPT: username='{username}'")

        if not username or not password:
            logger.warning("❌ Empty username or password")
            return "❌ Username and password are required!", "error"

        # Создаем UserCreate
        logger.info(f"📝 Creating UserCreate object for '{username}'")
        user_create = UserCreate(
            username=username,
            password=password,
            email=email if email else None,
            full_name=full_name if full_name else None
        )
        logger.info(f"✅ UserCreate object created successfully")

        # Регистрируем
        logger.info(f"🔄 Calling auth_service.register_user() for '{username}'")
        user = asyncio.run(auth_service.register_user(user_create))

        logger.info(f"📊 auth_service.register_user() returned: {user}")
        logger.info(f"📊 Type of returned value: {type(user)}")
        logger.info(f"📊 Boolean value: {bool(user)}")

        if user:
            logger.info(f"✅ Registration successful for '{username}'")
            return f"✅ User '{username}' registered successfully! Please login.", "success"
        else:
            logger.warning(f"❌ Registration returned None for '{username}' - user may already exist")
            return f"❌ Username '{username}' already exists!", "error"

    except ValueError as e:
        logger.error(f"❌ Validation error for '{username}': {e}")
        return f"❌ Validation error: {str(e)}", "error"
    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR registering user '{username}': {e}", exc_info=True)
        return f"❌ Error: {str(e)}", "error"


def login_user(username: str, password: str, request: gr.Request) -> Tuple[str, str, Dict]:
    """Вход пользователя"""
    try:
        if not username or not password:
            return "❌ Username and password are required!", "error", gr.update(visible=True)

        # Создаем UserLogin
        user_login = UserLogin(username=username, password=password)

        # Логин
        session = asyncio.run(auth_service.login(user_login))

        if session:
            # Сохраняем session_id (в реальности используем cookies/JWT)
            current_sessions[str(request.session_hash)] = session.session_id

            return f"✅ Welcome, {username}!", "success", gr.update(visible=False)
        else:
            return "❌ Invalid username or password!", "error", gr.update(visible=True)

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return f"❌ Error: {str(e)}", "error", gr.update(visible=True)


def logout_user(request: gr.Request) -> Tuple[str, Dict]:
    """Выход пользователя"""
    try:
        session_hash = str(request.session_hash)
        if session_hash in current_sessions:
            session_id = current_sessions[session_hash]
            auth_service.logout(session_id)
            del current_sessions[session_hash]
            return "✅ Logged out successfully!", gr.update(visible=True)
        return "❌ Not logged in", gr.update(visible=True)
    except Exception as e:
        return f"❌ Error: {str(e)}", gr.update(visible=True)


def get_current_username(request: gr.Request) -> Optional[str]:
    """Получить текущего пользователя"""
    session_hash = str(request.session_hash)
    if session_hash not in current_sessions:
        return None

    session_id = current_sessions[session_hash]
    return auth_service.validate_session(session_id)


# ============================================================================
# SIGNAL FUNCTIONS (требуют авторизации)
# ============================================================================

async def create_signal_async(
    name: str,
    exchange: str,
    symbol: str,
    condition: str,
    target_price: float,
    notes: Optional[str],
    request: gr.Request
) -> Tuple[str, pd.DataFrame]:
    """Создание нового сигнала (только для авторизованных)"""
    try:
        # Проверяем авторизацию
        username = get_current_username(request)
        if not username:
            return "❌ Please login first!", pd.DataFrame()

        # Создаем SignalTarget
        signal = SignalTarget(
            name=name,
            exchange=ExchangeType(exchange.lower()),
            symbol=symbol.upper(),
            condition=SignalCondition(condition.lower()),
            target_price=target_price,
            user_id=username,  # Используем username из сессии
            notes=notes
        )

        # Генерируем ID
        signal.id = signal.generate_id()

        # Сохраняем в DynamoDB
        success = await storage.save_signal(signal)

        if success:
            return f"✅ Signal created: {signal.name}", await get_user_signals(request)
        else:
            return "❌ Failed to save signal", await get_user_signals(request)

    except Exception as e:
        logger.error(f"Error creating signal: {e}")
        return f"❌ Error: {e}", await get_user_signals(request)


def create_signal(name: str, exchange: str, symbol: str, condition: str,
                 target_price: float, notes: str, request: gr.Request):
    """Wrapper для создания сигнала"""
    return asyncio.run(create_signal_async(name, exchange, symbol, condition,
                                           target_price, notes or None, request))


async def get_user_signals(request: gr.Request) -> pd.DataFrame:
    """Получение сигналов текущего пользователя"""
    try:
        username = get_current_username(request)
        if not username:
            return pd.DataFrame(columns=['Please login to view signals'])

        # Получаем все сигналы
        all_signals = await storage.get_all_signals()

        # Фильтруем по текущему пользователю
        user_signals = [s for s in all_signals if s.user_id == username]

        if not user_signals:
            return pd.DataFrame(columns=[
                'ID', 'Name', 'Exchange', 'Symbol', 'Condition',
                'Target Price', 'Status', 'Created'
            ])

        # Формируем DataFrame
        data = []
        for signal in user_signals:
            data.append({
                'ID': signal.id[:8] + '...',
                'Name': signal.name,
                'Exchange': signal.exchange.value,
                'Symbol': signal.symbol,
                'Condition': signal.condition.value,
                'Target Price': f"${signal.target_price:.2f}",
                'Status': 'Active' if signal.active else 'Inactive',
                'Created': signal.created_at.strftime('%Y-%m-%d %H:%M')
            })

        return pd.DataFrame(data)

    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return pd.DataFrame(columns=['Error'], data=[[str(e)]])


def refresh_signals(request: gr.Request):
    """Обновить список сигналов"""
    return asyncio.run(get_user_signals(request))


async def delete_signal_async(signal_id: str, request: gr.Request) -> Tuple[str, pd.DataFrame]:
    """Удаление сигнала"""
    try:
        username = get_current_username(request)
        if not username:
            return "❌ Please login first!", pd.DataFrame()

        # Находим сигнал
        signals = await storage.get_all_signals()
        signal_to_delete = None

        for signal in signals:
            if signal.id.startswith(signal_id.replace('...', '')) and signal.user_id == username:
                signal_to_delete = signal
                break

        if not signal_to_delete:
            return f"❌ Signal not found or access denied: {signal_id}", await get_user_signals(request)

        # Удаляем
        success = await storage.delete_signal(signal_to_delete.id)

        if success:
            return f"✅ Signal deleted: {signal_to_delete.name}", await get_user_signals(request)
        else:
            return "❌ Failed to delete signal", await get_user_signals(request)

    except Exception as e:
        logger.error(f"Error deleting signal: {e}")
        return f"❌ Error: {e}", await get_user_signals(request)


def delete_signal(signal_id: str, request: gr.Request):
    """Wrapper для удаления сигнала"""
    return asyncio.run(delete_signal_async(signal_id, request))


# ============================================================================
# GRADIO INTERFACE
# ============================================================================

def create_interface():
    """Создание Gradio интерфейса с авторизацией"""

    # Инициализация при старте
    init_status = init_services()

    with gr.Blocks(title="Trading Signal System - Auth", theme=gr.themes.Soft()) as app:

        gr.Markdown("""
        # 🔐 Trading Signal System with Authentication
        ### Secure multi-user platform for trading alerts
        """)

        # Статус инициализации
        with gr.Accordion("System Status", open=False):
            gr.Markdown(f"```\n{init_status}\n```")

        # Главные вкладки
        with gr.Tabs() as main_tabs:

            # ============================================================================
            # TAB: AUTH (Login/Register)
            # ============================================================================
            with gr.Tab("🔐 Login / Register") as auth_tab:

                auth_status = gr.Textbox(label="Status", interactive=False)

                with gr.Row():
                    # ЛОГИН
                    with gr.Column():
                        gr.Markdown("### Login")
                        login_username = gr.Textbox(label="Username", placeholder="your_username")
                        login_password = gr.Textbox(label="Password", type="password")
                        login_btn = gr.Button("Login", variant="primary")

                    # РЕГИСТРАЦИЯ
                    with gr.Column():
                        gr.Markdown("### Register New Account")
                        reg_username = gr.Textbox(label="Username", placeholder="Choose username")
                        reg_password = gr.Textbox(
                            label="Password",
                            type="password",
                            info="Min 8 chars, include uppercase, lowercase, and digit"
                        )
                        reg_email = gr.Textbox(label="Email (optional)", placeholder="email@example.com")
                        reg_full_name = gr.Textbox(label="Full Name (optional)")
                        register_btn = gr.Button("Register", variant="secondary")

                # Привязка функций авторизации
                login_btn.click(
                    fn=login_user,
                    inputs=[login_username, login_password],
                    outputs=[auth_status, gr.State(), auth_tab]
                )

                register_btn.click(
                    fn=register_user,
                    inputs=[reg_username, reg_password, reg_email, reg_full_name],
                    outputs=[auth_status, gr.State()]
                )

            # ============================================================================
            # TAB: CREATE SIGNAL (требует авторизации)
            # ============================================================================
            with gr.Tab("📝 Create Signal"):
                gr.Markdown("### Create New Trading Signal")

                with gr.Row():
                    with gr.Column():
                        signal_name = gr.Textbox(label="Signal Name", placeholder="My BTC Alert")
                        signal_exchange = gr.Dropdown(
                            choices=["binance", "bybit", "coinbase"],
                            label="Exchange",
                            value="bybit"
                        )
                        signal_symbol = gr.Textbox(label="Symbol", placeholder="BTCUSDT")

                    with gr.Column():
                        signal_condition = gr.Dropdown(
                            choices=["above", "below"],
                            label="Condition",
                            value="above"
                        )
                        signal_target_price = gr.Number(label="Target Price", value=50000.0)

                signal_notes = gr.Textbox(label="Notes (Optional)", lines=2)
                create_btn = gr.Button("Create Signal", variant="primary")
                create_output = gr.Textbox(label="Result", lines=2)
                create_table = gr.Dataframe(label="Your Signals")

                create_btn.click(
                    fn=create_signal,
                    inputs=[signal_name, signal_exchange, signal_symbol, signal_condition,
                           signal_target_price, signal_notes],
                    outputs=[create_output, create_table]
                )

            # ============================================================================
            # TAB: VIEW SIGNALS
            # ============================================================================
            with gr.Tab("📊 My Signals"):
                gr.Markdown("### Your Trading Signals")

                refresh_btn = gr.Button("🔄 Refresh", variant="primary")
                signals_table = gr.Dataframe(label="My Signals")

                refresh_btn.click(
                    fn=refresh_signals,
                    outputs=signals_table
                )

            # ============================================================================
            # TAB: DELETE SIGNAL
            # ============================================================================
            with gr.Tab("🗑️ Delete Signal"):
                gr.Markdown("### Delete Trading Signal")

                delete_id = gr.Textbox(
                    label="Signal ID",
                    placeholder="Enter short ID (e.g., a1b2c3d4...)"
                )
                delete_btn = gr.Button("Delete Signal", variant="stop")
                delete_output = gr.Textbox(label="Result", lines=2)
                delete_table = gr.Dataframe(label="Your Signals")

                delete_btn.click(
                    fn=delete_signal,
                    inputs=delete_id,
                    outputs=[delete_output, delete_table]
                )

            # ============================================================================
            # TAB: LOGOUT
            # ============================================================================
            with gr.Tab("🚪 Logout"):
                gr.Markdown("### Logout from your account")
                logout_btn = gr.Button("Logout", variant="stop")
                logout_status = gr.Textbox(label="Status")

                logout_btn.click(
                    fn=logout_user,
                    outputs=[logout_status, auth_tab]
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
        share=False,
        debug=True
    )

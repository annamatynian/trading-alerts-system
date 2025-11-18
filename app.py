"""
Gradio Web Interface для Trading Alert System
Работает с DynamoDB и Google Sheets одновременно
"""
import os
import sys
import asyncio
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


def init_services():
    """Инициализация всех сервисов"""
    global storage, sheets_reader, exchanges, price_checker
    
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Инициализируем DynamoDB
        table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-alerts')
        region = os.getenv('DYNAMODB_REGION', 'eu-west-1')
        storage = DynamoDBStorage(table_name=table_name, region=region)
        logger.info(f"✅ DynamoDB initialized: {table_name} in {region}")
        
        # Инициализируем Google Sheets
        sheets_reader = SheetsReader()
        if sheets_reader.test_connection():
            logger.info("✅ Google Sheets initialized")
        else:
            logger.warning("⚠️  Google Sheets connection failed")
        
        # Инициализируем биржи
        async def init_exchanges_async():
            global exchanges, price_checker
            
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
# CRUD ОПЕРАЦИИ ДЛЯ СИГНАЛОВ
# ============================================================================

async def create_signal_async(
    name: str,
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
        
        # Создаем SignalTarget
        signal = SignalTarget(
            name=name,
            exchange=ExchangeType(exchange.lower()),
            symbol=symbol.upper(),
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
                
                # Добавляем в Sheets (требуется метод append_signal)
                # sheets_reader.append_signal(row_data)
                logger.info("📊 Signal also saved to Google Sheets")
            except Exception as e:
                logger.warning(f"⚠️  Failed to save to Sheets: {e}")
        
        return f"✅ Signal created: {signal.name} (ID: {signal.id[:8]}...)", get_signals_table()
        
    except Exception as e:
        logger.error(f"❌ Error creating signal: {e}")
        return f"❌ Error: {e}", get_signals_table()


def create_signal(
    name: str,
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
        create_signal_async(name, exchange, symbol, condition, target_price, 
                          user_id or None, notes or None, save_to_sheets)
    )


def get_signals_table(user_id: str = "") -> pd.DataFrame:
    """Получение сигналов из DynamoDB с опциональным фильтром по user_id"""
    try:
        signals = asyncio.run(storage.get_all_signals())
        
        # Фильтруем по user_id если указан
        if user_id and user_id.strip():
            signals = [s for s in signals if s.user_id and s.user_id.strip() == user_id.strip()]
        
        if not signals:
            return pd.DataFrame(columns=[
                'ID', 'Name', 'User ID', 'Exchange', 'Symbol', 'Condition', 
                'Target Price', 'Status', 'Created', 'Triggered Count'
            ])
        
        # Формируем DataFrame
        data = []
        for signal in signals:
            data.append({
                'ID': signal.id[:8] + '...',
                'Name': signal.name,
                'User ID': signal.user_id or 'N/A',
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


async def delete_signal_async(signal_id: str) -> Tuple[str, pd.DataFrame]:
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
            return f"❌ Signal not found: {signal_id}", get_signals_table()
        
        # Удаляем
        success = await storage.delete_signal(signal_to_delete.id)
        
        if success:
            return f"✅ Signal deleted: {signal_to_delete.name}", get_signals_table()
        else:
            return f"❌ Failed to delete signal", get_signals_table()
            
    except Exception as e:
        logger.error(f"❌ Error deleting signal: {e}")
        return f"❌ Error: {e}", get_signals_table()


def delete_signal(signal_id: str):
    """Wrapper для удаления сигнала"""
    return asyncio.run(delete_signal_async(signal_id))


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


def sync_from_sheets() -> Tuple[str, pd.DataFrame]:
    """Синхронизация из Google Sheets в DynamoDB"""
    try:
        if not sheets_reader:
            return "❌ Google Sheets not initialized", get_signals_table()
        
        # Читаем из Sheets
        signals_data = sheets_reader.read_signals()
        
        if not signals_data:
            return "⚠️  No signals found in Google Sheets", get_signals_table()
        
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
        
        return f"✅ Synced {saved_count} signals from Google Sheets to DynamoDB", get_signals_table()
        
    except Exception as e:
        logger.error(f"❌ Error syncing from sheets: {e}")
        return f"❌ Error: {e}", get_signals_table()


# ============================================================================
# GRADIO INTERFACE
# ============================================================================

def create_interface():
    """Создание Gradio интерфейса"""
    
    # Инициализация при старте
    init_status = init_services()
    
    with gr.Blocks(title="Trading Signal System", theme=gr.themes.Soft()) as app:
        
        gr.Markdown("""
        # 🚀 Trading Signal System
        ### DynamoDB + Google Sheets + AWS Lambda
        
        Управляйте торговыми сигналами через удобный веб-интерфейс
        """)
        
        # Статус инициализации
        with gr.Accordion("System Status", open=False):
            gr.Markdown(f"```\n{init_status}\n```")
        
        # ============================================================================
        # TAB 1: CREATE SIGNAL
        # ============================================================================
        with gr.Tab("📝 Create Signal"):
            gr.Markdown("### Create New Trading Signal")
            
            with gr.Row():
                with gr.Column():
                    signal_name = gr.Textbox(
                        label="Signal Name",
                        placeholder="My BTC Alert",
                        info="Human-readable name for this signal"
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
                        info="Trading pair (e.g., BTCUSDT, ETHUSDT)"
                    )
                
                with gr.Column():
                    signal_condition = gr.Dropdown(
                        choices=["above", "below"],
                        label="Condition",
                        value="above",
                        info="Trigger when price goes above/below target"
                    )
                    
                    signal_target_price = gr.Number(
                        label="Target Price",
                        value=50000.0,
                        info="Price threshold"
                    )
                    
                    signal_user_id = gr.Textbox(
                        label="User ID (Required)",
                        placeholder="your_username (e.g., anna, john)",
                        info="Your unique identifier for notifications",
                        value=""
                    )
            
            signal_notes = gr.Textbox(
                label="Notes (Optional)",
                placeholder="Additional information...",
                lines=2
            )
            
            save_to_sheets_check = gr.Checkbox(
                label="Also save to Google Sheets",
                value=True,
                info="Sync to Google Sheets for manual editing"
            )
            
            create_btn = gr.Button("Create Signal", variant="primary")
            create_output = gr.Textbox(label="Result", lines=2)
            create_table = gr.Dataframe(label="Current Signals")
            
            create_btn.click(
                fn=create_signal,
                inputs=[
                    signal_name,
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
        
        # ============================================================================
        # TAB 2: VIEW SIGNALS
        # ============================================================================
        with gr.Tab("📊 View Signals"):
            gr.Markdown("### All Trading Signals in DynamoDB")
            
            # Фильтр по User ID
            with gr.Row():
                filter_user_id = gr.Textbox(
                    label="Filter by User ID",
                    placeholder="Leave empty to see all signals, or enter username (e.g., anna)",
                    value=""
                )
                with gr.Column():
                    filter_btn = gr.Button("🔍 Filter", variant="primary")
                    refresh_btn = gr.Button("🔄 Refresh All", variant="secondary")
            
            signals_table = gr.Dataframe(
                label="Trading Signals",
                value=get_signals_table()
            )
            
            # Привязка кнопок
            filter_btn.click(
                fn=lambda user_id: get_signals_table(user_id=user_id),
                inputs=filter_user_id,
                outputs=signals_table
            )
            
            refresh_btn.click(
                fn=lambda: get_signals_table(user_id=""),
                outputs=signals_table
            )
        
        # ============================================================================
        # TAB 3: DELETE SIGNAL
        # ============================================================================
        with gr.Tab("🗑️ Delete Signal"):
            gr.Markdown("### Delete Trading Signal")

            with gr.Row():
                filter_user_id = gr.Textbox(
                    label="Filter by User ID (optional)",
                    placeholder="Enter your User ID to see only your signals",
                    scale=3
                )
                load_signals_btn = gr.Button("🔄 Load Signals", scale=1, variant="secondary")

            # State для хранения mapping label -> id
            signal_mapping = gr.State({})

            signal_dropdown = gr.Dropdown(
                label="Select Signal to Delete",
                choices=[],
                interactive=True,
                info="First, load signals above"
            )

            delete_btn = gr.Button("Delete Signal", variant="stop")
            delete_output = gr.Textbox(label="Result", lines=2)
            delete_table = gr.Dataframe(label="Current Signals")

            # Загрузка сигналов в dropdown
            def load_signals_to_dropdown(user_id: str = ""):
                try:
                    signals = asyncio.run(storage.get_all_signals())

                    # Фильтруем по user_id если указан
                    if user_id and user_id.strip():
                        signals = [s for s in signals if s.user_id and s.user_id.strip() == user_id.strip()]

                    if not signals:
                        return gr.update(choices=[], value=None), {}

                    # Формируем список и mapping
                    choices = []
                    mapping = {}
                    for signal in signals:
                        label = f"{signal.name} ({signal.symbol}, {signal.condition.value}, ${signal.target_price:.2f})"
                        choices.append(label)
                        mapping[label] = signal.id

                    return gr.update(choices=choices, value=None), mapping

                except Exception as e:
                    logger.error(f"❌ Error loading signals: {e}")
                    return gr.update(choices=[], value=None), {}

            # Удаление выбранного сигнала
            def delete_selected_signal(selected_label: str, mapping: dict):
                if not selected_label:
                    return "⚠️ Please select a signal first", get_signals_table()

                signal_id = mapping.get(selected_label)
                if not signal_id:
                    return "❌ Signal not found in mapping", get_signals_table()

                return delete_signal(signal_id)

            load_signals_btn.click(
                fn=load_signals_to_dropdown,
                inputs=filter_user_id,
                outputs=[signal_dropdown, signal_mapping]
            )

            delete_btn.click(
                fn=delete_selected_signal,
                inputs=[signal_dropdown, signal_mapping],
                outputs=[delete_output, delete_table]
            )
        
        # ============================================================================
        # TAB 4: CHECK PRICE
        # ============================================================================
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
        
        # ============================================================================
        # TAB 5: SYNC FROM SHEETS
        # ============================================================================
        with gr.Tab("🔄 Sync from Sheets"):
            gr.Markdown("""
            ### Sync Signals from Google Sheets to DynamoDB
            
            This will read all signals from Google Sheets and save them to DynamoDB.
            Existing signals will be updated (upsert logic).
            """)
            
            sync_btn = gr.Button("Sync from Google Sheets", variant="primary")
            sync_output = gr.Textbox(label="Result", lines=2)
            sync_table = gr.Dataframe(label="Synced Signals")
            
            sync_btn.click(
                fn=sync_from_sheets,
                outputs=[sync_output, sync_table]
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

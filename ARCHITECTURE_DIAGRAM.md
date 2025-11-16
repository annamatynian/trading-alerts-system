# 🏗️ АРХИТЕКТУРА СИСТЕМЫ - Вариант 3 (Максимальная гибкость)

## 📐 Общая схема

```
┌─────────────────────────────────────────────────────────────────────┐
│                      TRADING ALERT SYSTEM                            │
│                   (DynamoDB + Lambda + Gradio + Sheets)              │
└─────────────────────────────────────────────────────────────────────┘

                          ┌──────────────┐
                          │ Google Sheets│  
                          │  (Optional)  │  ← Администраторы: быстрое редактирование
                          └──────┬───────┘
                                 │
                                 │ Sync (manual)
                                 ↓
┌────────────────────────────────────────────────────────────────────┐
│                         DYNAMODB TABLE                              │
│                      (trading-alerts)                               │
│                  ← ЕДИНЫЙ ИСТОЧНИК ДАННЫХ →                        │
└───────┬────────────────────────────────────────────┬───────────────┘
        │                                             │
        │                                             │
        ↓                                             ↓
┌──────────────┐                              ┌──────────────┐
│ AWS LAMBDA   │                              │  GRADIO UI   │
│ (Auto Check) │                              │  (Web UI)    │
└──────┬───────┘                              └──────┬───────┘
       │                                             │
       │ ┌────────────────────┐                     │
       │ │ EventBridge (Cron) │                     │
       │ │  Every 1 hour      │                     │
       │ └────────────────────┘                     │
       │                                             │
       ↓                                             ↓
┌──────────────┐                              ┌──────────────┐
│  Read Signals│                              │ User Actions │
│  from DynamoDB                              │ - Create     │
│     ↓        │                              │ - View       │
│ Check Prices │                              │ - Delete     │
│  (Exchanges) │                              │ - Check Price│
│     ↓        │                              │ - Sync Sheets│
│ Send Pushover│                              └──────────────┘
│ Notifications│
└──────────────┘

        ↓                                             ↓
┌──────────────┐                              ┌──────────────┐
│  EXCHANGES   │                              │    USERS     │
├──────────────┤                              ├──────────────┤
│ • Binance    │                              │ Web Browser  │
│ • Bybit      │                              │ localhost:   │
│ • Coinbase   │                              │   7860       │
└──────────────┘                              └──────────────┘
```

---

## 🔄 Data Flow

### Flow 1: Создание сигнала через Gradio

```
User (Browser)
    ↓
Gradio UI: "Create Signal" form
    ↓
gradio_app.py: create_signal_async()
    ↓
DynamoDBStorage.save_signal()
    ↓
AWS DynamoDB Table: "trading-alerts"
    ↓
[Optional] Google Sheets: append row
    ↓
SUCCESS ✅
```

### Flow 2: Автоматическая проверка Lambda

```
EventBridge Rule (hourly)
    ↓
AWS Lambda: lambda_function.handler()
    ↓
DynamoDBStorage.get_all_signals()
    ↓
DynamoDB: read all active signals
    ↓
For each signal:
    ↓
    PriceChecker.get_price(exchange, symbol)
    ↓
    Exchange API (Binance/Bybit/Coinbase)
    ↓
    Compare: current_price vs target_price
    ↓
    If triggered:
        ↓
        Notifier.send_pushover()
        ↓
        Pushover API → User's phone 📱
        ↓
        DynamoDBStorage.update_signal_status()
```

### Flow 3: Синхронизация из Google Sheets

```
User: Edit Google Sheets
    ↓
Gradio UI: "Sync from Sheets" button
    ↓
SheetsReader.read_signals()
    ↓
Google Sheets API: fetch all rows
    ↓
Parse rows → SignalTarget objects
    ↓
For each signal:
    DynamoDBStorage.save_signal()
    ↓
DynamoDB: upsert signals
    ↓
SUCCESS ✅
```

---

## 🧩 Компоненты системы

### 1. **DynamoDB Table** (Центральное хранилище)

```
Table Name: trading-alerts
Partition Key: id (String)

Signal Attributes:
├── id: unique identifier (UUID)
├── name: signal name
├── exchange: binance | bybit | coinbase
├── symbol: BTCUSDT, ETHUSDT, etc.
├── condition: above | below
├── target_price: float
├── active: boolean
├── user_id: Pushover user key
├── created_at: timestamp
├── updated_at: timestamp
├── triggered_count: int
├── last_triggered: timestamp (optional)
└── notes: string (optional)
```

### 2. **AWS Lambda** (Автоматизация)

```
Function Name: trading-alerts-checker
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60 seconds
Region: us-east-2 (избегает блокировки от бирж)

Triggers:
└── EventBridge Rule: rate(1 hour)

Permissions:
├── DynamoDB: Read/Write on trading-alerts table
├── Secrets Manager: Read exchange API keys
├── CloudWatch Logs: Write logs
└── VPC: None (public internet for exchange APIs)

Environment Variables:
├── DYNAMODB_TABLE_NAME=trading-alerts
├── DYNAMODB_REGION=us-east-2
└── [Exchange keys loaded from Secrets Manager]
```

### 3. **Gradio UI** (Веб-интерфейс)

```
Application: gradio_app.py
Framework: Gradio 4.x
Port: 7860 (default)

Tabs:
├── Create Signal   ← форма создания
├── View Signals    ← таблица просмотра
├── Delete Signal   ← удаление по ID
├── Check Price     ← real-time цены
└── Sync from Sheets ← массовая загрузка

Services Used:
├── DynamoDBStorage  ← основное хранилище
├── SheetsReader     ← Google Sheets API
├── PriceChecker     ← проверка цен с бирж
└── Exchange APIs    ← Binance, Bybit, Coinbase
```

### 4. **Google Sheets** (Опционально)

```
Purpose: Быстрое редактирование администраторами
Access: Service Account (JSON credentials)

Columns:
├── Symbol        (BTCUSDT)
├── Condition     (above/below)
├── Target Price  (50000)
├── Exchange      (bybit)
├── Active        (TRUE/FALSE)
├── User Key      (Pushover)
└── Notes         (optional)

Sync:
└── Manual via Gradio "Sync from Sheets" button
```

### 5. **Exchange APIs**

```
Supported Exchanges:
├── Binance
│   ├── Endpoint: api.binance.com
│   ├── Symbols: BTCUSDT, ETHUSDT, etc.
│   └── Fallback: api1.binance.com, api2.binance.com
│
├── Bybit
│   ├── Endpoint: api.bybit.com
│   ├── Symbols: BTCUSDT, ETHUSDT, etc.
│   └── Fallback: api-testnet.bybit.com
│
└── Coinbase
    ├── Endpoint: api.coinbase.com
    ├── Symbols: BTC-USD, ETH-USD, etc.
    └── Symbol conversion: BTCUSDT → BTC-USD
```

### 6. **Notification System**

```
Service: Pushover
API: https://api.pushover.net/1/messages.json

Notification Format:
┌──────────────────────────────┐
│ 🚨 Price Alert Triggered!    │
│                              │
│ Signal: BTC above 50k        │
│ Exchange: Bybit              │
│ Symbol: BTCUSDT              │
│ Current: $51,234.56          │
│ Target: $50,000.00           │
│ Time: 2025-11-14 11:45       │
└──────────────────────────────┘
```

---

## 🔐 Security & Credentials

### AWS Secrets Manager

```
Secrets stored:
├── trading-alerts/binance
│   ├── api_key
│   └── api_secret
│
├── trading-alerts/bybit
│   ├── api_key
│   └── api_secret
│
├── trading-alerts/coinbase
│   ├── api_key
│   └── api_secret
│
├── trading-alerts/pushover
│   ├── app_token
│   └── user_key (default)
│
└── trading-alerts/google-sheets
    └── credentials_json
```

### Local .env file (for Gradio)

```
# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
DYNAMODB_TABLE_NAME=trading-alerts
DYNAMODB_REGION=us-east-2

# Exchanges (at least one required)
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
COINBASE_API_KEY=...
COINBASE_API_SECRET=...

# Pushover
PUSHOVER_APP_TOKEN=...
PUSHOVER_USER_KEY=...

# Google Sheets (optional)
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials.json
GOOGLE_SPREADSHEET_ID=...
```

---

## 🚀 Deployment Architecture

### Current Setup (Working)

```
┌─────────────────────────────────────────────┐
│           AWS Cloud (us-east-2)             │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │         Lambda Function               │ │
│  │  trading-alerts-checker               │ │
│  │  ├── Trigger: EventBridge (hourly)    │ │
│  │  ├── Runtime: Python 3.11             │ │
│  │  ├── Package: S3 deployment           │ │
│  │  └── Size: ~50MB (with dependencies)  │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │       DynamoDB Table                  │ │
│  │  trading-alerts                       │ │
│  │  ├── Partition Key: id                │ │
│  │  ├── Billing: On-Demand               │ │
│  │  └── Capacity: Auto-scaling           │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │      Secrets Manager                  │ │
│  │  ├── Exchange API keys                │ │
│  │  ├── Pushover credentials             │ │
│  │  └── Google Sheets credentials        │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │      CloudWatch                       │ │
│  │  ├── Logs                             │ │
│  │  ├── Metrics                          │ │
│  │  └── Alarms (optional)                │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│         Local / Cloud (Gradio)              │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │       Gradio Application              │ │
│  │  gradio_app.py                        │ │
│  │  ├── Host: localhost:7860 OR          │ │
│  │  │         Hugging Face Spaces        │ │
│  │  ├── Access: DynamoDB (boto3)         │ │
│  │  └── UI: Create/View/Delete signals   │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│         External Services                   │
│                                             │
│  ├── Google Sheets API                     │
│  ├── Binance API                           │
│  ├── Bybit API                             │
│  ├── Coinbase API                          │
│  └── Pushover API                          │
└─────────────────────────────────────────────┘
```

---

## 🎯 Use Cases & Workflows

### Use Case 1: Quick Alert через Gradio

```
Admin opens Gradio UI
    ↓
Create Signal form:
- Symbol: BTCUSDT
- Condition: above
- Target: 50000
- Exchange: bybit
    ↓
Click "Create Signal"
    ↓
Saved to DynamoDB ✅
    ↓
Lambda checks hourly
    ↓
When BTC > 50k → Pushover notification 📱
```

### Use Case 2: Bulk Management через Google Sheets

```
Admin opens Google Sheets
    ↓
Add multiple rows:
ETHUSDT  | above | 3000  | binance | TRUE
SOLUSDT  | above | 150   | bybit   | TRUE
ADAUSDT  | below | 0.5   | coinbase| TRUE
    ↓
Save changes
    ↓
Open Gradio → Sync from Sheets
    ↓
All signals loaded to DynamoDB ✅
    ↓
Lambda monitors all signals
```

### Use Case 3: Price Monitoring

```
User opens Gradio
    ↓
Tab: "Check Price"
    ↓
Select: Exchange=bybit, Symbol=BTCUSDT
    ↓
Click "Check Price"
    ↓
Real-time price from Bybit API ✅
    ↓
Display: price, volume, timestamp
```

---

## 📊 Data Models

### SignalTarget (Pydantic Model)

```python
class SignalTarget(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    exchange: ExchangeType  # binance | bybit | coinbase
    symbol: str  # BTCUSDT, ETHUSDT, etc.
    condition: SignalCondition  # above | below
    target_price: float
    active: bool = True
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    triggered_count: int = 0
    last_triggered: Optional[datetime] = None
    notes: Optional[str] = None
```

### PriceData (Pydantic Model)

```python
class PriceData(BaseModel):
    exchange: ExchangeType
    symbol: str
    price: float
    volume_24h: float
    timestamp: datetime
    raw_data: Dict[str, Any] = {}
```

---

## 🔧 Configuration

### Lambda Environment Variables

```python
DYNAMODB_TABLE_NAME = "trading-alerts"
DYNAMODB_REGION = "us-east-2"
```

### Gradio .env Variables

```python
# AWS
AWS_ACCESS_KEY_ID = "AKIA..."
AWS_SECRET_ACCESS_KEY = "..."
DYNAMODB_TABLE_NAME = "trading-alerts"
DYNAMODB_REGION = "us-east-2"

# At least one exchange
BYBIT_API_KEY = "..."
BYBIT_API_SECRET = "..."

# Optional
PUSHOVER_APP_TOKEN = "..."
GOOGLE_SHEETS_CREDENTIALS_PATH = "./credentials.json"
```

---

## 🎉 SUMMARY

### Что работает:

✅ **AWS Lambda** - автоматическая проверка каждый час  
✅ **DynamoDB** - надежное хранилище сигналов  
✅ **Gradio UI** - красивый веб-интерфейс  
✅ **Google Sheets** - быстрое редактирование (опционально)  
✅ **Multi-Exchange** - Binance, Bybit, Coinbase  
✅ **Pushover** - мгновенные уведомления  

### Архитектурные преимущества:

- **Децентрализация** - Lambda и Gradio работают независимо
- **Гибкость** - можно управлять через UI или Sheets
- **Надежность** - DynamoDB как единый источник правды
- **Масштабируемость** - легко добавлять новые биржи
- **Безопасность** - Secrets Manager для credentials

---

*Последнее обновление: 14 ноября 2025*

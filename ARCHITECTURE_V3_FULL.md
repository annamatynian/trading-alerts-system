# 🏗️ Архитектура Trading Alert System - Вариант 3

## Максимальная гибкость: Всё вместе

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRADING ALERT SYSTEM V3                         │
│                    (Максимальная гибкость - Всё вместе)                 │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────────┐
                              │   Google Sheets      │
                              │   (для админов)      │
                              │                      │
                              │ ┌──────────────────┐ │
                              │ │ symbol           │ │
                              │ │ condition        │ │
                              │ │ target_price     │ │
                              │ │ exchange         │ │
                              │ │ active           │ │
                              │ │ pushover_user_key│ │
                              │ │ notes            │ │
                              │ └──────────────────┘ │
                              └──────────┬───────────┘
                                        │
                                        │ Sync
                                        ▼
                              ┌──────────────────────┐
                              │     DynamoDB         │
                              │  (единый источник)   │
                              │                      │
                              │  Table: trading-     │
                              │         alerts       │
                              │                      │
                              │  PK: id (hash)       │
                              │  Attributes:         │
                              │   - name             │
                              │   - exchange         │
                              │   - symbol           │
                              │   - condition        │
                              │   - target_price     │
                              │   - status           │
                              │   - created_at       │
                              │   - triggered_count  │
                              └──────────┬───────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
        ┌───────────────────┐ ┌──────────────────┐ ┌─────────────────┐
        │   Gradio Web UI   │ │   AWS Lambda     │ │ Google Sheets   │
        │  (пользователи)   │ │  (автоматизация) │ │    (админы)     │
        │                   │ │                  │ │                 │
        │ ┌───────────────┐ │ │ ┌──────────────┐ │ │ ┌─────────────┐ │
        │ │Create Signal  │ │ │ │CloudWatch    │ │ │ │Manual edit  │ │
        │ │View Signals   │ │ │ │Schedule:     │ │ │ │Copy/Paste   │ │
        │ │Delete Signal  │ │ │ │rate(5 min)   │ │ │ │Formulas     │ │
        │ │Check Price    │ │ │ └──────┬───────┘ │ │ └─────────────┘ │
        │ │Sync from      │ │ │        │         │ │                 │
        │ │  Sheets       │ │ │        ▼         │ │                 │
        │ └───────────────┘ │ │ lambda_function  │ │                 │
        │                   │ │      .py         │ │                 │
        │ localhost:7860    │ │                  │ │                 │
        └─────────┬─────────┘ └────────┬─────────┘ └─────────────────┘
                  │                    │
                  │                    │
                  └────────┬───────────┘
                           │
                           ▼
                ┌────────────────────────┐
                │   Exchange Layer       │
                │   (Price Checker)      │
                │                        │
                │  ┌──────────────────┐  │
                │  │ BinanceExchange  │  │
                │  │ BybitExchange    │  │
                │  │ CoinbaseExchange │  │
                │  └──────────────────┘  │
                │                        │
                │  Fallback logic:       │
                │  1. Try primary exch   │
                │  2. Try fallback exch  │
                │  3. Return best price  │
                └────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   Exchange APIs          │
              │                          │
              │  ┌────────────────────┐  │
              │  │ Binance REST API   │  │
              │  │ Bybit REST API     │  │
              │  │ Coinbase REST API  │  │
              │  └────────────────────┘  │
              │                          │
              │  ⚠️ Geographic blocks:   │
              │  US regions → BLOCKED   │
              │  EU/APAC → OK ✅        │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │  Notification Layer      │
              │                          │
              │  ┌────────────────────┐  │
              │  │ Pushover API       │  │
              │  │ (Mobile push)      │  │
              │  └────────────────────┘  │
              │                          │
              │  Sends:                  │
              │  - Signal name           │
              │  - Current price         │
              │  - Target price          │
              │  - Timestamp             │
              └──────────────────────────┘
```

---

## 📊 Поток данных

### 1️⃣ Создание сигналов

```
User Action:
┌─────────────┐
│ Gradio UI   │ → Signal created via form
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ SignalTarget model   │ → Validation (Pydantic)
│ - name               │
│ - exchange           │
│ - symbol             │
│ - condition          │
│ - target_price       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ DynamoDB Storage     │ → save_signal()
│ - Upsert logic       │
│ - Generate ID        │
└──────┬───────────────┘
       │
       ▼ (optional)
┌──────────────────────┐
│ Google Sheets        │ → append_row()
│ - For manual edit    │
└──────────────────────┘
```

### 2️⃣ Автоматическая проверка (Lambda)

```
CloudWatch Event (every 5 min)
       │
       ▼
┌──────────────────────┐
│ AWS Lambda           │
│ lambda_function.py   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ DynamoDB             │ → get_all_signals()
│ - Read all active    │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Price Checker        │
│ For each signal:     │
│ 1. Get current price │
│ 2. Check condition   │
│ 3. If triggered:     │
│    → Send Pushover   │
│    → Update DynamoDB │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Exchange APIs        │
│ - Binance            │
│ - Bybit              │
│ - Coinbase           │
│ (with fallback)      │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Pushover             │
│ - Send notification  │
│ - To user's device   │
└──────────────────────┘
```

### 3️⃣ Синхронизация из Sheets

```
User Action:
┌─────────────┐
│ Google      │ → Manual edits in spreadsheet
│ Sheets      │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ Gradio UI            │ → "Sync from Sheets" button
│ sync_from_sheets()   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ SheetsReader         │ → read_signals()
│ - Parse rows         │
│ - Validate data      │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ DynamoDB Storage     │ → save_signal() (upsert)
│ - For each row       │
└──────────────────────┘
```

---

## 🔧 Компоненты системы

### Backend Core

```
src/
├── models/
│   └── signal.py
│       ├── SignalTarget (Pydantic model)
│       ├── ExchangeType (Enum)
│       ├── SignalCondition (Enum)
│       └── SignalStatus (Enum)
│
├── exchanges/
│   ├── base.py          (AbstractExchange)
│   ├── binance.py       (BinanceExchange)
│   ├── bybit.py         (BybitExchange)
│   └── coinbase.py      (CoinbaseExchange)
│
├── services/
│   ├── price_checker.py (PriceChecker - orchestrates exchanges)
│   ├── alert_sender.py  (AlertSender - Pushover integration)
│   └── sheets_reader.py (SheetsReader - Google Sheets API)
│
├── storage/
│   ├── base.py          (AbstractStorage)
│   ├── dynamodb_storage.py (DynamoDBStorage)
│   └── json_storage.py  (JSONStorage - for local dev)
│
└── utils/
    ├── config.py        (Config management)
    └── logger.py        (Logging setup)
```

### Deployment Targets

```
Deployment options:
├── gradio_app.py        → Gradio Web UI (localhost:7860)
├── lambda_function.py   → AWS Lambda (monolithic)
├── lambda_reader.py     → Lambda Reader (Fan-Out pattern)
├── lambda_worker.py     → Lambda Worker (Fan-Out pattern)
└── simple_alert.py      → Local script (for testing)
```

---

## 🎯 Сценарии использования

### Use Case 1: Single User (You)
```
You → Gradio UI → DynamoDB ← Lambda (checks) → Pushover (to your phone)
```
**Best for:** Personal trading, 1-20 signals

### Use Case 2: Team of Traders
```
Team → Google Sheets → Sync → DynamoDB ← Lambda → Pushover (to team)
```
**Best for:** Shared signals, team collaboration, 20+ signals

### Use Case 3: Automated 24/7
```
CloudWatch → Lambda → DynamoDB → Exchange APIs → Pushover
```
**Best for:** Hands-off monitoring, production environment

### Use Case 4: Hybrid (Recommended)
```
                  ┌→ Gradio UI (for quick signals)
                  │
DynamoDB ← Lambda ← → Google Sheets (for bulk edits)
                  │
                  └→ Pushover notifications
```
**Best for:** Maximum flexibility, 1-1000+ signals

---

## 🔒 Security & IAM

### AWS Resources

```
IAM Role: lambda-dynamodb-role
├── Trusted entity: lambda.amazonaws.com
└── Policies:
    ├── DynamoDBAccess
    │   ├── dynamodb:GetItem
    │   ├── dynamodb:PutItem
    │   ├── dynamodb:Scan
    │   └── dynamodb:UpdateItem
    │
    ├── SecretsManagerAccess
    │   └── secretsmanager:GetSecretValue
    │
    └── CloudWatchLogsAccess
        ├── logs:CreateLogGroup
        ├── logs:CreateLogStream
        └── logs:PutLogEvents
```

### Environment Variables

```
Production (AWS Lambda):
├── Stored in: AWS Secrets Manager
└── Retrieved at runtime

Development (Local):
├── Stored in: .env file
└── Loaded via: python-dotenv
```

---

## 📈 Scalability Options

### Current (Monolithic)
```
Lambda function (single)
- Processes all signals sequentially
- Good for: <100 signals
- Limitation: 15 min timeout
```

### Future (Fan-Out)
```
Lambda Reader
       │
       ▼
SQS Queue
       │
       ├→ Lambda Worker 1
       ├→ Lambda Worker 2
       ├→ Lambda Worker 3
       └→ Lambda Worker N

- Processes signals in parallel
- Good for: 100-10,000+ signals
- No timeout limitation
```

See: [DEPLOY_FAN_OUT.md](./DEPLOY_FAN_OUT.md)

---

## 🌍 Geographic Considerations

### ⚠️ CRITICAL: AWS Region Selection

```
US Regions (🚫 BLOCKED by exchanges):
├── us-east-1 (Virginia)
├── us-east-2 (Ohio)
├── us-west-1 (California)
└── us-west-2 (Oregon)

✅ RECOMMENDED Regions:
├── eu-central-1 (Frankfurt)
├── eu-west-1 (Ireland)
├── ap-southeast-1 (Singapore)
└── ap-northeast-1 (Tokyo)
```

**Why?** Binance, Bybit, Coinbase block API requests from US IP addresses.

---

## 🛠️ Development Workflow

```
Local Development:
1. Edit code in src/
2. Test with: pytest tests/
3. Run Gradio: python gradio_app.py
4. Verify functionality locally

Production Deployment:
1. Update code
2. Build Lambda package: python build_lambda_package.py
3. Upload to S3: aws s3 cp lambda_deployment.zip s3://bucket/
4. Update Lambda: aws lambda update-function-code ...
5. Monitor CloudWatch logs
```

---

## 📊 Data Models

### SignalTarget (Pydantic)

```python
class SignalTarget:
    id: str                    # Unique identifier
    name: str                  # Human-readable name
    exchange: ExchangeType     # BINANCE | BYBIT | COINBASE
    symbol: str                # BTCUSDT, ETHUSDT, etc.
    condition: SignalCondition # ABOVE | BELOW
    target_price: Decimal      # Target price threshold
    status: SignalStatus       # PENDING | TRIGGERED | EXPIRED
    active: bool               # Is signal active?
    created_at: datetime       # Creation timestamp
    triggered_at: datetime?    # Last trigger timestamp
    triggered_count: int       # Number of times triggered
    user_id: str?              # Pushover user key
    notes: str?                # Optional notes
```

### DynamoDB Schema

```
Table: trading-alerts
├── Primary Key: id (String, Hash)
├── Attributes:
│   ├── name (String)
│   ├── exchange (String)
│   ├── symbol (String)
│   ├── condition (String)
│   ├── target_price (Number)
│   ├── status (String)
│   ├── active (Boolean)
│   ├── created_at (String)
│   ├── triggered_at (String)
│   ├── triggered_count (Number)
│   ├── user_id (String)
│   └── notes (String)
└── Global Secondary Indexes: (optional for future)
    └── symbol-index (for querying by symbol)
```

---

## 🎯 Best Practices

### ✅ DO:
- Use DynamoDB as single source of truth
- Sync Google Sheets → DynamoDB regularly
- Deploy Lambda in non-US regions
- Use AWS Secrets Manager for production
- Monitor CloudWatch logs
- Test locally before deploying

### ❌ DON'T:
- Don't edit Sheets without syncing to DynamoDB
- Don't deploy Lambda in US regions
- Don't commit `.env` to Git
- Don't store secrets in code
- Don't skip testing

---

## 🔄 Future Enhancements

### Planned Features:
- [ ] Fan-Out architecture for massive scalability
- [ ] Telegram Bot integration
- [ ] Discord notifications
- [ ] Advanced analytics dashboard
- [ ] Multi-user support with authentication
- [ ] Historical price tracking
- [ ] Backtesting capabilities

---

**Happy Trading! 🚀📈**

# Trading Alerts System - Hugging Face Spaces Deployment

Автоматическая система мониторинга цен криптовалют с уведомлениями через Pushover.

## 🚀 Features

- ✅ **Мониторинг цен** - Проверка цен на Binance, Coinbase, Bybit каждый час
- ✅ **Pushover уведомления** - Emergency push-уведомления на телефон
- ✅ **JWT Authentication** - Безопасная аутентификация пользователей
- ✅ **DynamoDB** - Хранение сигналов и пользователей в AWS
- ✅ **Google Sheets** - Опциональная интеграция с таблицами
- ✅ **Gradio UI** - Простой веб-интерфейс для управления

## 📋 Что нужно перед деплоем

### 1. AWS DynamoDB Table

Создайте таблицу в AWS DynamoDB:

- **Table Name**: `trading-alerts`
- **Partition Key**: `PK` (String)
- **Sort Key**: `SK` (String)
- **Region**: `eu-west-1` (или любой другой)

### 2. Pushover Account

1. Создайте аккаунт на [pushover.net](https://pushover.net)
2. Создайте приложение (получите **App Token**)
3. Получите ваш **User Key** из дашборда

### 3. AWS IAM Credentials

Создайте IAM пользователя с правами:

- `dynamodb:PutItem`
- `dynamodb:GetItem`
- `dynamodb:Query`
- `dynamodb:DeleteItem`
- `dynamodb:UpdateItem`

### 4. Google Service Account (опционально)

Если используете Google Sheets:

1. Создайте Service Account в Google Cloud Console
2. Скачайте JSON ключ
3. Дайте доступ к таблице для email из Service Account

## 🔐 Configuration Secrets

После создания Space, добавьте следующие Secrets:

**Settings → Repository Secrets**

### Required Secrets:

```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=eu-west-1
DYNAMODB_TABLE_NAME=trading-alerts

PUSHOVER_APP_TOKEN=your_app_token_here

JWT_SECRET_KEY=your-super-secret-key-change-me

GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

### Optional Secrets (API keys для бирж):

```bash
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret

COINBASE_API_KEY=your_coinbase_key
COINBASE_API_SECRET=your_coinbase_secret
```

> ⚠️ **Важно**: Если не указать API ключи бирж, система всё равно будет работать в режиме публичного API (без приватных операций)

## 📦 Deployment Steps

### 1. Create New Space

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Choose:
   - **SDK**: Gradio
   - **Hardware**: CPU Basic (FREE) или CPU Upgrade ($5/month)

### 2. Upload Files

Upload these files to your Space:

```
app_hf.py              # Main entry point
requirements_hf.txt    # Dependencies
app_with_auth.py       # Gradio interface
src/                   # Source code directory
  ├── models/
  ├── services/
  ├── storage/
  ├── exchanges/
  └── utils/
```

### 3. Configure Secrets

Go to **Settings → Repository Secrets** and add all required secrets (see above)

### 4. Start Space

Space will automatically build and deploy. Check logs for any errors.

## 🧪 Testing After Deployment

### Test 1: UI Access

1. Open your Space URL
2. You should see Login/Register page
3. Register a new account

### Test 2: Add Pushover Key

1. Login to UI
2. Go to **Settings** tab
3. Add your Pushover User Key
4. Click "Save Settings"

### Test 3: Create Signal

1. Go to **Add Signal** tab
2. Fill in:
   - Name: `Test BTC Alert`
   - Exchange: `binance`
   - Symbol: `BTC/USDT`
   - Condition: `above` or `below`
   - Target Price: (slightly above/below current price)
3. Click "Add Signal"
4. Wait for price to trigger (check every hour)

## 📱 Pushover Setup

1. Install Pushover app on your phone ([iOS](https://apps.apple.com/app/pushover-notifications/id506088175) / [Android](https://play.google.com/store/apps/details?id=net.superblock.pushover))
2. Login with your Pushover account
3. You'll receive notifications when price alerts trigger

## 🔧 Monitoring

### Check Logs

Go to **Settings → Logs** to see:

- Price checker status
- DynamoDB connections
- Notification delivery
- Any errors

### Background Process

The price checker runs every **1 hour** in background thread. Check logs for:

```
🔍 Starting background signal check
📊 Read X trading signals from Google Sheets
✅ Signal check completed. Next check in 60 minutes
```

## 🐛 Troubleshooting

### "Missing required secrets"

- Check that all secrets are added in Settings → Repository Secrets
- Restart the Space after adding secrets

### "Failed to connect to DynamoDB"

- Verify AWS credentials are correct
- Check IAM user has DynamoDB permissions
- Verify table name and region match

### "No Pushover notifications"

- Check PUSHOVER_APP_TOKEN is correct
- Verify user added their Pushover User Key in Settings tab
- Check signal is `active=True`

### "Price checker not running"

- Check logs for background thread startup
- Verify at least one exchange is configured (Binance works without API keys)

## 💰 Costs

### Free Tier:

- **HF Spaces**: FREE (CPU Basic)
- **DynamoDB**: FREE tier includes 25GB storage + 25 WCU/RCU
- **Pushover**: $5 one-time (iOS) or $5 one-time (Android)

### Paid Options:

- **HF Spaces CPU Upgrade**: $5/month (faster performance)
- **HF Spaces Persistent Storage**: $5/month (keeps data between restarts)

## 📚 Architecture

```
┌─────────────────────┐
│  Hugging Face Space │
│                     │
│  ┌───────────────┐  │
│  │  Gradio UI    │  │  ← User manages signals
│  └───────────────┘  │
│                     │
│  ┌───────────────┐  │
│  │ Price Checker │  │  ← Runs every hour
│  │ (Background)  │  │
│  └───────────────┘  │
└─────────────────────┘
         ↓ ↓ ↓
    ┌────────┬────────┬──────────┐
    ↓        ↓        ↓          ↓
┌────────┐ ┌──────┐ ┌────────┐ ┌──────┐
│ Dynamo │ │Sheets│ │Binance │ │Pushov│
│   DB   │ │      │ │        │ │  er  │
└────────┘ └──────┘ └────────┘ └──────┘
```

## 🔗 Links

- [Pushover](https://pushover.net)
- [AWS DynamoDB](https://aws.amazon.com/dynamodb/)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [CCXT Library](https://github.com/ccxt/ccxt)

## 📄 License

MIT License

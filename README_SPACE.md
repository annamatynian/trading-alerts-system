```markdown
---
title: Trading Signal System
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
---

# Trading Signal System

Автоматическая система мониторинга криптовалютных цен.

## Features

- Create trading signals with target prices
- Monitor multiple exchanges (Binance, Bybit, Coinbase)
- Real-time price checking
- DynamoDB integration
- Google Sheets sync (optional)

## Usage

1. Go to "Create Signal" tab
2. Fill in the form
3. Click "Create Signal"
4. Your signal is saved to DynamoDB
5. AWS Lambda checks hourly and sends Pushover notifications

Enjoy! 🎉
```
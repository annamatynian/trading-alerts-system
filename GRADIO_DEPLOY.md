# 🌐 Деплой Gradio на облачных платформах

## Варианты деплоя Gradio интерфейса

### Вариант 1: Hugging Face Spaces (Рекомендуется) ⭐

**Преимущества:**
- ✅ Бесплатный хостинг
- ✅ Автоматический деплой из Git
- ✅ Gradio поддерживается нативно
- ✅ Публичный URL
- ✅ Простая настройка

**Шаги:**

1. **Создайте Space на Hugging Face:**
   ```
   https://huggingface.co/spaces
   → New Space
   → SDK: Gradio
   → Name: trading-signal-system
   ```

2. **Подготовьте файлы:**
   ```
   trading_alert_system/
   ├── app.py                  ← переименуйте gradio_app.py
   ├── requirements.txt
   ├── .env.example
   └── src/                    ← вся структура проекта
   ```

3. **Создайте файл для Hugging Face:**
   
   `app.py` (упрощенная версия):
   ```python
   import gradio as gr
   import os
   
   # Ваш код gradio_app.py
   # ...
   
   if __name__ == "__main__":
       app = create_interface()
       app.launch()  # Hugging Face сам настроит порт
   ```

4. **Настройте Secrets в HF Spaces:**
   ```
   Settings → Repository secrets:
   - DYNAMODB_TABLE_NAME
   - DYNAMODB_REGION
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - BINANCE_API_KEY
   - BINANCE_API_SECRET
   - ...
   ```

5. **Push в Git:**
   ```bash
   git remote add hf https://huggingface.co/spaces/USERNAME/trading-signal-system
   git push hf main
   ```

**Результат:**
```
https://huggingface.co/spaces/USERNAME/trading-signal-system
```

---

### Вариант 2: Render.com

**Преимущества:**
- ✅ Бесплатный tier
- ✅ Автодеплой из GitHub
- ✅ Поддержка Docker
- ✅ Простая настройка environment variables

**Шаги:**

1. **Создайте файл `Dockerfile`:**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   CMD ["python", "gradio_app.py"]
   ```

2. **Создайте Web Service на Render:**
   ```
   https://render.com
   → New Web Service
   → Connect GitHub repo
   → Environment: Docker
   → Port: 7860
   ```

3. **Настройте Environment Variables:**
   ```
   DYNAMODB_TABLE_NAME = trading-alerts
   AWS_ACCESS_KEY_ID = your_key
   AWS_SECRET_ACCESS_KEY = your_secret
   ...
   ```

4. **Deploy автоматически запустится**

**Результат:**
```
https://trading-signal-system.onrender.com
```

---

### Вариант 3: AWS EC2 (Полный контроль)

**Преимущества:**
- ✅ Полный контроль
- ✅ Та же инфраструктура что Lambda
- ✅ Можно интегрировать с VPC
- ❌ Платный (t2.micro бесплатный tier)

**Шаги:**

1. **Создайте EC2 инстанс:**
   ```
   AWS Console → EC2 → Launch Instance
   - AMI: Ubuntu 22.04
   - Type: t2.micro (free tier)
   - Security Group: Allow 7860 (HTTP)
   ```

2. **Подключитесь по SSH:**
   ```bash
   ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute-1.amazonaws.com
   ```

3. **Установите зависимости:**
   ```bash
   sudo apt update
   sudo apt install python3-pip git -y
   
   # Clone repo
   git clone https://github.com/YOUR_USERNAME/trading_alert_system.git
   cd trading_alert_system
   
   # Install dependencies
   pip3 install -r requirements.txt
   ```

4. **Настройте .env файл:**
   ```bash
   nano .env
   # Вставьте все переменные окружения
   ```

5. **Запустите с systemd (автозапуск):**
   
   Создайте `/etc/systemd/system/gradio.service`:
   ```ini
   [Unit]
   Description=Gradio Trading Signal System
   After=network.target
   
   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/trading_alert_system
   ExecStart=/usr/bin/python3 gradio_app.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Активируйте:
   ```bash
   sudo systemctl enable gradio
   sudo systemctl start gradio
   ```

6. **Настройте nginx (опционально):**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:7860;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

**Результат:**
```
http://ec2-xx-xx-xx-xx.compute-1.amazonaws.com:7860
```

---

### Вариант 4: Fly.io

**Преимущества:**
- ✅ Бесплатный tier (3 маленьких VM)
- ✅ Глобальный edge network
- ✅ Простой деплой

**Шаги:**

1. **Установите Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Создайте `fly.toml`:**
   ```toml
   app = "trading-signal-system"
   
   [build]
     dockerfile = "Dockerfile"
   
   [[services]]
     internal_port = 7860
     protocol = "tcp"
   
     [[services.ports]]
       port = 80
       handlers = ["http"]
   
     [[services.ports]]
       port = 443
       handlers = ["tls", "http"]
   ```

3. **Deploy:**
   ```bash
   fly deploy
   fly secrets set DYNAMODB_TABLE_NAME=trading-alerts
   fly secrets set AWS_ACCESS_KEY_ID=your_key
   # ... остальные secrets
   ```

**Результат:**
```
https://trading-signal-system.fly.dev
```

---

## 🔒 Безопасность для Production

### 1. Добавьте аутентификацию

```python
# В gradio_app.py
app.launch(
    auth=("admin", os.getenv("GRADIO_PASSWORD")),
    auth_message="Enter credentials to access Trading Signal System"
)
```

### 2. Используйте HTTPS

- Hugging Face: автоматически ✅
- Render: автоматически ✅
- EC2: настройте Let's Encrypt
- Fly.io: автоматически ✅

### 3. Rate Limiting

```python
import time
from functools import wraps

def rate_limit(max_calls=10, period=60):
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [c for c in calls if c > now - period]
            if len(calls) >= max_calls:
                return "⚠️ Rate limit exceeded. Try again later."
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=5, period=60)
def create_signal(*args, **kwargs):
    # ...
```

### 4. Environment Variables

**НИКОГДА** не коммитьте:
- `.env`
- Credential files
- API keys

Используйте:
- Hugging Face Spaces → Repository Secrets
- Render → Environment Variables
- EC2 → AWS Secrets Manager
- Fly.io → `fly secrets`

---

## 📊 Мониторинг и логи

### Hugging Face Spaces
```
Settings → Logs (real-time)
```

### Render
```
Logs tab → Real-time logs
```

### EC2
```bash
# Systemd logs
sudo journalctl -u gradio -f

# Application logs
tail -f /home/ubuntu/trading_alert_system/logs/app.log
```

### Fly.io
```bash
fly logs
```

---

## 💰 Стоимость

| Платформа | Free Tier | Платный План |
|-----------|-----------|--------------|
| **Hugging Face Spaces** | ✅ CPU (постоянно) | $9/мес (GPU) |
| **Render** | ✅ 750h/мес | $7/мес (постоянный) |
| **AWS EC2** | ✅ t2.micro (12 мес) | $10-20/мес |
| **Fly.io** | ✅ 3 VM shared CPU | $5-10/мес |

---

## 🎯 Рекомендация

Для **Trading Alert System** рекомендую:

1. **Hugging Face Spaces** - для быстрого старта и бесплатного хостинга
2. **AWS EC2** - если уже используете AWS для Lambda и хотите единую инфраструктуру
3. **Render** - золотая середина между простотой и функциональностью

---

## 🚀 Быстрый старт для HF Spaces

```bash
# 1. Переименуйте файл
mv gradio_app.py app.py

# 2. Создайте репозиторий на HF
# https://huggingface.co/spaces

# 3. Push код
git remote add hf https://huggingface.co/spaces/USERNAME/trading-signal-system
git add .
git commit -m "Deploy Gradio to HF Spaces"
git push hf main

# 4. Настройте secrets в HF UI
# Settings → Repository secrets

# 5. Готово! 🎉
# Ваш URL: https://huggingface.co/spaces/USERNAME/trading-signal-system
```

---

## 📚 Полезные ссылки

- [Hugging Face Spaces Docs](https://huggingface.co/docs/hub/spaces)
- [Render Deployment Guide](https://render.com/docs)
- [Fly.io Gradio Guide](https://fly.io/docs/app-guides/gradio/)
- [Gradio Sharing Options](https://gradio.app/sharing-your-app/)

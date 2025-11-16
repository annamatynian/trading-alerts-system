# 🎯 НАЧНИ ОТСЮДА - Trading Alert System

## 👋 Добро пожаловать!

У вас есть полноценная система мониторинга криптовалютных торговых сигналов с тремя интерфейсами управления:

1. **Gradio Web UI** - красивый веб-интерфейс
2. **Google Sheets** - табличное редактирование
3. **AWS Lambda** - автоматизация 24/7

---

## ⚡ БЫСТРЫЙ СТАРТ (3 минуты)

### Шаг 1: Запустите Gradio UI

**Windows (проще всего):**
```
Двойной клик на файл: run_gradio.bat
```

**Вручную:**
```bash
# Активируйте виртуальное окружение
venv\Scripts\activate

# Запустите Gradio
python gradio_app.py
```

### Шаг 2: Откройте браузер
```
http://localhost:7860
```

### Шаг 3: Создайте первый сигнал

1. Перейдите на вкладку **"Create Signal"**
2. Заполните форму:
   - **Signal Name:** `My BTC Alert`
   - **Exchange:** `bybit`
   - **Symbol:** `BTCUSDT`
   - **Condition:** `above`
   - **Target Price:** `50000`
   - **User ID:** (ваш Pushover user key)
3. Нажмите **"Create Signal"**

### Шаг 4: Готово! 🎉
Ваш первый сигнал создан и сохранен в DynamoDB!

---

## 📁 Структура проекта - Что где находится?

```
trading_alert_system/
│
├── 📘 README.md                  ← Главная документация
├── 📘 STATUS.md                  ← Статус проекта (ВСЁ ГОТОВО!)
├── 📘 QUICKSTART.md              ← Быстрая справка
├── 📘 START_HERE.md              ← ВЫ ЗДЕСЬ
│
├── 🎨 ИНТЕРФЕЙСЫ:
│   ├── gradio_app.py             ← Gradio Web UI
│   ├── run_gradio.bat            ← Запуск Gradio (Windows)
│   └── simple_alert.py           ← Простая локальная проверка
│
├── ☁️ AWS LAMBDA:
│   ├── lambda_function.py        ← Lambda handler (монолитный)
│   ├── lambda_reader.py          ← Lambda Reader (Fan-Out)
│   ├── lambda_worker.py          ← Lambda Worker (Fan-Out)
│   └── build_lambda_package.py   ← Скрипт сборки пакета
│
├── 📚 ДОКУМЕНТАЦИЯ:
│   ├── GRADIO_GUIDE.md           ← Полный гайд по Gradio
│   ├── DEPLOY_AWS_LAMBDA.md      ← Деплоймент на AWS
│   ├── DEPLOY_FAN_OUT.md         ← Fan-Out архитектура
│   ├── ARCHITECTURE_V3_FULL.md   ← Архитектура системы
│   └── PROXY_SETUP.md            ← Настройка прокси
│
├── 🔧 ИСХОДНЫЙ КОД:
│   └── src/
│       ├── models/               ← Pydantic модели
│       ├── exchanges/            ← Адаптеры бирж
│       ├── services/             ← Бизнес-логика
│       ├── storage/              ← Слой хранения
│       └── utils/                ← Утилиты
│
├── 🧪 ТЕСТЫ:
│   └── tests/                    ← Юнит-тесты
│
└── ⚙️ КОНФИГУРАЦИЯ:
    ├── .env                      ← Переменные окружения
    ├── .env.example              ← Пример .env
    ├── requirements.txt          ← Зависимости (локально)
    └── requirements_lambda.txt   ← Зависимости (Lambda)
```

---

## 🎯 Что читать дальше?

### Если вы новичок:
1. **START_HERE.md** ← Вы здесь
2. **QUICKSTART.md** - Быстрая справка по использованию
3. **GRADIO_GUIDE.md** - Полный гайд по Gradio интерфейсу

### Если хотите понять архитектуру:
1. **README.md** - Главная документация
2. **ARCHITECTURE_V3_FULL.md** - Полная архитектура системы
3. **STATUS.md** - Что уже готово

### Если хотите задеплоить на AWS:
1. **DEPLOY_AWS_LAMBDA.md** - Пошаговая инструкция деплоя
2. **DEPLOY_FAN_OUT.md** - Fan-Out архитектура (для масштабирования)

### Если возникли проблемы:
1. **QUICKSTART.md** раздел "Troubleshooting"
2. **GRADIO_GUIDE.md** раздел "Troubleshooting"
3. **DEPLOY_AWS_LAMBDA.md** раздел "Troubleshooting"

---

## 📊 Три способа управления сигналами

### 1️⃣ Gradio Web UI (Рекомендуется)

**Запуск:**
```bash
python gradio_app.py
# или
run_gradio.bat
```

**Возможности:**
- ✅ Создание сигналов через форму
- ✅ Просмотр всех сигналов
- ✅ Удаление сигналов
- ✅ Проверка цен на бирже
- ✅ Синхронизация из Google Sheets

**Когда использовать:** Для создания 1-10 сигналов, просмотра, управления

---

### 2️⃣ Google Sheets

**Формат таблицы:**

| symbol   | condition | target_price | exchange | active | pushover_user_key | notes |
|----------|-----------|--------------|----------|--------|-------------------|-------|
| BTCUSDT  | above     | 50000        | bybit    | TRUE   | user_xyz123       | BTC   |
| ETHUSDT  | below     | 3000         | binance  | TRUE   | user_xyz123       | ETH   |

**Синхронизация:**
1. Редактируйте таблицу
2. Откройте Gradio → вкладка "Sync from Sheets"
3. Нажмите "Sync from Google Sheets"

**Когда использовать:** Для массовых правок (10+ сигналов)

---

### 3️⃣ AWS Lambda

**Что делает:**
- Автоматически проверяет сигналы каждые 5 минут
- Читает из DynamoDB
- Проверяет цены на биржах
- Отправляет Pushover уведомления

**Деплоймент:**
См. [DEPLOY_AWS_LAMBDA.md](./DEPLOY_AWS_LAMBDA.md)

**Когда использовать:** Для автоматизации 24/7

---

## 🏗️ Архитектура системы (Вариант 3)

```
                  ┌──────────────────┐
                  │  Google Sheets   │
                  │  (для админов)   │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │    DynamoDB      │
                  │ (единый источник)│
                  └────────┬─────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌────────────────┐ ┌──────────────┐ ┌────────────────┐
│  Gradio UI     │ │ AWS Lambda   │ │ Google Sheets  │
│ (пользователи) │ │ (автомат.)   │ │    (админы)    │
└────────┬───────┘ └──────┬───────┘ └────────────────┘
         │                │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │ Exchange APIs  │
         │ + Pushover     │
         └────────────────┘
```

**Преимущества:**
- ✅ Максимальная гибкость
- ✅ Выбор интерфейса по ситуации
- ✅ DynamoDB как единый источник данных

---

## ✅ Чек-лист: Что уже готово

### Локально:
- [x] Gradio UI работает
- [x] DynamoDB подключен
- [x] Google Sheets синхронизируется
- [x] Exchanges доступны (Binance, Bybit, Coinbase)
- [x] Pushover уведомления настроены

### AWS Lambda:
- [x] Lambda пакет собран
- [x] IAM роль с правами на DynamoDB
- [x] Lambda функция готова к деплою
- [x] CloudWatch расписание (каждые 5 минут)

### Документация:
- [x] README.md - главная документация
- [x] STATUS.md - статус проекта
- [x] QUICKSTART.md - быстрая справка
- [x] GRADIO_GUIDE.md - гайд по Gradio
- [x] DEPLOY_AWS_LAMBDA.md - деплоймент
- [x] ARCHITECTURE_V3_FULL.md - архитектура

---

## 🚀 Рекомендуемый путь

### День 1: Локальное тестирование
1. Запустите Gradio: `python gradio_app.py`
2. Создайте 2-3 тестовых сигнала
3. Проверьте что уведомления приходят через Pushover
4. Протестируйте синхронизацию с Google Sheets

### День 2: AWS Lambda деплоймент
1. Создайте DynamoDB таблицу в AWS
2. Настройте IAM роль
3. Соберите Lambda пакет: `python build_lambda_package.py`
4. Задеплойте Lambda функцию
5. Настройте CloudWatch расписание

### День 3+: Production использование
1. Добавьте реальные сигналы через Gradio или Sheets
2. Мониторьте CloudWatch логи
3. Получайте уведомления на телефон
4. Наслаждайтесь автоматизацией! 🎉

---

## 🛠️ Быстрые команды

```bash
# Запустить Gradio UI
python gradio_app.py

# Собрать Lambda пакет
python build_lambda_package.py

# Запустить тесты
pytest tests/

# Простая локальная проверка
python simple_alert.py
```

---

## 💡 Полезные советы

### Для начинающих:
1. Начните с Gradio UI - он самый простой
2. Создайте 1-2 тестовых сигнала
3. Убедитесь что уведомления приходят
4. Только потом переходите к Lambda

### Для опытных:
1. Используйте Google Sheets для массовых операций
2. Автоматизируйте через Lambda
3. Мониторьте CloudWatch логи
4. Рассмотрите Fan-Out архитектуру для масштабирования

### Для всех:
1. ⚠️ **НЕ используйте US регионы AWS** (биржи блокируют!)
2. Используйте `eu-central-1` или `ap-southeast-1`
3. Храните API ключи в AWS Secrets Manager
4. Регулярно проверяйте CloudWatch логи

---

## 🐛 Частые проблемы и решения

### Gradio не запускается
```bash
pip install --upgrade gradio
```

### Lambda не работает
- Проверьте регион (НЕ US!)
- Проверьте IAM права
- Проверьте CloudWatch логи

### Sheets не синхронизируется
- Проверьте доступ Service Account
- Проверьте формат таблицы

### Биржи недоступны
- Проверьте API ключи в `.env`
- Проверьте AWS регион

---

## 📞 Поддержка

**Если возникли проблемы:**
1. Проверьте раздел "Troubleshooting" в соответствующей документации
2. Посмотрите CloudWatch логи (для Lambda)
3. Проверьте `.env` переменные окружения

---

## 🎉 Готово! Что дальше?

### Выберите ваш путь:

#### 🎨 Хочу красивый UI
```bash
python gradio_app.py
```
→ http://localhost:7860

#### 📊 Хочу табличное редактирование
→ Откройте Google Sheets
→ Редактируйте таблицу
→ Синхронизируйте через Gradio

#### ☁️ Хочу автоматизацию 24/7
→ См. [DEPLOY_AWS_LAMBDA.md](./DEPLOY_AWS_LAMBDA.md)

---

## 📚 Карта документации

```
START_HERE.md (ВЫ ЗДЕСЬ)
    │
    ├─→ QUICKSTART.md (быстрая справка)
    │
    ├─→ GRADIO_GUIDE.md (гайд по Gradio)
    │
    ├─→ DEPLOY_AWS_LAMBDA.md (деплоймент)
    │
    ├─→ ARCHITECTURE_V3_FULL.md (архитектура)
    │
    └─→ README.md (главная документация)
```

---

**Happy Trading! 🚀📈**

---

**Version:** 3.0.0
**Date:** 2025-11-14
**Status:** ✅ Production Ready

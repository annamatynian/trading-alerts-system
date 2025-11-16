# Это файл src/handlers/commands.py

from aiogram import types, Router
from aiogram.filters import CommandStart, Command
from models.alert import ExchangeType, AlertCondition, AlertTarget

# "Router" — это как мини-мозг для набора команд.
router = Router()

@router.message(CommandStart())
async def handle_start(message: types.Message):
    """
    Этот код выполняется, когда пользователь пишет /start
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or "незнакомец"

    # TODO: Здесь будет ваш код для сохранения chat_id и user_id в базу данных.
    # Прямо сейчас мы просто выводим их для проверки.
    print(f"Новый пользователь: {username}, ID: {user_id}, Chat ID: {chat_id}")

    await message.answer(
        f"Привет, {username}!\n"
        f"Я бот для отслеживания цен. Я сохранил твой Chat ID: `{chat_id}`.\n\n"
        f"Чтобы получать громкие алерты, настрой Pushover командой /pushover"
    )

@router.message(Command("pushover"))
async def handle_pushover_info(message: types.Message):
    """
    Этот код отправляет инструкцию по настройке Pushover
    """
    await message.answer(
        "Инструкция по настройке громких алертов:\n"
        "1. Зайди на сайт pushover.net и скопируй свой 'User Key'.\n"
        "2. Пришли его мне командой:\n"
        "/set_key твой_ключ_из_pushover"
    )

@router.message(Command("set_key"))
async def handle_set_key(message: types.Message):
    """
    Этот код сохраняет Pushover User Key
    """
    user_key = message.text.replace("/set_key", "").strip()

    if len(user_key) == 30:
        # TODO: Здесь будет ваш код для сохранения user_key в базу данных.
        print(f"Пользователь {message.from_user.id} установил Pushover Key: {user_key}")
        await message.answer("✅ Отлично! Твой Pushover ключ сохранен.")
    else:
        await message.answer("❌ Ключ выглядит неверно. Проверь его и попробуй снова.")

@router.message(Command("add_alert"))
async def handle_add_alert(message: types.Message):
    """
    Обрабатывает команду для создания нового алерта.
    Формат: /add_alert <биржа> <пара> <условие> <цена>
    Пример: /add_alert bybit BTCUSDT above 80000
    """
    parts = message.text.split()
    
    # Проверяем, что команда введена в правильном формате
    if len(parts) != 5:
        await message.answer(
            "❌ Неправильный формат. Используйте:\n"
            "`/add_alert <биржа> <пара> <условие> <цена>`\n\n"
            "**Пример:**\n"
            "`/add_alert bybit BTCUSDT above 80000`",
            parse_mode="Markdown"
        )
        return

    _, exchange_str, symbol, condition_str, price_str = parts

    # --- Преобразуем текст в наши модели данных ---
    try:
        exchange = ExchangeType(exchange_str.lower())
        condition = AlertCondition(condition_str.lower())
        target_price = float(price_str)
        user_id = str(message.from_user.id) # user_id должен быть строкой для совместимости
    except (ValueError, KeyError):
        await message.answer("❌ Ошибка в данных. Проверьте название биржи, условие или цену.")
        return

    # --- Создаем объект алерта ---
    new_alert = AlertTarget(
        name=f"Alert for {symbol} {condition.value} ${target_price}",
        exchange=exchange,
        symbol=symbol.upper(),
        condition=condition,
        target_price=target_price,
        user_id=user_id,
        active=True
    )

    # --- TODO: Сохраняем алерт в базу данных ---
    # Этот код пока условный. Вам нужно будет реализовать логику сохранения.
    # success = await storage.save_alert(new_alert)
    success = True # Временно ставим заглушку
    # ------------------------------------------

    if success:
        await message.answer(f"✅ Алерт создан: {new_alert.name}")
        print(f"Новый алерт сохранен: {new_alert.dict()}")
    else:
        await message.answer("❌ Не удалось сохранить алерт. Попробуйте позже.")

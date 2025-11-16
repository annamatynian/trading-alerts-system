@echo off
echo ================================
echo Коммитим изменения - убран Telegram бот полностью
echo ================================
echo.

git add src/main.py
git add src/utils/config.py

echo.
echo Файлы добавлены! Создаём коммит...
echo.

git commit -m "refactor: полностью убран Telegram бот - Система работает только с Google Sheets + Pushover - Простой HTTP сервер для health checks Leapcell - Фоновая проверка алертов каждый час - Не требует TELEGRAM_BOT_TOKEN и PUBLIC_URL - API ключи бирж опциональны (используются публичные endpoints)"

echo.
echo Коммит создан! Пушим на сервер...
echo.

git push

echo.
echo ================================
echo Готово! Изменения отправлены!
echo ================================
pause

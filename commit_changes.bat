@echo off
echo ================================
echo Коммитим изменения в систему...
echo ================================
echo.

git add src/services/alert_manager.py
git add src/models/alert.py
git add src/services/notification.py
git add src/services/price_checker.py
git add src/exchanges/binance.py
git add src/exchanges/bybit.py
git add src/utils/config.py
git add .env.example
git add DEPLOY_LEAPCELL.md
git add src/check_alerts_cron.py

echo.
echo Файлы добавлены! Создаём коммит...
echo.

git commit -m "feat: изменена логика алертов + улучшения системы - ГЛАВНОЕ: Алерт срабатывает только один раз НАВСЕГДА (Вариант 1) - После срабатывания алерт деактивируется (active = False) - Обновлены модели, сервисы и конфигурация - Добавлен cron скрипт для проверки алертов"

echo.
echo Коммит создан! Пушим на сервер...
echo.

git push

echo.
echo ================================
echo Готово! Изменения отправлены!
echo ================================
pause

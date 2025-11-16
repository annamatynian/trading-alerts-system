@echo off
echo ================================
echo Коммитим изменения - ускорение Binance
echo ================================
echo.

git add src/exchanges/binance.py

echo.
echo Файлы добавлены! Создаём коммит...
echo.

git commit -m "perf: убран медленный load_markets() из Binance - Инициализация теперь занимает секунды вместо 5+ минут - load_markets() не нужен для fetch_ticker() - Binance fast mode enabled"

echo.
echo Коммит создан! Пушим на сервер...
echo.

git push

echo.
echo ================================
echo Готово! Изменения отправлены!
echo ================================
pause

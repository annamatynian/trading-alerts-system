@echo off
echo ================================
echo Коммитим изменения - добавлена Coinbase и fallback механизм
echo ================================
echo.

git add src/exchanges/coinbase.py
git add src/exchanges/binance.py
git add src/main.py
git add src/utils/config.py
git add src/services/price_checker.py

echo.
echo Файлы добавлены! Создаём коммит...
echo.

git commit -m "feat: добавлена Coinbase и автоматический fallback между биржами - Добавлена Coinbase (американская биржа, работает из США) - Реализован автоматический fallback: если одна биржа не работает -> пробует другую - Binance fast mode (убран медленный load_markets) - Теперь 3 биржи: Binance (основная), Coinbase (fallback), Bybit (fallback) - Умная защита от сбоев любой биржи"

echo.
echo Коммит создан! Пушим на сервер...
echo.

git push

echo.
echo ================================
echo Готово! Изменения отправлены!
echo ================================
pause

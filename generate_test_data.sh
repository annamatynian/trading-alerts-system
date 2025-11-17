#!/bin/bash
# ========================================
# ЁЯЪА Generate Test Signals for Anna & Tomas
# ========================================

echo ""
echo "========================================"
echo "ЁЯЪА ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ"
echo "========================================"
echo ""
echo "Этот скрипт создаст тестовые сигналы для:"
echo "  - anna (4 сигнала)"
echo "  - tomas (5 сигналов)"
echo ""
echo "========================================"
echo ""

# Активируем виртуальное окружение если есть
if [ -d "venv" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Проверяем .env
if [ ! -f ".env" ]; then
    echo ""
    echo "❌ ERROR: .env file not found!"
    echo "   Please copy .env.example to .env and configure it"
    echo ""
    exit 1
fi

echo ""
echo "ЁЯЪл Generating test signals..."
echo ""

# Запускаем скрипт генерации
python3 generate_test_signals.py

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✅ SUCCESS!"
    echo "========================================"
    echo ""
    echo "Тестовые данные созданы!"
    echo "Теперь можете тестировать фильтр по User ID"
    echo ""
else
    echo ""
    echo "========================================"
    echo "❌ FAILED"
    echo "========================================"
    echo ""
    echo "Проверьте логи выше для деталей"
    echo ""
fi

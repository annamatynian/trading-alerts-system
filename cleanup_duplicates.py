"""
Скрипт для удаления дубликатов из DynamoDB
Оставляет только самые новые версии сигналов
"""
import os
import asyncio
from datetime import datetime
from collections import defaultdict

# Добавляем src в path
import sys
sys.path.insert(0, 'src')

from storage.dynamodb_storage import DynamoDBStorage
from dotenv import load_dotenv

load_dotenv()

async def cleanup_duplicates():
    """Удаляет дубликаты, оставляя самую свежую версию каждого сигнала"""
    
    # Инициализируем storage
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'trading-signals-eu')
    region = os.getenv('AWS_REGION', 'eu-west-1')
    storage = DynamoDBStorage(table_name=table_name, region=region)
    
    # Загружаем все сигналы
    signals = await storage.load_signals()
    print(f"📊 Найдено сигналов: {len(signals)}")
    
    # Группируем по ключу: (exchange, symbol, condition, target_price)
    signal_groups = defaultdict(list)
    
    for signal in signals:
        key = (
            signal.exchange.value,
            signal.symbol,
            signal.condition.value,
            float(signal.target_price)
        )
        signal_groups[key].append(signal)
    
    # Находим дубликаты
    duplicates_found = 0
    duplicates_removed = 0
    
    for key, group in signal_groups.items():
        if len(group) > 1:
            duplicates_found += len(group) - 1
            print(f"\n🔍 Найден дубликат: {key[0]} {key[1]} {key[2]} ${key[3]}")
            print(f"   Копий: {len(group)}")
            
            # Сортируем по дате обновления (самый новый - первый)
            group.sort(key=lambda s: s.updated_at, reverse=True)
            
            # Оставляем первый (самый новый), удаляем остальные
            keep = group[0]
            remove = group[1:]
            
            print(f"   ✅ Оставляем: {keep.id} (updated: {keep.updated_at})")
            
            for signal in remove:
                print(f"   ❌ Удаляем: {signal.id} (updated: {signal.updated_at})")
                success = await storage.delete_signal(signal.id)
                if success:
                    duplicates_removed += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Готово!")
    print(f"📊 Дубликатов найдено: {duplicates_found}")
    print(f"🗑️  Дубликатов удалено: {duplicates_removed}")
    print(f"📈 Уникальных сигналов осталось: {len(signal_groups)}")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
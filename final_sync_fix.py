with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Заменить asyncio.run на прямой синхронный вызов
for i, line in enumerate(lines):
    if 'signals = asyncio.run(storage.get_all_signals())' in line:
        indent = '        '
        # Вставляем многострочный код правильно
        replacement = [
            indent + '# Синхронный вызов к DynamoDB\n',
            indent + 'try:\n',
            indent + '    response = storage.table.scan()\n',
            indent + '    items = response.get("Items", [])\n',
            indent + '    signals = [storage._item_to_signal(item) for item in items if item.get("entity_type") == "signal"]\n',
            indent + 'except Exception as e:\n',
            indent + '    logger.error(f"Failed to load signals: {e}")\n',
            indent + '    signals = []\n'
        ]
        # Удаляем старую строку и вставляем новый код
        lines[i:i+1] = replacement
        break

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed!')
with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти функцию load_signals_to_dropdown и добавить nest_asyncio
for i, line in enumerate(lines):
    if 'def load_signals_to_dropdown(user_id: str):' in line:
        # Добавляем import nest_asyncio в начало функции
        # Ищем следующую строку после def
        next_line_idx = i + 2  # Пропускаем docstring
        while '"""' in lines[next_line_idx]:
            next_line_idx += 1
        
        # Вставляем nest_asyncio.apply() после try:
        for j in range(next_line_idx, next_line_idx + 5):
            if 'try:' in lines[j]:
                lines.insert(j + 1, '            import nest_asyncio\n')
                lines.insert(j + 2, '            nest_asyncio.apply()\n')
                break
        break

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Dropdown fixed!')
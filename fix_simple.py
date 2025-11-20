with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти начало функции get_signals_table и добавить nest_asyncio
for i, line in enumerate(lines):
    if 'def get_signals_table(user_id: str = "") -> pd.DataFrame:' in line:
        # Добавляем import и apply перед функцией
        lines.insert(i, '    import nest_asyncio\n')
        lines.insert(i+1, '    nest_asyncio.apply()\n')
        break

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed with nest_asyncio!')
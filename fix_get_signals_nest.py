with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти функцию get_signals_table и добавить nest_asyncio после try:
for i, line in enumerate(lines):
    if 'def get_signals_table(user_id: str = "") -> pd.DataFrame:' in line:
        # Найти следующую строку с try:
        for j in range(i+1, i+5):
            if 'try:' in lines[j]:
                # Вставить nest_asyncio после try:
                indent = '        '
                lines.insert(j+1, indent + 'import nest_asyncio\n')
                lines.insert(j+2, indent + 'nest_asyncio.apply()\n')
                break
        break

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Added nest_asyncio to get_signals_table!')
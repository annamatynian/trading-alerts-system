with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Изменяем сигнатуру функции
old_signature = 'def sync_from_sheets() -> Tuple[str, pd.DataFrame]:'
new_signature = 'def sync_from_sheets(user_id: str = "") -> Tuple[str, pd.DataFrame]:'
content = content.replace(old_signature, new_signature)

# Заменяем все вызовы get_signals_table() на get_signals_table(user_id) внутри sync_from_sheets
# Находим функцию и заменяем внутри неё
lines = content.split('\n')
new_lines = []
inside_sync = False

for line in lines:
    if 'def sync_from_sheets(user_id: str = "")' in line:
        inside_sync = True
    elif inside_sync and line.startswith('def ') and 'sync_from_sheets' not in line:
        inside_sync = False
    
    # Внутри функции sync_from_sheets заменяем get_signals_table() на get_signals_table(user_id)
    if inside_sync and 'get_signals_table()' in line:
        line = line.replace('get_signals_table()', 'get_signals_table(user_id)')
    
    new_lines.append(line)

content = '\n'.join(new_lines)

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed sync_from_sheets!')
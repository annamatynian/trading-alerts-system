with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти строки с get_signals_table внутри sync_from_sheets
for i, line in enumerate(lines):
    if i >= 573 and i <= 635:  # Диапазон функции sync_from_sheets
        if 'get_signals_table' in line:
            print(f'Line {i+1}: {line.strip()}')
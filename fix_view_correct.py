with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти функцию get_signals_table и сделать её async
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Найти определение функции
    if 'def get_signals_table(user_id: str = "") -> pd.DataFrame:' in line:
        # Заменить def на async def
        new_lines.append(line.replace('def get_signals_table', 'async def get_signals_table'))
        i += 1
        continue
    
    # Заменить asyncio.run на await
    if 'signals = asyncio.run(storage.get_all_signals())' in line:
        indent = line[:line.index('signals')]
        new_lines.append(indent + 'signals = await storage.load_signals()\n')
        i += 1
        continue
    
    new_lines.append(line)
    i += 1

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Fixed!')
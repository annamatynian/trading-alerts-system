with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

inside_get_signals = False
for i, line in enumerate(lines):
    # Нашли начало get_signals_table
    if 'def get_signals_table(user_id: str = "") -> pd.DataFrame:' in line:
        lines[i] = line.replace('def get_signals_table', 'async def get_signals_table')
        inside_get_signals = True
        continue
    
    # Внутри get_signals_table заменяем asyncio.run на await
    if inside_get_signals:
        if 'signals = asyncio.run(storage.get_all_signals())' in line:
            indent = line[:line.index('signals')]
            lines[i] = indent + 'signals = await storage.load_signals()\n'
        
        # Вышли из функции
        if line.startswith('async def ') or (line.startswith('def ') and 'get_signals_table' not in line):
            inside_get_signals = False

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed only get_signals_table!')
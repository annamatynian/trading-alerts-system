with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Делаем get_signals_table асинхронной
content = content.replace(
    'def get_signals_table(user_id: str = "") -> pd.DataFrame:',
    'async def get_signals_table(user_id: str = "") -> pd.DataFrame:'
)

# Заменяем asyncio.run на await
content = content.replace(
    'signals = asyncio.run(storage.get_all_signals())',
    'signals = await storage.load_signals()'
)

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Made get_signals_table async!')
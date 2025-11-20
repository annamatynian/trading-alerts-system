with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти async def get_signals_table и заменить обратно на def
for i, line in enumerate(lines):
    if 'async def get_signals_table(user_id: str = "") -> pd.DataFrame:' in line:
        lines[i] = line.replace('async def get_signals_table', 'def get_signals_table')
    
    # Заменить await на прямой синхронный вызов через boto3
    if 'signals = await storage.load_signals()' in line:
        indent = line[:line.index('signals')]
        new_code = f'''{indent}# Прямой синхронный вызов к DynamoDB
{indent}response = storage.table.scan()
{indent}items = response.get('Items', [])
{indent}signals = []
{indent}for item in items:
{indent}    if item.get('entity_type') == 'signal':
{indent}        try:
{indent}            signal = storage._item_to_signal(item)
{indent}            signals.append(signal)
{indent}        except:
{indent}            pass
'''
        lines[i] = new_code

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Created sync version!')
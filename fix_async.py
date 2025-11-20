with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '        signals = asyncio.run(storage.get_all_signals())'
new = '''        # Безопасный вызов async функции из sync контекста
        try:
            loop = asyncio.get_event_loop()
            signals = loop.run_until_complete(storage.get_all_signals())
        except RuntimeError:
            # Если loop уже запущен, используем nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            signals = asyncio.run(storage.get_all_signals())'''

content = content.replace(old, new)

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')
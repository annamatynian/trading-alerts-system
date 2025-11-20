with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем asyncio.run на синхронный вызов
old = '        signals = asyncio.run(storage.get_all_signals())'
new = '''        # Синхронный вызов через обертку
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            signals = loop.run_until_complete(storage.load_signals())
        finally:
            loop.close()'''

content = content.replace(old, new)

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')
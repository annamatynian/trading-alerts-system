with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Убрать nest_asyncio из get_signals_table
new_lines = []
skip_next = False
for i, line in enumerate(lines):
    if 'import nest_asyncio' in line and i > 360 and i < 380:
        skip_next = True
        continue
    if skip_next and 'nest_asyncio.apply()' in line:
        skip_next = False
        continue
    new_lines.append(line)

# Также убрать из load_signals_to_dropdown
final_lines = []
skip_next2 = False
for i, line in enumerate(new_lines):
    if 'import nest_asyncio' in line and i > 640 and i < 660:
        skip_next2 = True
        continue
    if skip_next2 and 'nest_asyncio.apply()' in line:
        skip_next2 = False
        continue
    final_lines.append(line)

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

print('Removed nest_asyncio!')
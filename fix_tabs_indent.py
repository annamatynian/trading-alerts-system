with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти main_app и добавить gr.Tabs() + отступы для всех вкладок
in_main_app = False
tabs_added = False
new_lines = []

for i, line in enumerate(lines):
    if 'with gr.Column(visible=False) as main_app:' in line:
        new_lines.append(line)
        in_main_app = True
        tabs_added = False
        continue
    
    if in_main_app and not tabs_added:
        # Добавить gr.Tabs() перед первой вкладкой
        if 'with gr.Tab(' in line:
            new_lines.append('            with gr.Tabs():\n')
            # Добавить 4 пробела к текущей строке
            new_lines.append('    ' + line)
            tabs_added = True
            continue
    
    # Если внутри main_app и после gr.Tabs(), добавляем отступы
    if in_main_app and tabs_added:
        # Проверяем не вышли ли из main_app
        if line.strip() and not line.startswith(' ' * 8):
            in_main_app = False
            tabs_added = False
        else:
            # Добавляем 4 пробела отступа
            new_lines.append('    ' + line)
            continue
    
    new_lines.append(line)

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✅ Fixed tabs indentation!')
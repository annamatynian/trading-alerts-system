with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти строку с main_app и добавить gr.Tabs() после неё
for i, line in enumerate(lines):
    if 'with gr.Column(visible=False) as main_app:' in line:
        # Вставить gr.Tabs() после main_app
        indent = '            '
        lines.insert(i+1, '\n')
        lines.insert(i+2, indent + 'with gr.Tabs():\n')
        break

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('✅ Added gr.Tabs() container!')
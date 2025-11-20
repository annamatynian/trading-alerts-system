with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти строку sync_btn.click и добавить inputs после fn=
for i, line in enumerate(lines):
    if 'sync_btn.click(' in line:
        # Найти следующую строку после fn=sync_from_sheets,
        if i+1 < len(lines) and 'fn=sync_from_sheets,' in lines[i+1]:
            # Вставить inputs после fn строки
            indent = '                    '
            lines.insert(i+2, indent + 'inputs=[current_user],\n')
            break

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Added inputs to sync button!')
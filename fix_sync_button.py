with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем sync_btn.click без inputs на версию с inputs
old_click = '''                sync_btn.click(
                    fn=sync_from_sheets,
                    outputs=[sync_output, sync_table]
                )'''

new_click = '''                sync_btn.click(
                    fn=sync_from_sheets,
                    inputs=[current_user],
                    outputs=[sync_output, sync_table]
                )'''

content = content.replace(old_click, new_click)

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed sync button!')
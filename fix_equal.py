with open('app_with_auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_text = '        condition_symbol = ">" if condition.lower() == "above" else "<"'

new_text = '''        if condition.lower() == "above":
            condition_symbol = ">"
        elif condition.lower() == "below":
            condition_symbol = "<"
        elif condition.lower() == "equal":
            condition_symbol = "="
        else:
            condition_symbol = "?"'''

content = content.replace(old_text, new_text)

with open('app_with_auth.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')
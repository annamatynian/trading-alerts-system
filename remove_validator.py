with open('src/models/signal.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найдём и удалим валидатор (строки с @validator('percentage_threshold') до return v)
new_lines = []
skip = False
for i, line in enumerate(lines):
    if '@validator(\'percentage_threshold\')' in line:
        skip = True
        continue
    if skip and 'return v' in line:
        skip = False
        continue
    if not skip:
        new_lines.append(line)

with open('src/models/signal.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Validator removed!')
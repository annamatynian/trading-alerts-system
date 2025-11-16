#!/usr/bin/env python3
"""
Скрипт для создания Lambda deployment пакета БЕЗ Docker
Скачивает правильные Linux-версии библиотек и собирает ZIP
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
import tempfile

print("🚀 Lambda Package Builder - БЕЗ Docker!")
print("=" * 60)

# Путь к проекту
PROJECT_ROOT = Path(__file__).parent
LAMBDA_PACKAGE = PROJECT_ROOT / "lambda_package"
REQUIREMENTS = PROJECT_ROOT / "requirements_lambda.txt"
SRC_DIR = PROJECT_ROOT / "src"
LAMBDA_FUNCTION = PROJECT_ROOT / "lambda_function.py"

# Проверки
if not REQUIREMENTS.exists():
    print(f"❌ Не найден файл: {REQUIREMENTS}")
    sys.exit(1)

if not SRC_DIR.exists():
    print(f"❌ Не найдена папка: {SRC_DIR}")
    sys.exit(1)

if not LAMBDA_FUNCTION.exists():
    print(f"❌ Не найден файл: {LAMBDA_FUNCTION}")
    sys.exit(1)

print(f"✅ Проект: {PROJECT_ROOT}")
print(f"✅ Requirements: {REQUIREMENTS}")
print()

# Шаг 1: Очистка старой папки
print("🗑️  Шаг 1: Очистка старой папки lambda_package...")
if LAMBDA_PACKAGE.exists():
    shutil.rmtree(LAMBDA_PACKAGE)
    print("   Старая папка удалена")
LAMBDA_PACKAGE.mkdir()
print("   Новая папка создана")
print()

# Шаг 2: Создание временной папки для скачивания
print("📦 Шаг 2: Скачивание Linux-версий библиотек...")
temp_dir = Path(tempfile.mkdtemp())
print(f"   Временная папка: {temp_dir}")

try:
    # Читаем requirements и разделяем на бинарные и исходные
    with open(REQUIREMENTS, 'r') as f:
        requirements_lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Отделяем pybit от остальных
    binary_requirements = [req for req in requirements_lines if not req.startswith('pybit')]
    source_requirements = [req for req in requirements_lines if req.startswith('pybit')]
    
    print(f"   Бинарных пакетов: {len(binary_requirements)}")
    print(f"   Из исходников: {len(source_requirements)}")
    print()
    
    # ЭТАП 1: Скачиваем бинарные пакеты для Linux
    if binary_requirements:
        print("   📥 Этап 1: Скачивание бинарных пакетов для Linux...")
        # Создаем временный requirements файл
        temp_req_binary = temp_dir / "requirements_binary.txt"
        with open(temp_req_binary, 'w') as f:
            f.write('\n'.join(binary_requirements))
        
        cmd = [
            sys.executable, "-m", "pip", "download",
            "-r", str(temp_req_binary),
            "-d", str(temp_dir),
            "--platform", "manylinux2014_x86_64",
            "--python-version", "3.11",
            "--implementation", "cp",
            "--only-binary=:all:"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Ошибка при скачивании бинарных пакетов:")
            print(result.stderr)
            sys.exit(1)
        
        print("      ✅ Бинарные пакеты скачаны")
    
    # ЭТАП 2: Скачиваем pybit (пробуем сначала wheel, потом исходники)
    if source_requirements:
        print("   📥 Этап 2: Скачивание pybit...")
        for req in source_requirements:
            # Попытка 1: Скачать wheel для Linux (если есть)
            cmd_wheel = [
                sys.executable, "-m", "pip", "download",
                req,
                "-d", str(temp_dir),
                "--platform", "manylinux2014_x86_64",
                "--python-version", "3.11",
                "--implementation", "cp",
                "--only-binary=:all:",
                "--no-deps"
            ]
            
            result = subprocess.run(cmd_wheel, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"      ✅ {req} скачан (бинарный wheel)")
            else:
                # Попытка 2: Если wheel нет, качаем любую доступную версию без платформы
                print(f"      ⚠️  Бинарный wheel не найден, пробуем универсальный...")
                cmd_any = [
                    sys.executable, "-m", "pip", "download",
                    req,
                    "-d", str(temp_dir),
                    "--no-deps"
                ]
                
                result2 = subprocess.run(cmd_any, capture_output=True, text=True)
                
                if result2.returncode != 0:
                    print(f"❌ Ошибка при скачивании {req}:")
                    print(result2.stderr)
                    print("\n⚠️  Попробуем установить напрямую в lambda_package...")
                else:
                    print(f"      ✅ {req} скачан (универсальная версия)")
    
    print("   ✅ Все библиотеки скачаны")
    print()
    
    # Шаг 3: Распаковка wheel-файлов
    print("📂 Шаг 3: Распаковка wheel-файлов...")
    wheel_files = list(temp_dir.glob("*.whl"))
    print(f"   Найдено wheel-файлов: {len(wheel_files)}")
    
    for wheel_file in wheel_files:
        print(f"   Распаковка: {wheel_file.name}")
        with zipfile.ZipFile(wheel_file, 'r') as zip_ref:
            zip_ref.extractall(LAMBDA_PACKAGE)
    
    # Распаковка tar.gz файлов (для pybit)
    tar_files = list(temp_dir.glob("*.tar.gz"))
    if tar_files:
        print(f"   Найдено tar.gz файлов: {len(tar_files)}")
        for tar_file in tar_files:
            print(f"   Устанавливаем из исходников: {tar_file.name}")
            # Устанавливаем в lambda_package
            cmd = [
                sys.executable, "-m", "pip", "install",
                str(tar_file),
                "-t", str(LAMBDA_PACKAGE),
                "--no-deps"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
    
    # Если pybit не был скачан - установим его напрямую
    if source_requirements and not tar_files and not any('pybit' in wf.name.lower() for wf in wheel_files):
        print("   ⚠️  pybit не был скачан, устанавливаем напрямую...")
        for req in source_requirements:
            cmd = [
                sys.executable, "-m", "pip", "install",
                req,
                "-t", str(LAMBDA_PACKAGE),
                "--no-deps"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"      ✅ {req} установлен напрямую")
            else:
                print(f"      ❌ Не удалось установить {req}")
                print(f"      ⚠️  Продолжаем без него...")
    
    print("   ✅ Все библиотеки распакованы")
    print()
    
    # Шаг 4: Удаление ненужных файлов
    print("🧹 Шаг 4: Очистка от мусора...")
    patterns_to_remove = [
        "*.dist-info",
        "*.egg-info",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "tests",
        "test"
    ]
    
    removed_count = 0
    for pattern in patterns_to_remove:
        for item in LAMBDA_PACKAGE.rglob(pattern):
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            removed_count += 1
    
    print(f"   Удалено ненужных файлов: {removed_count}")
    print()
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    sys.exit(1)
finally:
    # Удаляем временную папку
    shutil.rmtree(temp_dir)
    print("   🗑️  Временная папка удалена")

# Шаг 5: Копирование кода проекта
print("📋 Шаг 5: Копирование кода проекта...")
# Копируем папку src
dest_src = LAMBDA_PACKAGE / "src"
shutil.copytree(SRC_DIR, dest_src)
print(f"   ✅ Скопирована папка: src")

# Копируем lambda_function.py
shutil.copy2(LAMBDA_FUNCTION, LAMBDA_PACKAGE / "lambda_function.py")
print(f"   ✅ Скопирован файл: lambda_function.py")
print()

# Шаг 6: Создание ZIP архива
print("📦 Шаг 6: Создание ZIP архива...")
zip_path = PROJECT_ROOT / "lambda_deployment.zip"

# Удаляем старый ZIP если есть
if zip_path.exists():
    zip_path.unlink()

# Создаем новый ZIP
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(LAMBDA_PACKAGE):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(LAMBDA_PACKAGE)
            zipf.write(file_path, arcname)

zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
print(f"   ✅ ZIP создан: {zip_path.name}")
print(f"   📊 Размер: {zip_size_mb:.2f} MB")
print()

# Финал
print("=" * 60)
print("🎉 УСПЕХ! Lambda пакет готов!")
print("=" * 60)
print(f"📦 Файл для загрузки: {zip_path}")
print(f"📁 Папка с библиотеками: {LAMBDA_PACKAGE}")
print()
print("🚀 Следующий шаг:")
print("   1. Откройте AWS Lambda Console")
print("   2. Выберите вашу функцию")
print("   3. Upload from → .zip file")
print(f"   4. Загрузите: {zip_path.name}")
print()
print("✨ Готово! Удачи с деплоем!")

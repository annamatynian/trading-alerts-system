"""
Pytest configuration file
"""
import sys
import os

# Добавляем src в путь Python
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, os.path.abspath(src_path))

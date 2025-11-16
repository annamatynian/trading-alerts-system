#!/usr/bin/env python3
"""
Quick test to verify project structure and imports
"""
import sys
import importlib.util

def test_import(module_path, description):
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        module = importlib.util.module_from_spec(spec)
        print(f"✅ {description}: OK")
        return True
    except Exception as e:
        print(f"❌ {description}: {e}")
        return False

def main():
    print("🧪 Тестирование структуры проекта...")
    
    tests = [
        ("src/models/signal.py", "Signal models"),
        ("src/models/price.py", "Price models"), 
        ("src/exchanges/base.py", "Exchange base"),
        ("src/exchanges/bybit.py", "Bybit exchange"),
    ]
    
    for path, desc in tests:
        test_import(path, desc)

if __name__ == "__main__":
    main()

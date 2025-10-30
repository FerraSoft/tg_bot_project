#!/usr/bin/env python3
"""
Простой тестовый раннер для телеграм-бота.
Запускает базовые тесты для проверки работоспособности системы.
"""

import subprocess
import sys
import os
from datetime import datetime
import locale

def run_tests():
    """Запуск основных тестов"""
    # Устанавливаем UTF-8 для корректного вывода эмодзи
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            pass  # Если UTF-8 не доступен, продолжаем без него

    print("[TEST] Запуск тестирования телеграм-бота")
    print(f"[TIME] Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Проверяем, установлен ли pytest
    try:
        import pytest
        print("[OK] pytest найден")
    except ImportError:
        print("[INSTALL] Установка pytest...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"], check=True)

    # Запускаем тесты
    test_dirs = [
        "test_utils/",
        "test_services/",
        "test_handlers/",
        "test_integration/"
    ]

    success = True

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            print(f"\n[RUN] Запуск тестов из {test_dir}")
            result = subprocess.run([
                sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print(f"[PASS] Тесты {test_dir} - ПРОЙДЕНЫ")
                print(result.stdout)
            else:
                print(f"[FAIL] Тесты {test_dir} - ПРОВАЛЕНЫ")
                print(result.stderr)
                success = False

    # Итоговый результат
    print(f"\n[FINISH] Тестирование завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if success:
        print("[SUCCESS] Все тесты пройдены успешно!")
        return 0
    else:
        print("[ERROR] Некоторые тесты провалились")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
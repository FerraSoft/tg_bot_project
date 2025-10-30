# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
#!/usr/bin/env python3
"""
Скрипт для запуска полного тестирования телеграм-бота.
Выполняет все типы тестов и генерирует отчеты.
"""

import subprocess
import sys
import os
import argparse
from datetime import datetime
import json

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_command(cmd: str, description: str) -> bool:
    """
    Запуск команды с логированием.

    Args:
        cmd: Команда для выполнения
        description: Описание команды

    Returns:
        True если команда выполнена успешно
    """
    print(f"\n🔄 {description}")
    print(f"Выполняется: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ {description} - УСПЕХ")
            if result.stdout:
                print(f"Вывод: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - ОШИБКА")
            print(f"Код ошибки: {result.returncode}")
            if result.stderr:
                print(f"Ошибка: {result.stderr.strip()}")
            return False

    except Exception as e:
        print(f"❌ {description} - ИСКЛЮЧЕНИЕ: {e}")
        return False


def install_test_dependencies():
    """Установка зависимостей для тестирования"""
    print("\n📦 Установка зависимостей для тестирования...")

    # Проверяем, установлен ли pytest
    try:
        import pytest
        print("✅ pytest уже установлен")
    except ImportError:
        print("📥 Установка pytest...")
        if not run_command("pip install pytest pytest-asyncio pytest-mock", "Установка основных зависимостей pytest"):
            print("❌ Не удалось установить зависимости pytest")
            return False

    # Устанавливаем зависимости из файла
    if os.path.exists("requirements-test.txt"):
        if not run_command("pip install -r requirements-test.txt", "Установка тестовых зависимостей"):
            print("⚠️ Некоторые тестовые зависимости не удалось установить")
    else:
        print("⚠️ Файл requirements-test.txt не найден")

    return True


def run_unit_tests():
    """Запуск unit тестов"""
    return run_command(
        "python -m pytest tests/ -v --tb=short -m unit",
        "Запуск unit тестов"
    )


def run_integration_tests():
    """Запуск интеграционных тестов"""
    return run_command(
        "python -m pytest test_integration/ -v --tb=short",
        "Запуск интеграционных тестов"
    )


def run_all_tests():
    """Запуск всех тестов"""
    return run_command(
        "python -m pytest tests/ test_utils/ test_services/ test_handlers/ test_integration/ -v --tb=short",
        "Запуск всех тестов"
    )


def run_coverage_report():
    """Генерация отчета о покрытии кода"""
    success = run_command(
        "python -m pytest --cov=telegram_bot --cov-report=html --cov-report=term-missing tests/ test_utils/ test_services/ test_handlers/ test_integration/",
        "Генерация отчета покрытия"
    )

    if success:
        print("📊 Отчет покрытия сохранен в htmlcov/index.html")
        print("📈 Краткий отчет покрытия выведен выше")

    return success


def run_performance_tests():
    """Запуск тестов производительности"""
    return run_command(
        "python -m pytest -v --tb=short -k performance",
        "Запуск тестов производительности"
    )


def lint_code():
    """Проверка кода линтером"""
    print("\n🔍 Проверка качества кода...")

    # Проверяем, установлен ли flake8
    try:
        import flake8
    except ImportError:
        print("📥 Установка flake8...")
        if not run_command("pip install flake8", "Установка flake8"):
            print("⚠️ Пропускаем проверку линтером")
            return True

    # Запускаем flake8
    return run_command(
        "python -m flake8 telegram_bot/ --count --select=E9,F63,F7,F82 --show-source --statistics",
        "Проверка кода flake8 (критические ошибки)"
    )


def check_imports():
    """Проверка корректности импортов"""
    print("\n🔗 Проверка импортов...")

    # Проверяем основные модули новой архитектуры
    modules_to_check = [
        "core.config",
        "core.exceptions",
        "utils.validators",
        "utils.formatters",
        "utils.helpers",
        "services.user_service",
        "handlers.base_handler",
        "handlers.user_handlers",
        "database.models",
        "database.repository"
    ]

    all_success = True

    for module in modules_to_check:
        try:
            __import__(module)
            print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            all_success = False

    return all_success


def analyze_test_results():
    """Анализ результатов тестирования"""
    print("\n📊 Анализ результатов тестирования...")

    try:
        # Читаем результаты последних тестов
        result_file = "test_results.json"

        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            print("📈 Статистика тестирования:")
            print(f"   Всего тестов: {results.get('total', 0)}")
            print(f"   Пройдено: {results.get('passed', 0)}")
            print(f"   Провалено: {results.get('failed', 0)}")
            print(f"   Пропущено: {results.get('skipped', 0)}")
            print(f"   Время выполнения: {results.get('duration', 0):.2f} сек")

            success_rate = (results.get('passed', 0) / results.get('total', 1)) * 100
            print(f"   Успешность: {success_rate:.1f}%")

            if success_rate >= 90:
                print("🎉 Отличные результаты тестирования!")
            elif success_rate >= 70:
                print("👍 Хорошие результаты, но есть над чем поработать")
            else:
                print("⚠️ Требуется улучшение качества кода и тестов")

        else:
            print("📋 Результаты тестирования не найдены")

    except Exception as e:
        print(f"⚠️ Не удалось проанализировать результаты: {e}")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="Запуск тестирования телеграм-бота")
    parser.add_argument("--unit", action="store_true", help="Запустить только unit тесты")
    parser.add_argument("--integration", action="store_true", help="Запустить только интеграционные тесты")
    parser.add_argument("--coverage", action="store_true", help="Генерировать отчет покрытия")
    parser.add_argument("--performance", action="store_true", help="Запустить тесты производительности")
    parser.add_argument("--lint", action="store_true", help="Проверить код линтером")
    parser.add_argument("--quick", action="store_true", help="Быстрое тестирование (только критические тесты)")

    args = parser.parse_args()

    print("🧪 Начинаем тестирование телеграм-бота")
    print(f"🕐 Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Установка зависимостей
    if not install_test_dependencies():
        print("❌ Не удалось установить зависимости")
        return 1

    # Проверка импортов
    if not check_imports():
        print("❌ Проблемы с импортами модулей")
        return 1

    # Проверка линтера
    if args.lint:
        if not lint_code():
            print("❌ Найдены проблемы с качеством кода")
            return 1

    # Запуск тестов
    test_success = False

    if args.unit:
        test_success = run_unit_tests()
    elif args.integration:
        test_success = run_integration_tests()
    elif args.performance:
        test_success = run_performance_tests()
    elif args.quick:
        # Быстрое тестирование - только основные компоненты
        test_success = run_command(
            "python -m pytest test_utils/ test_services/ -v --tb=short",
            "Быстрое тестирование"
        )
    else:
        # Полное тестирование
        test_success = run_all_tests()

    # Генерация отчета покрытия
    if args.coverage and test_success:
        run_coverage_report()

    # Анализ результатов
    analyze_test_results()

    # Итоговый результат
    print(f"\n🏁 Тестирование завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if test_success:
        print("✅ Все тесты пройдены успешно!")
        return 0
    else:
        print("❌ Некоторые тесты провалились")
        return 1


if __name__ == "__main__":
    sys.exit(main())
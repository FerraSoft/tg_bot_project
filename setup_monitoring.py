#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическая настройка системы мониторинга.
Создает конфигурацию и проверяет все компоненты.
"""

import os
import json
import sys
import io
from pathlib import Path

# Установка UTF-8 кодировки
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def print_header(text):
    """Печатает заголовок с эмодзи"""
    print(f"\n🚀 {text}")
    print("=" * (len(text) + 3))

def print_success(text):
    """Печатает успешное сообщение"""
    print(f"✅ {text}")

def print_warning(text):
    """Печатает предупреждение"""
    print(f"⚠️ {text}")

def print_error(text):
    """Печатает ошибку"""
    print(f"❌ {text}")

def check_dependencies():
    """Проверка зависимостей"""
    print_header("Проверка зависимостей")

    required_packages = [
        'prometheus_client',
        'sentry-sdk',
        'flask',
        'requests'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_success(f"{package} - установлен")
        except ImportError:
            missing_packages.append(package)
            print_error(f"{package} - не установлен")

    if missing_packages:
        print_warning(f"Установите недостающие пакеты: pip install {' '.join(missing_packages)}")
        return False

    return True

def setup_configuration():
    """Настройка конфигурации"""
    print_header("Настройка конфигурации")

    config_path = "config_local.py"

    if not os.path.exists(config_path):
        print_warning(f"Файл {config_path} не найден. Создайте его на основе config_template.py")
        return False

    # Проверяем, что в конфигурации есть настройки мониторинга
    with open(config_path, 'r', encoding='utf-8') as f:
        config_content = f.read()

    monitoring_settings = [
        'ENABLE_SENTRY',
        'SENTRY_DSN',
        'PROMETHEUS_PORT',
        'ENABLE_DEVELOPER_NOTIFICATIONS',
        'DEVELOPER_CHAT_ID'
    ]

    missing_settings = []
    for setting in monitoring_settings:
        if setting not in config_content:
            missing_settings.append(setting)

    if missing_settings:
        print_warning("Добавьте настройки мониторинга в config_local.py:")
        print("\n# Мониторинг ошибок")
        print("ENABLE_SENTRY = True")
        print('SENTRY_DSN = "http://localhost:8000/api/1/project/your-project/dsn/"')
        print("PROMETHEUS_PORT = 8000")
        print("ENABLE_DEVELOPER_NOTIFICATIONS = True")
        print("DEVELOPER_CHAT_ID = 123456789  # Ваш Telegram ID")
        return False

    print_success("Конфигурация настроена правильно")
    return True

def check_glitchtip_setup():
    """Проверка настройки GlitchTip"""
    print_header("Проверка GlitchTip")

    # Проверяем docker-compose.yml
    docker_compose_path = "docker-compose.yml"
    if os.path.exists(docker_compose_path):
        with open(docker_compose_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'glitchtip' in content.lower():
                print_success("Docker Compose для GlitchTip настроен")
            else:
                print_warning("GlitchTip не найден в docker-compose.yml")
    else:
        print_warning("docker-compose.yml не найден. Создайте по инструкции в GLITCHTIP_SETUP.md")

def test_imports():
    """Тестирование импорта модулей мониторинга"""
    print_header("Тестирование импорта модулей")

    modules_to_test = [
        ('core.monitoring', 'MetricsCollector'),
        ('core.alerts', 'AlertManager'),
        ('prometheus_client', 'Counter'),
        ('sentry_sdk', 'init')
    ]

    all_good = True

    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print_success(f"{module_name}.{class_name} - доступен")
        except (ImportError, AttributeError) as e:
            print_error(f"{module_name}.{class_name} - ошибка: {e}")
            all_good = False

    return all_good

def check_documentation():
    """Проверка наличия документации"""
    print_header("Проверка документации")

    required_docs = [
        'MONITORING.md',
        'README_MONITORING.md',
        'GLITCHTIP_SETUP.md',
        'WEBHOOK_ALERTS.md',
        'START_MONITORING.md'
    ]

    all_docs_present = True

    for doc in required_docs:
        if os.path.exists(doc):
            print_success(f"{doc} - найден")
        else:
            print_error(f"{doc} - отсутствует")
            all_docs_present = False

    return all_docs_present

def create_sample_config():
    """Создание примера конфигурации"""
    print_header("Создание примера конфигурации мониторинга")

    sample_config = '''
# Пример настроек мониторинга для config_local.py

# Включение системы мониторинга
ENABLE_SENTRY = True
SENTRY_DSN = "http://localhost:8000/api/1/project/your-project-id/dsn/"

# Настройки Prometheus
PROMETHEUS_PORT = 8000

# Уведомления разработчиков
ENABLE_DEVELOPER_NOTIFICATIONS = True
DEVELOPER_CHAT_ID = 123456789  # Замените на ваш Telegram ID

# Логирование
LOG_CONFIG = {
    "level": "INFO",
    "file": "bot.log",
    "format": "json",
    "max_size": 10*1024*1024,
    "backup_count": 5
}
'''

    config_path = "config_monitoring_sample.py"
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(sample_config)

    print_success(f"Пример конфигурации создан: {config_path}")

def main():
    """Главная функция настройки"""
    print("🔧 Автоматическая настройка системы мониторинга")
    print("=" * 50)

    all_checks_passed = True

    # Проверяем зависимости
    if not check_dependencies():
        all_checks_passed = False

    # Проверяем конфигурацию
    if not setup_configuration():
        all_checks_passed = False

    # Проверяем GlitchTip
    check_glitchtip_setup()

    # Тестируем импорты
    if not test_imports():
        all_checks_passed = False

    # Проверяем документацию
    if not check_documentation():
        all_checks_passed = False

    # Создаем пример конфигурации
    create_sample_config()

    print("\n" + "=" * 50)
    if all_checks_passed:
        print("🎉 Настройка завершена успешно!")
        print("\n📋 Следующие шаги:")
        print("1. Настройте GlitchTip по инструкции в GLITCHTIP_SETUP.md")
        print("2. Получите DSN и добавьте в config_local.py")
        print("3. Запустите бота: python new_bot.py")
        print("4. Проверьте метрики: http://localhost:8000/metrics")
    else:
        print("⚠️ Требуются дополнительные настройки!")
        print("\n🔧 Исправьте проблемы и запустите настройку снова")

    print(f"\n📚 Документация в файлах:")
    for file in ['MONITORING.md', 'README_MONITORING.md', 'GLITCHTIP_SETUP.md', 'START_MONITORING.md']:
        if os.path.exists(file):
            print(f"• {file}")

if __name__ == "__main__":
    main()
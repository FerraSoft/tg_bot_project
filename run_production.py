#!/usr/bin/env python3
"""
Скрипт запуска телеграм-бота в продакшен среде.
Обеспечивает надежный запуск с обработкой ошибок и логированием.
"""

import sys
import os
import logging
import io
from datetime import datetime

# Исправляем кодировку для Windows
if os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения из .env файла
from dotenv import load_dotenv
load_dotenv()

from core.application import Application


def setup_logging():
    """Настройка системы логирования"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        format=log_format,
        level=logging.INFO,
        handlers=[
            logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'bot.log'), encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Отключаем логи от библиотек
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def check_environment():
    """Проверка окружения перед запуском"""
    print("🔍 Проверка окружения...")

    # Проверяем токен бота
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("❌ BOT_TOKEN не найден в переменных окружения!")
        print("💡 Добавьте BOT_TOKEN в файл .env или переменные окружения")
        return False

    print(f"✅ BOT_TOKEN найден (длина: {len(token)})")

    # Проверяем API ключи (опционально)
    api_keys = ['OPENWEATHER_API_KEY', 'NEWS_API_KEY', 'OPENAI_API_KEY']
    for key in api_keys:
        value = os.getenv(key)
        if value:
            print(f"✅ {key} найден")
        else:
            print(f"⚠️ {key} не найден (функция будет ограничена)")

    return True


def main():
    """Основная функция запуска"""
    print("🚀 Запуск телеграм-бота в продакшен среде")
    print(f"🕐 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Настраиваем логирование
    setup_logging()

    # Проверяем окружение
    if not check_environment():
        print("❌ Проверка окружения провалилась!")
        sys.exit(1)

    try:
        # Создаем приложение
        print("🏗️ Инициализация приложения...")
        app = Application("config_prod.py")

        # Показываем статус
        status = app.get_status()
        print("✅ Приложение инициализировано успешно!")
        print(f"📊 Статус: {status}")

        # Запускаем бота
        print("🎯 Запуск бота...")
        app.run()

    except KeyboardInterrupt:
        print("\n👋 Получен сигнал остановки (Ctrl+C)")
        print("🛑 Остановка бота...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logging.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)
    finally:
        print("🏁 Процесс завершен")


if __name__ == '__main__':
    main()
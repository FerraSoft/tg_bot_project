#!/usr/bin/env python3
"""
Новая версия телеграм-бота с модульной архитектурой.

Основные улучшения:
- Модульная архитектура с четким разделением ответственности
- Улучшенная обработка ошибок
- Гибкая система конфигурации
- Легкость тестирования и поддержки
"""

import sys
import os
import io
from dotenv import load_dotenv
load_dotenv()  # Загружаем переменные окружения из .env

# Исправляем кодировку для Windows
if os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from core.application import Application


def main():
    """Главная функция приложения"""
    try:
        # Получаем уровень логирования из переменной окружения
        log_level = os.getenv('LOG_LEVEL', 'INFO')

        # Создаем и запускаем приложение
        app = Application(log_level=log_level)
        print("🚀 Телеграм-бот запущен с новой архитектурой!")
        print(f"📊 Статус: {app.get_status()}")

        app.run()

    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
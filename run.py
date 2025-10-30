#!/usr/bin/env python3
"""
Простой скрипт запуска телеграм-бота.
Запускает основное приложение бота с учетом окружения Windows.
"""

import sys
import os
import subprocess
import io
import argparse

def main():
    # Исправляем кодировку для Windows
    if os.name == 'nt':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # Парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Запуск телеграм-бота с различными уровнями логирования')
    parser.add_argument('--log-level', choices=['ERROR', 'WARNING', 'INFO'],
                       default='INFO',
                       help='Уровень логирования: ERROR (только ошибки), WARNING (ошибки + предупреждения), INFO (ошибки + предупреждения + информация)')

    args = parser.parse_args()

    """Главная функция запуска"""
    try:
        # Получаем путь к директории скрипта
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Путь к основному скрипту new_bot.py
        bot_script = os.path.join(script_dir, 'new_bot.py')

        # Устанавливаем кодировку для Windows
        if os.name == 'nt':
            os.environ['PYTHONIOENCODING'] = 'utf-8'

        # Запускаем бота с указанным уровнем логирования
        print(f"🚀 Запуск телеграм-бота с уровнем логирования: {args.log_level}...")
        env = os.environ.copy()
        env['BOT_LOG_LEVEL'] = args.log_level

        result = subprocess.run([sys.executable, bot_script], cwd=script_dir, env=env)

        if result.returncode == 0:
            print("✅ Бот завершил работу успешно")
        else:
            print(f"❌ Бот завершился с ошибкой (код: {result.returncode})")

    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
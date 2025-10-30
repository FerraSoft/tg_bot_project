#!/usr/bin/env python3
"""
Отладка сервиса пользователей для выявления причины возврата None
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.user_service import UserService
from database.repository import UserRepository, ScoreRepository

async def debug_user_service():
    """Отладка сервиса пользователей"""
    print("НАЧАЛО ОТЛАДКИ СЕРВИСА ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 50)

    try:
        # Создаем репозитории
        user_repo = UserRepository("telegram_bot.db")
        score_repo = ScoreRepository("telegram_bot.db")

        # Создаем сервис
        user_service = UserService(user_repo, score_repo)

        print("1. Тестируем репозиторий пользователей напрямую...")

        # Тестируем репозиторий напрямую
        user_data = user_repo.get_by_id(123456789)
        print(f"   Прямой запрос пользователя 123456789: {user_data}")

        if user_data:
            print("   Найденные колонки:")
            for key, value in user_data.items():
                print(f"     {key}: {value}")
        else:
            print("   Пользователь не найден, создаем нового...")

            # Создаем пользователя напрямую через репозиторий
            user_data_to_create = {
                'telegram_id': 123456789,
                'username': 'debug_user',
                'first_name': 'Debug',
                'last_name': 'User',
                'joined_date': None,
                'last_activity': None
            }

            print("   Создание пользователя через репозиторий...")
            created_data = user_repo.create_user(user_data_to_create)
            print(f"   Результат создания: {created_data}")

            # Пробуем получить пользователя снова
            user_data = user_repo.get_by_id(123456789)
            print(f"   Повторный запрос пользователя: {user_data}")

        print("\n2. Тестируем сервис пользователей...")

        # Тестируем сервис пользователей
        user_profile = await user_service.get_or_create_user(
            123456789, "debug_user", "Debug", "User"
        )

        print(f"   Результат сервиса: {user_profile}")

        if user_profile:
            print("   Профиль создан успешно!")
            print(f"     ID: {user_profile.user_id}")
            print(f"     Имя: {user_profile.first_name}")
            print(f"     Репутация: {user_profile.reputation}")
        else:
            print("   Профиль не создан (None)")

        print("\n3. Проверяем таблицу пользователей...")

        # Проверяем таблицу напрямую
        connection = user_repo._get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (123456789,))
        direct_result = cursor.fetchone()

        print(f"   Прямой SQL запрос: {direct_result}")

        if direct_result:
            print("   Колонки в таблице:")
            for i, column in enumerate(cursor.description):
                print(f"     {column[0]}: {direct_result[i]}")

        connection.close()

    except Exception as e:
        print(f"[ERROR] Ошибка при отладке: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*50}")
    print("ОТЛАДКА ЗАВЕРШЕНА")

if __name__ == "__main__":
    asyncio.run(debug_user_service())
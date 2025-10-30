#!/usr/bin/env python3
"""
Интеграционный тест для проверки работы системы предупреждений.
Тестирует весь путь: добавление предупреждения → отображение в /info.
"""

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from database.repository import UserRepository, ScoreRepository
from services.user_service import UserService
from core.config import Config


class TestWarningsIntegration(unittest.TestCase):
    """Интеграционные тесты системы предупреждений"""

    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем временную базу данных для тестов
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()
        self.db_path = self.test_db.name

        # Инициализируем репозитории
        self.user_repo = UserRepository(self.db_path)
        self.score_repo = ScoreRepository(self.db_path)

        # Инициализируем сервис
        self.user_service = UserService(self.user_repo, self.score_repo)

    def tearDown(self):
        """Очистка после тестов"""
        try:
            os.unlink(self.db_path)
        except:
            pass

    async def asyncSetUp(self):
        """Асинхронная настройка"""
        pass

    def test_full_warnings_workflow(self):
        """Тест полного цикла работы с предупреждениями"""
        async def run_test():
            # Шаг 1: Создаем тестового пользователя
            user_id = 123456789
            username = "testuser"
            first_name = "Test"
            last_name = "User"

            profile = await self.user_service.get_or_create_user(
                user_id, username, first_name, last_name
            )

            # Проверяем, что пользователь создан без предупреждений
            self.assertIsNotNone(profile)
            self.assertEqual(profile.warnings, 0)
            self.assertEqual(profile.first_name, first_name)
            self.assertEqual(profile.username, username)

            # Шаг 2: Добавляем предупреждение (имитируем нецензурную лексику)
            result = await self.user_service.add_warning(
                user_id, "Нецензурная лексика", 0
            )

            # Проверяем, что предупреждение добавлено
            self.assertTrue(result)

            # Шаг 3: Получаем обновленный профиль (имитируем команду /info)
            updated_profile = await self.user_service.get_or_create_user(
                user_id, username, first_name, last_name
            )

            # Проверяем, что предупреждение отображается в профиле
            self.assertIsNotNone(updated_profile)
            self.assertEqual(updated_profile.warnings, 1)

            # Шаг 4: Проверяем данные непосредственно в базе данных
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Проверяем таблицу users
            cursor.execute("SELECT warnings FROM users WHERE telegram_id = ?", (user_id,))
            user_warnings = cursor.fetchone()
            self.assertIsNotNone(user_warnings)
            self.assertEqual(user_warnings[0], 1)

            # Проверяем таблицу warnings
            cursor.execute("SELECT COUNT(*) FROM warnings WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (user_id,))
            warnings_count = cursor.fetchone()
            self.assertEqual(warnings_count[0], 1)

            conn.close()

            print("✅ Тест полного цикла предупреждений пройден успешно")

        # Запускаем асинхронный тест
        asyncio.run(run_test())

    def test_multiple_warnings(self):
        """Тест добавления нескольких предупреждений"""
        async def run_test():
            user_id = 987654321

            # Создаем пользователя
            profile = await self.user_service.get_or_create_user(user_id, "multiuser", "Multi", "User")
            self.assertEqual(profile.warnings, 0)

            # Добавляем 3 предупреждения
            for i in range(3):
                result = await self.user_service.add_warning(
                    user_id, f"Предупреждение #{i+1}", 0
                )
                self.assertTrue(result)

            # Проверяем, что все предупреждения учтены
            updated_profile = await self.user_service.get_or_create_user(user_id, "multiuser", "Multi", "User")
            self.assertEqual(updated_profile.warnings, 3)

            print("✅ Тест множественных предупреждений пройден успешно")

        asyncio.run(run_test())

    def test_warnings_persistence(self):
        """Тест сохранения предупреждений между сессиями"""
        async def run_test():
            user_id = 555666777

            # Первая сессия: создаем пользователя и добавляем предупреждение
            profile1 = await self.user_service.get_or_create_user(user_id, "persist", "Persist", "User")
            self.assertEqual(profile1.warnings, 0)

            await self.user_service.add_warning(user_id, "Тестовое предупреждение", 0)

            profile2 = await self.user_service.get_or_create_user(user_id, "persist", "Persist", "User")
            self.assertEqual(profile2.warnings, 1)

            # Имитируем "перезапуск" - создаем новые репозитории и сервисы
            user_repo2 = UserRepository(self.db_path)
            score_repo2 = ScoreRepository(self.db_path)
            user_service2 = UserService(user_repo2, score_repo2)

            # Вторая сессия: проверяем, что данные сохранились
            profile3 = await user_service2.get_or_create_user(user_id, "persist", "Persist", "User")
            self.assertEqual(profile3.warnings, 1)

            print("✅ Тест сохранения предупреждений пройден успешно")

        asyncio.run(run_test())

    def test_admin_warning(self):
        """Тест предупреждения от администратора"""
        async def run_test():
            user_id = 111222333
            admin_id = 999888777

            # Создаем пользователя
            profile = await self.user_service.get_or_create_user(user_id, "adminuser", "Admin", "User")
            self.assertEqual(profile.warnings, 0)

            # Добавляем предупреждение от админа
            result = await self.user_service.add_warning(
                user_id, "Нарушение правил администратором", admin_id
            )
            self.assertTrue(result)

            # Проверяем предупреждение
            updated_profile = await self.user_service.get_or_create_user(user_id, "adminuser", "Admin", "User")
            self.assertEqual(updated_profile.warnings, 1)

            # Проверяем запись в таблице warnings
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT reason, admin_id FROM warnings
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
            """, (user_id,))

            warning_record = cursor.fetchone()
            self.assertIsNotNone(warning_record)
            self.assertEqual(warning_record[0], "Нарушение правил администратором")

            # Проверяем admin_id (внутренний ID админа)
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (admin_id,))
            admin_internal_id = cursor.fetchone()
            if admin_internal_id:
                self.assertEqual(warning_record[1], admin_internal_id[0])

            conn.close()

            print("✅ Тест предупреждения от администратора пройден успешно")

        asyncio.run(run_test())


def run_integration_tests():
    """Запуск интеграционных тестов"""
    print("=" * 50)
    print("ЗАПУСК ИНТЕГРАЦИОННЫХ ТЕСТОВ ПРЕДУПРЕЖДЕНИЙ")
    print("=" * 50)

    # Создаем тестовый набор
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWarningsIntegration)

    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("Система предупреждений работает корректно.")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ!")
        print("Необходимо проверить систему предупреждений.")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Тесты для проверки работы SUPER_ADMIN роли.
Проверяет корректность назначения ролей и доступ к командам.
"""

import logging
import sys
import os
from pathlib import Path

# Настраиваем кодировку для корректного вывода Unicode
sys.stdout.reconfigure(encoding='utf-8')

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

# Устанавливаем переменные окружения для тестов
os.environ['BOT_TOKEN'] = 'test_token_for_tests'
os.environ['ADMIN_IDS'] = '1278359005'
os.environ['SUPER_ADMIN_IDS'] = '1278359005'

from core.config import Config
from core.permissions import permission_manager, UserRole
from core.middleware import MiddlewareContext
from telegram import User, CallbackQuery


def test_super_admin_config():
    """Тест загрузки SUPER_ADMIN из конфигурации"""
    print("=== Тест загрузки SUPER_ADMIN из конфигурации ===")

    try:
        config = Config()
        print(f"✓ Конфигурация загружена")
        print(f"  SUPER_ADMIN_IDS: {config.bot_config.super_admin_ids}")
        print(f"  ADMIN_IDS: {config.bot_config.admin_ids}")

        # Проверяем что пользователь 1278359005 в SUPER_ADMIN_IDS
        assert 1278359005 in config.bot_config.super_admin_ids, "Пользователь не найден в SUPER_ADMIN_IDS"
        print("✓ Пользователь 1278359005 найден в SUPER_ADMIN_IDS")

        # Проверяем роль из конфигурации
        role = permission_manager.get_user_role_from_config(1278359005, config)
        assert role == UserRole.SUPER_ADMIN, f"Ожидалась роль SUPER_ADMIN, получена {role}"
        print("✓ Пользователь имеет роль SUPER_ADMIN из конфигурации")

        return True
    except Exception as e:
        print(f"✗ Ошибка в тесте конфигурации: {e}")
        return False


def test_super_admin_permissions():
    """Тест разрешений для SUPER_ADMIN"""
    print("\n=== Тест разрешений SUPER_ADMIN ===")

    try:
        config = Config()
        user_role = permission_manager.get_user_role_from_config(1278359005, config)
        assert user_role == UserRole.SUPER_ADMIN, f"Ожидалась роль SUPER_ADMIN, получена {user_role}"

        # Тестируем команды которые должны быть доступны SUPER_ADMIN
        super_admin_commands = [
            'report_error', 'admin_errors', 'analyze_error_ai',
            'process_all_errors_ai', 'add_error_to_todo', 'add_all_analyzed_to_todo',
            'menu_moderation', 'menu_admin', 'menu_triggers'
        ]

        for cmd in super_admin_commands:
            can_execute = permission_manager.can_execute_command(user_role, cmd)
            assert can_execute, f"Команда /{cmd} должна быть доступна SUPER_ADMIN"
            print(f"✓ Команда /{cmd} доступна SUPER_ADMIN")

        # Тестируем базовые команды
        basic_commands = ['start', 'help', 'info', 'rank', 'leaderboard', 'donate']
        for cmd in basic_commands:
            can_execute = permission_manager.can_execute_command(user_role, cmd)
            assert can_execute, f"Команда /{cmd} должна быть доступна SUPER_ADMIN"
            print(f"✓ Команда /{cmd} доступна SUPER_ADMIN")

        return True
    except Exception as e:
        print(f"✗ Ошибка в тесте разрешений: {e}")
        return False


async def test_middleware_super_admin():
    """Тест middleware с SUPER_ADMIN"""
    print("\n=== Test middleware with SUPER_ADMIN ===")

    try:
        config = Config()

        # Создаем фейковый callback update
        user = User(id=1278359005, first_name='Test Super Admin', is_bot=False)
        callback_query = CallbackQuery(id='123', from_user=user, chat_instance='123', data='menu_admin')
        fake_update = type('FakeUpdate', (), {'effective_user': user, 'callback_query': callback_query})()

        # Тестируем middleware context
        ctx = MiddlewareContext(fake_update, None)
        await ctx.initialize(config)

        assert ctx.user_id == 1278359005, f"Expected user_id 1278359005, got {ctx.user_id}"
        assert ctx.user_role == UserRole.SUPER_ADMIN, f"Expected SUPER_ADMIN role, got {ctx.user_role}"
        assert ctx.command == 'menu_admin', f"Expected command menu_admin, got {ctx.command}"

        print("[OK] Middleware correctly initializes SUPER_ADMIN")
        print(f"  User ID: {ctx.user_id}")
        print(f"  User Role: {ctx.user_role}")
        print(f"  Command: {ctx.command}")

        return True
    except Exception as e:
        print(f"[ERROR] Middleware test error: {e}")
        import traceback
        traceback.print_exc()
        return False
async def test_middleware_super_admin():
    """Тест middleware с SUPER_ADMIN"""
    print("\n=== Test middleware with SUPER_ADMIN ===")

    try:
        config = Config()

        # Создаем фейковый callback update
        user = User(id=1278359005, first_name='Test Super Admin', is_bot=False)
        callback_query = CallbackQuery(id='123', from_user=user, chat_instance='123', data='menu_admin')
        fake_update = type('FakeUpdate', (), {'effective_user': user, 'callback_query': callback_query})()

        # Тестируем middleware context
        ctx = MiddlewareContext(fake_update, None)
        await ctx.initialize(config)

        assert ctx.user_id == 1278359005, f"Expected user_id 1278359005, got {ctx.user_id}"
        assert ctx.user_role == UserRole.SUPER_ADMIN, f"Expected SUPER_ADMIN role, got {ctx.user_role}"
        assert ctx.command == 'menu_admin', f"Expected command menu_admin, got {ctx.command}"

        print("[OK] Middleware correctly initializes SUPER_ADMIN")
        print(f"  User ID: {ctx.user_id}")
        print(f"  User Role: {ctx.user_role}")
        print(f"  Command: {ctx.command}")

        return True
    except Exception as e:
        print(f"[ERROR] Middleware test error: {e}")
        return False


def test_role_hierarchy():
    """Тест иерархии ролей"""
    print("\n=== Тест иерархии ролей ===")

    try:
        # Проверяем что SUPER_ADMIN имеет все разрешения
        super_admin_perms = permission_manager.get_role_permissions(UserRole.SUPER_ADMIN)
        admin_perms = permission_manager.get_role_permissions(UserRole.ADMIN)
        moderator_perms = permission_manager.get_role_permissions(UserRole.MODERATOR)
        user_perms = permission_manager.get_role_permissions(UserRole.USER)

        # SUPER_ADMIN должен иметь все разрешения
        assert len(super_admin_perms) >= len(admin_perms), "SUPER_ADMIN должен иметь как минимум все разрешения ADMIN"
        assert len(super_admin_perms) >= len(moderator_perms), "SUPER_ADMIN должен иметь как минимум все разрешения MODERATOR"
        assert len(super_admin_perms) >= len(user_perms), "SUPER_ADMIN должен иметь как минимум все разрешения USER"

        print("✓ Иерархия ролей корректна")
        print(f"  SUPER_ADMIN разрешений: {len(super_admin_perms)}")
        print(f"  ADMIN разрешений: {len(admin_perms)}")
        print(f"  MODERATOR разрешений: {len(moderator_perms)}")
        print(f"  USER разрешений: {len(user_perms)}")

        return True
    except Exception as e:
        print(f"✗ Ошибка в тесте иерархии ролей: {e}")
        return False


import asyncio

async def main():
    """Основная функция тестирования"""
    print("Running SUPER_ADMIN role tests...")
    print("=" * 50)

    tests = [
        test_super_admin_config,
        test_super_admin_permissions,
        test_middleware_super_admin,  # Теперь async
        test_role_hierarchy
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()

            if result:
                passed += 1
                print(f"[OK] {test.__name__} - PASSED")
            else:
                failed += 1
                print(f"[FAIL] {test.__name__} - FAILED")
        except Exception as e:
            failed += 1
            print(f"[ERROR] {test.__name__} - ERROR: {e}")

    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"[OK] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"Total tests: {passed + failed}")

    if failed > 0:
        print("\n[ERROR] Some tests failed!")
        return 1
    else:
        print("\n[SUCCESS] All tests passed!")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)  # Уменьшаем логирование для тестов
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
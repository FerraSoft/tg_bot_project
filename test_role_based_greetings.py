#!/usr/bin/env python3
"""
Тесты для системы разделения приветствий по ролям пользователей.
Тестирование функциональности ролей, приветствий и интеграции компонентов.
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.role_service import RoleService
from services.user_service import UserService
from database.repository import BaseRepository
from messages import USER_MESSAGES


class TestRoleBasedGreetings:
    """Тесты для системы ролей и приветствий"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.db_repo = BaseRepository(':memory:')  # Используем in-memory базу для тестов
        self.role_service = RoleService(':memory:')

        # Инициализируем роли
        self.role_service.initialize_roles()

    def teardown_method(self):
        """Очистка после каждого теста"""
        if hasattr(self.db_repo, '_connection'):
            self.db_repo.close()

    def test_role_initialization(self):
        """Тест инициализации ролей"""
        roles = self.role_service.get_all_roles()
        assert len(roles) == 3

        role_names = [role.name for role in roles]
        assert 'user' in role_names
        assert 'moderator' in role_names
        assert 'admin' in role_names

    def test_default_user_role(self):
        """Тест роли по умолчанию для новых пользователей"""
        # Создаем тестового пользователя
        user_data = {
            'telegram_id': 123456789,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User'
        }
        self.db_repo._execute_query("""
            INSERT INTO users (telegram_id, username, first_name, last_name, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_data['telegram_id'], user_data['username'],
              user_data['first_name'], user_data['last_name'], 1))

        # Проверяем роль
        role = self.role_service.get_user_role_name(123456789)
        assert role == 'user'

    def test_admin_role_assignment(self):
        """Тест назначения роли администратора"""
        # Создаем пользователя
        user_data = {
            'telegram_id': 987654321,
            'username': 'adminuser',
            'first_name': 'Admin',
            'last_name': 'User'
        }
        self.db_repo._execute_query("""
            INSERT INTO users (telegram_id, username, first_name, last_name, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_data['telegram_id'], user_data['username'],
              user_data['first_name'], user_data['last_name'], 1))

        # Назначаем роль admin
        success = self.role_service.assign_role(987654321, 'admin')
        assert success

        # Проверяем роль
        role = self.role_service.get_user_role_name(987654321)
        assert role == 'admin'

        # Проверяем методы проверки ролей
        assert self.role_service.is_admin(987654321)
        assert self.role_service.is_moderator(987654321)

    def test_moderator_role_assignment(self):
        """Тест назначения роли модератора"""
        # Создаем пользователя
        user_data = {
            'telegram_id': 555666777,
            'username': 'moduser',
            'first_name': 'Mod',
            'last_name': 'User'
        }
        self.db_repo._execute_query("""
            INSERT INTO users (telegram_id, username, first_name, last_name, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_data['telegram_id'], user_data['username'],
              user_data['first_name'], user_data['last_name'], 1))

        # Назначаем роль moderator
        success = self.role_service.assign_role(555666777, 'moderator')
        assert success

        # Проверяем роль
        role = self.role_service.get_user_role_name(555666777)
        assert role == 'moderator'

        # Проверяем методы проверки ролей
        assert not self.role_service.is_admin(555666777)
        assert self.role_service.is_moderator(555666777)

    def test_invalid_role_assignment(self):
        """Тест назначения невалидной роли"""
        # Создаем пользователя
        user_data = {
            'telegram_id': 111222333,
            'username': 'invaliduser',
            'first_name': 'Invalid',
            'last_name': 'User'
        }
        self.db_repo._execute_query("""
            INSERT INTO users (telegram_id, username, first_name, last_name, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_data['telegram_id'], user_data['username'],
              user_data['first_name'], user_data['last_name'], 1))

        # Пытаемся назначить невалидную роль
        success = self.role_service.assign_role(111222333, 'superuser')
        assert not success

        # Проверяем, что роль не изменилась
        role = self.role_service.get_user_role_name(111222333)
        assert role == 'user'

    def test_greeting_messages_exist(self):
        """Тест наличия приветственных сообщений для всех ролей"""
        assert 'greetings_by_role' in USER_MESSAGES
        greetings = USER_MESSAGES['greetings_by_role']

        # Проверяем наличие приветствий для всех ролей
        assert 'user' in greetings
        assert 'moderator' in greetings
        assert 'admin' in greetings

        # Проверяем, что приветствия содержат плейсхолдер {name}
        for role, greeting in greetings.items():
            assert '{name}' in greeting
            assert isinstance(greeting, str)
            assert len(greeting) > 0

    def test_greeting_personalization(self):
        """Тест персонализации приветствий"""
        greetings = USER_MESSAGES['greetings_by_role']

        test_name = "ТестовыйПользователь"

        # Проверяем каждое приветствие
        for role, template in greetings.items():
            personalized = template.format(name=test_name)
            assert test_name in personalized
            assert '{name}' not in personalized

    def test_fallback_greeting(self):
        """Тест fallback приветствия для неизвестной роли"""
        greetings = USER_MESSAGES['greetings_by_role']

        # Для неизвестной роли должно использоваться приветствие user
        unknown_role_greeting = greetings.get('unknown_role', greetings['user'])
        assert unknown_role_greeting == greetings['user']

    def test_role_permissions(self):
        """Тест получения разрешений для ролей"""
        # Проверяем разрешения для каждой роли
        user_permissions = self.role_service.get_role_permissions('user')
        assert user_permissions['can_use_basic_commands'] is True
        assert user_permissions['can_play_games'] is True
        assert user_permissions.get('can_moderate', False) is False

        moderator_permissions = self.role_service.get_role_permissions('moderator')
        assert moderator_permissions['can_use_basic_commands'] is True
        assert moderator_permissions['can_play_games'] is True
        assert moderator_permissions['can_moderate'] is True
        assert moderator_permissions['can_warn_users'] is True

        admin_permissions = self.role_service.get_role_permissions('admin')
        assert admin_permissions['can_use_basic_commands'] is True
        assert admin_permissions['can_play_games'] is True
        assert admin_permissions['can_moderate'] is True
        assert admin_permissions['can_warn_users'] is True
        assert admin_permissions['can_manage_users'] is True
        assert admin_permissions['can_schedule_posts'] is True
        assert admin_permissions['can_export_data'] is True

    def test_nonexistent_user_role(self):
        """Тест получения роли для несуществующего пользователя"""
        role = self.role_service.get_user_role_name(999999999)
        assert role == 'user'  # Должен возвращать роль по умолчанию


class TestIntegrationRoleGreetings:
    """Интеграционные тесты для системы ролей и приветствий"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.db_repo = BaseRepository(':memory:')
        self.role_service = RoleService(':memory:')
        self.user_service = UserService(self.db_repo, Mock(), self.role_service)

        # Инициализируем роли
        self.role_service.initialize_roles()

    def teardown_method(self):
        """Очистка после каждого теста"""
        if hasattr(self.db_repo, '_connection'):
            self.db_repo.close()

    @pytest.mark.asyncio
    async def test_user_creation_with_default_role(self):
        """Тест создания пользователя с ролью по умолчанию"""
        profile = await self.user_service.get_or_create_user(
            user_id=123456789,
            username='testuser',
            first_name='Test',
            last_name='User'
        )

        assert profile is not None
        assert profile.user_id == 123456789

        # Проверяем роль через UserService
        role = self.user_service.get_user_role(123456789)
        assert role == 'user'

        # Проверяем через RoleService
        role_via_service = self.role_service.get_user_role_name(123456789)
        assert role_via_service == 'user'

    @pytest.mark.asyncio
    async def test_role_assignment_integration(self):
        """Тест назначения роли в интеграции"""
        # Создаем пользователя
        profile = await self.user_service.get_or_create_user(
            user_id=987654321,
            username='testadmin',
            first_name='Test',
            last_name='Admin'
        )

        # Назначаем роль admin
        success = self.role_service.assign_role(987654321, 'admin')
        assert success

        # Проверяем через разные сервисы
        role_via_user_service = self.user_service.get_user_role(987654321)
        role_via_role_service = self.role_service.get_user_role_name(987654321)

        assert role_via_user_service == 'admin'
        assert role_via_role_service == 'admin'

        assert self.user_service.is_admin(987654321)
        assert self.user_service.is_moderator(987654321)


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
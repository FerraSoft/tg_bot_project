#!/usr/bin/env python3
"""
Тесты для сервиса приветственных сообщений.
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.welcome_service import WelcomeService
from core.permissions import UserRole


class TestWelcomeService:
    """Тесты WelcomeService"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.welcome_service = WelcomeService()

    def test_initialization(self):
        """Тест инициализации сервиса"""
        assert self.welcome_service is not None
        assert hasattr(self.welcome_service, 'welcome_messages')
        assert isinstance(self.welcome_service.welcome_messages, dict)

    def test_get_welcome_message_user(self):
        """Тест получения приветствия для обычного пользователя"""
        message = self.welcome_service.get_welcome_message(UserRole.USER, "Тест")
        assert "👋 Привет, Тест!" in message
        assert "👋 Добро пожаловать" in message  # Изменено: теперь используем emoji из сервиса
        assert "/rank" in message
        assert "/leaderboard" in message

    def test_get_welcome_message_moderator(self):
        """Тест получения приветствия для модератора"""
        message = self.welcome_service.get_welcome_message(UserRole.MODERATOR, "Модератор")
        assert "👋 Привет, Модератор!" in message
        assert "🛡️ Добро пожаловать, модератор!" in message
        assert "/warn" in message
        assert "/mute" in message
        assert "/unmute" in message

    def test_get_welcome_message_admin(self):
        """Тест получения приветствия для администратора"""
        message = self.welcome_service.get_welcome_message(UserRole.ADMIN, "Админ")
        assert "👋 Привет, Админ!" in message
        assert "👑 Добро пожаловать, администратор!" in message
        assert "/ban" in message
        assert "/kick" in message
        assert "/admin_stats" in message

    def test_get_welcome_message_super_admin(self):
        """Тест получения приветствия для супер-администратора"""
        message = self.welcome_service.get_welcome_message(UserRole.SUPER_ADMIN, "СуперАдмин")
        assert "👋 Привет, СуперАдмин!" in message
        assert "🔧 Супер-администратор активирован!" in message
        # Команды супер-админа в сообщении не перечислены, проверим общее содержание
        assert "/warn" in message
        assert "/admin_stats" in message

    def test_get_welcome_message_without_name(self):
        """Тест получения приветствия без имени пользователя"""
        message = self.welcome_service.get_welcome_message(UserRole.USER)
        assert "👋 Привет!" in message
        assert "👋 Добро пожаловать" in message  # Изменено: используем emoji из сервиса

    def test_invalid_role(self):
        """Тест обработки некорректной роли"""
        with pytest.raises(Exception):  # ValidationError
            self.welcome_service.get_welcome_message("invalid_role")

    def test_get_available_commands_user(self):
        """Тест получения доступных команд для пользователя"""
        commands = self.welcome_service.get_available_commands_for_role(UserRole.USER)

        assert 'user_commands' in commands
        assert 'games' in commands
        assert 'moderation' not in commands
        assert 'admin' not in commands
        assert 'super_admin' not in commands

        # Проверяем базовые команды
        user_commands = commands['user_commands']
        assert len(user_commands) > 0
        assert any('/start' in cmd for cmd in user_commands)
        assert any('/help' in cmd for cmd in user_commands)

    def test_get_available_commands_moderator(self):
        """Тест получения доступных команд для модератора"""
        commands = self.welcome_service.get_available_commands_for_role(UserRole.MODERATOR)

        assert 'user_commands' in commands
        assert 'games' in commands
        assert 'moderation' in commands
        assert 'admin' not in commands

        # Проверяем команды модерации
        moderation_commands = commands['moderation']
        assert len(moderation_commands) > 0
        assert any('/warn' in cmd for cmd in moderation_commands)

    def test_get_available_commands_admin(self):
        """Тест получения доступных команд для администратора"""
        commands = self.welcome_service.get_available_commands_for_role(UserRole.ADMIN)

        assert 'user_commands' in commands
        assert 'games' in commands
        assert 'moderation' in commands
        assert 'admin' in commands
        assert 'super_admin' not in commands

        # Проверяем команды администрирования
        admin_commands = commands['admin']
        assert len(admin_commands) > 0
        assert any('/ban' in cmd for cmd in admin_commands)

    def test_get_available_commands_super_admin(self):
        """Тест получения доступных команд для супер-администратора"""
        commands = self.welcome_service.get_available_commands_for_role(UserRole.SUPER_ADMIN)

        assert 'user_commands' in commands
        assert 'games' in commands
        assert 'moderation' in commands
        assert 'admin' in commands
        assert 'super_admin' in commands

        # Проверяем команды супер-администрирования
        super_admin_commands = commands['super_admin']
        assert len(super_admin_commands) > 0
        assert any('/admin_system' in cmd for cmd in super_admin_commands)

    def test_validate_user_name_valid(self):
        """Тест валидации корректного имени"""
        assert self.welcome_service.validate_user_name("ТестовоеИмя") == True
        assert self.welcome_service.validate_user_name("Test Name") == True
        assert self.welcome_service.validate_user_name("Имя123") == True

    def test_validate_user_name_invalid(self):
        """Тест валидации некорректного имени"""
        assert self.welcome_service.validate_user_name("") == False
        assert self.welcome_service.validate_user_name(None) == False
        assert self.welcome_service.validate_user_name("A" * 101) == False  # Слишком длинное
        assert self.welcome_service.validate_user_name("<script>") == False  # Запрещенные символы

    def test_all_roles_have_messages(self):
        """Тест, что для всех ролей есть приветственные сообщения"""
        for role in UserRole:
            message = self.welcome_service.get_welcome_message(role)
            assert message is not None
            assert len(message.strip()) > 0
            assert "👋 Привет" in message

    def test_messages_contain_role_specific_commands(self):
        """Тест, что приветствия содержат команды, специфичные для роли"""
        # Проверяем, что админское приветствие содержит админские команды
        admin_message = self.welcome_service.get_welcome_message(UserRole.ADMIN)
        assert "/ban" in admin_message or "/admin_stats" in admin_message

        # Проверяем, что пользовательское приветствие не содержит админских команд
        user_message = self.welcome_service.get_welcome_message(UserRole.USER)
        assert "/ban" not in user_message
        assert "/admin_stats" not in user_message


if __name__ == "__main__":
    pytest.main([__file__])
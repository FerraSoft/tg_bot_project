"""
Тесты для системы разрешений и ролей.
Проверяет корректность работы PermissionManager.
"""

import sys
import os
import pytest
from unittest.mock import Mock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.permissions import PermissionManager, UserRole, Permission


class TestPermissionManager:
    """Тесты менеджера разрешений"""

    @pytest.fixture
    def permission_manager(self):
        """Экземпляр менеджера разрешений"""
        return PermissionManager()

    @pytest.fixture
    def mock_config(self):
        """Мок конфигурации"""
        config = Mock()
        config.bot_config = Mock()
        config.bot_config.super_admin_ids = [111111111, 222222222]
        config.bot_config.admin_ids = [333333333, 444444444]
        config.bot_config.moderator_ids = [555555555, 666666666]
        return config

    @pytest.fixture
    def mock_update(self):
        """Мок обновления"""
        update = Mock()
        update.effective_chat = Mock()
        return update

    def test_get_role_permissions_user(self, permission_manager):
        """Тест получения разрешений для роли USER"""
        permissions = permission_manager.get_role_permissions(UserRole.USER)
        expected_permissions = {
            Permission.USE_BASIC_COMMANDS,
            Permission.USE_GAMES,
            Permission.USE_INFO,
            Permission.USE_DONATE,
        }
        assert permissions == expected_permissions

    def test_get_role_permissions_admin(self, permission_manager):
        """Тест получения разрешений для роли ADMIN"""
        permissions = permission_manager.get_role_permissions(UserRole.ADMIN)
        assert Permission.BAN_USERS in permissions
        assert Permission.VIEW_ADMIN_STATS in permissions
        assert len(permissions) > 10  # Должно быть много разрешений

    def test_get_role_permissions_super_admin(self, permission_manager):
        """Тест получения разрешений для роли SUPER_ADMIN"""
        permissions = permission_manager.get_role_permissions(UserRole.SUPER_ADMIN)
        # Супер-администратор должен иметь все разрешения
        assert len(permissions) == len(list(Permission))
        assert Permission.MANAGE_SYSTEM in permissions
        assert Permission.MANAGE_ADMINS in permissions

    def test_has_permission_user(self, permission_manager):
        """Тест проверки наличия разрешения у роли USER"""
        assert permission_manager.has_permission(UserRole.USER, Permission.USE_BASIC_COMMANDS)
        assert permission_manager.has_permission(UserRole.USER, Permission.USE_GAMES)
        assert not permission_manager.has_permission(UserRole.USER, Permission.BAN_USERS)

    def test_has_permission_admin(self, permission_manager):
        """Тест проверки наличия разрешения у роли ADMIN"""
        assert permission_manager.has_permission(UserRole.ADMIN, Permission.BAN_USERS)
        assert permission_manager.has_permission(UserRole.ADMIN, Permission.USE_BASIC_COMMANDS)
        assert not permission_manager.has_permission(UserRole.ADMIN, Permission.MANAGE_SYSTEM)

    def test_has_permission_super_admin(self, permission_manager):
        """Тест проверки наличия разрешения у роли SUPER_ADMIN"""
        # Супер-администратор должен иметь все разрешения
        for permission in Permission:
            assert permission_manager.has_permission(UserRole.SUPER_ADMIN, permission)

    def test_get_user_role_from_config_super_admin(self, permission_manager, mock_config):
        """Тест определения роли супер-администратора из конфигурации"""
        role = permission_manager.get_user_role_from_config(111111111, mock_config)
        assert role == UserRole.SUPER_ADMIN

    def test_get_user_role_from_config_admin(self, permission_manager, mock_config):
        """Тест определения роли администратора из конфигурации"""
        role = permission_manager.get_user_role_from_config(333333333, mock_config)
        assert role == UserRole.ADMIN

    def test_get_user_role_from_config_moderator(self, permission_manager, mock_config):
        """Тест определения роли модератора из конфигурации"""
        role = permission_manager.get_user_role_from_config(555555555, mock_config)
        assert role == UserRole.MODERATOR

    def test_get_user_role_from_config_user(self, permission_manager, mock_config):
        """Тест определения роли обычного пользователя из конфигурации"""
        role = permission_manager.get_user_role_from_config(777777777, mock_config)
        assert role == UserRole.USER

    @pytest.mark.asyncio
    async def test_get_user_role_from_chat_creator(self, permission_manager, mock_update):
        """Тест определения роли создателя чата"""
        # Мокируем создателя чата
        mock_member = Mock()
        mock_member.status = 'creator'
        mock_update.effective_chat.get_member = AsyncMock(return_value=mock_member)

        role = await permission_manager.get_user_role_from_chat(mock_update, 123456789)
        assert role == UserRole.SUPER_ADMIN

    @pytest.mark.asyncio
    async def test_get_user_role_from_chat_administrator(self, permission_manager, mock_update):
        """Тест определения роли администратора чата"""
        # Мокируем администратора чата
        mock_member = Mock()
        mock_member.status = 'administrator'
        mock_update.effective_chat.get_member = AsyncMock(return_value=mock_member)

        role = await permission_manager.get_user_role_from_chat(mock_update, 123456789)
        assert role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_get_user_role_from_chat_user(self, permission_manager, mock_update):
        """Тест определения роли обычного пользователя в чате"""
        # Мокируем обычного пользователя
        mock_member = Mock()
        mock_member.status = 'member'
        mock_update.effective_chat.get_member = AsyncMock(return_value=mock_member)

        role = await permission_manager.get_user_role_from_chat(mock_update, 123456789)
        assert role == UserRole.USER

    @pytest.mark.asyncio
    async def test_get_user_role_from_chat_error(self, permission_manager, mock_update):
        """Тест обработки ошибки при получении роли из чата"""
        # Мокируем ошибку при получении члена
        mock_update.effective_chat.get_member = AsyncMock(side_effect=Exception("API Error"))

        role = await permission_manager.get_user_role_from_chat(mock_update, 123456789)
        assert role == UserRole.USER  # Должна вернуться роль по умолчанию

    @pytest.mark.asyncio
    async def test_get_effective_role_config_priority(self, permission_manager, mock_config, mock_update):
        """Тест получения эффективной роли с приоритетом конфигурации"""
        # Пользователь является супер-администратором в конфигурации
        # и обычным пользователем в чате
        mock_member = Mock()
        mock_member.status = 'member'
        mock_update.effective_chat.get_member = AsyncMock(return_value=mock_member)

        role = await permission_manager.get_effective_role(mock_update, 111111111, mock_config)
        assert role == UserRole.SUPER_ADMIN  # Должна быть выбрана роль из конфигурации

    @pytest.mark.asyncio
    async def test_get_effective_role_chat_priority(self, permission_manager, mock_config, mock_update):
        """Тест получения эффективной роли с приоритетом чата"""
        # Пользователь является администратором в чате
        # и обычным пользователем в конфигурации
        mock_member = Mock()
        mock_member.status = 'administrator'
        mock_update.effective_chat.get_member = AsyncMock(return_value=mock_member)

        role = await permission_manager.get_effective_role(mock_update, 777777777, mock_config)
        assert role == UserRole.ADMIN  # Должна быть выбрана роль из чата

    @pytest.mark.asyncio
    async def test_get_effective_role_both_user(self, permission_manager, mock_config, mock_update):
        """Тест получения эффективной роли когда обе роли - USER"""
        # Пользователь является обычным пользователем везде
        mock_member = Mock()
        mock_member.status = 'member'
        mock_update.effective_chat.get_member = AsyncMock(return_value=mock_member)

        role = await permission_manager.get_effective_role(mock_update, 777777777, mock_config)
        assert role == UserRole.USER

    def test_get_required_permissions_for_command_basic(self, permission_manager):
        """Тест получения необходимых разрешений для базовой команды"""
        permissions = permission_manager.get_required_permissions_for_command('start')
        assert permissions == {Permission.USE_BASIC_COMMANDS}

    def test_get_required_permissions_for_command_game(self, permission_manager):
        """Тест получения необходимых разрешений для игровой команды"""
        permissions = permission_manager.get_required_permissions_for_command('play_game')
        assert permissions == {Permission.USE_GAMES}

    def test_get_required_permissions_for_command_admin(self, permission_manager):
        """Тест получения необходимых разрешений для административной команды"""
        permissions = permission_manager.get_required_permissions_for_command('ban')
        assert permissions == {Permission.BAN_USERS, Permission.VIEW_ADMIN_STATS}

    def test_get_required_permissions_for_command_unknown(self, permission_manager):
        """Тест получения необходимых разрешений для неизвестной команды"""
        permissions = permission_manager.get_required_permissions_for_command('unknown_command')
        assert permissions == {Permission.USE_BASIC_COMMANDS}  # По умолчанию

    def test_can_execute_command_user_allowed(self, permission_manager):
        """Тест проверки возможности выполнения команды для разрешенной роли"""
        can_execute = permission_manager.can_execute_command(UserRole.USER, 'start')
        assert can_execute is True

    def test_can_execute_command_user_denied(self, permission_manager):
        """Тест проверки возможности выполнения команды для запрещенной роли"""
        can_execute = permission_manager.can_execute_command(UserRole.USER, 'ban')
        assert can_execute is False

    def test_can_execute_command_admin_allowed(self, permission_manager):
        """Тест проверки возможности выполнения команды для администратора"""
        can_execute = permission_manager.can_execute_command(UserRole.ADMIN, 'ban')
        assert can_execute is True

    def test_can_execute_command_super_admin_allowed(self, permission_manager):
        """Тест проверки возможности выполнения команды для супер-администратора"""
        can_execute = permission_manager.can_execute_command(UserRole.SUPER_ADMIN, 'ban')
        assert can_execute is True
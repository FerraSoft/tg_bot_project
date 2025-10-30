"""
Тесты для ContextMenuManager.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from core.menu_manager import ContextMenuManager, MenuConfig
from core.permissions import UserRole


class TestContextMenuManager:
    """Тесты менеджера контекстных меню"""

    @pytest.fixture
    def mock_formatter(self):
        """Мок-объект для KeyboardFormatter"""
        formatter = Mock()
        formatter.create_main_menu.return_value = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Помощь", callback_data='menu_help')]
        ])
        formatter.create_games_menu.return_value = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 Игра 1", callback_data='game_1')]
        ])
        formatter.create_admin_menu.return_value = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Пользователи", callback_data='admin_users')]
        ])
        return formatter

    @pytest.fixture
    def mock_permission_manager(self):
        """Мок-объект для PermissionManager"""
        pm = Mock()
        pm.has_permission.return_value = True
        return pm

    @pytest.fixture
    def menu_manager(self, mock_permission_manager, mock_formatter):
        """Фикстура для ContextMenuManager"""
        return ContextMenuManager(mock_permission_manager, mock_formatter)

    def test_initialization(self, menu_manager):
        """Тест инициализации менеджера меню"""
        assert menu_manager.menus is not None
        assert 'menu_main' in menu_manager.menus
        assert 'menu_admin' in menu_manager.menus

        # Проверка разделения по уровням
        assert 'user' in menu_manager.menu_levels
        assert 'admin' in menu_manager.menu_levels
        assert 'super_admin' in menu_manager.menu_levels

    def test_menu_registration(self, menu_manager):
        """Тест регистрации нового меню"""
        async def test_builder(role, **context):
            return InlineKeyboardMarkup([[InlineKeyboardButton("Test", callback_data='test')]])

        menu_manager.register_menu(
            'test_menu', test_builder, UserRole.USER, 'user', 'Тестовое меню'
        )

        assert 'test_menu' in menu_manager.menus
        config = menu_manager.menus['test_menu']
        assert config.required_role == UserRole.USER
        assert config.level == 'user'
        assert config.description == 'Тестовое меню'

    @pytest.mark.asyncio
    async def test_get_menu_for_user_success(self, menu_manager):
        """Тест успешного получения меню для пользователя"""
        menu = await menu_manager.get_menu_for_user('menu_main', UserRole.USER)

        assert menu is not None
        assert isinstance(menu, InlineKeyboardMarkup)
        assert len(menu.inline_keyboard) > 0

    @pytest.mark.asyncio
    async def test_get_menu_for_user_insufficient_permissions(self, menu_manager, mock_permission_manager):
        """Тест получения меню при недостаточных правах"""
        mock_permission_manager.has_permission.return_value = False

        menu = await menu_manager.get_menu_for_user('menu_admin', UserRole.USER)

        assert menu is None

    @pytest.mark.asyncio
    async def test_get_menu_for_user_unknown_menu(self, menu_manager):
        """Тест получения неизвестного меню"""
        menu = await menu_manager.get_menu_for_user('unknown_menu', UserRole.USER)

        assert menu is None

    def test_is_menu_available(self, menu_manager, mock_permission_manager):
        """Тест проверки доступности меню"""
        # Доступно
        mock_permission_manager.has_permission.return_value = True
        assert menu_manager.is_menu_available('menu_main', UserRole.USER)

        # Недоступно
        mock_permission_manager.has_permission.return_value = False
        assert not menu_manager.is_menu_available('menu_admin', UserRole.USER)

    def test_is_menu_available_unknown_menu(self, menu_manager):
        """Тест проверки доступности неизвестного меню"""
        assert not menu_manager.is_menu_available('unknown_menu', UserRole.USER)

    def test_get_available_menus_for_role(self, menu_manager, mock_permission_manager):
        """Тест получения списка доступных меню для роли"""
        mock_permission_manager.has_permission.return_value = True

        menus = menu_manager.get_available_menus_for_role(UserRole.USER)

        assert isinstance(menus, list)
        assert 'menu_main' in menus
        assert 'menu_help' in menus

    def test_get_menus_by_level(self, menu_manager):
        """Тест получения меню по уровням"""
        user_menus = menu_manager.get_menus_by_level('user')
        admin_menus = menu_manager.get_menus_by_level('admin')

        assert isinstance(user_menus, list)
        assert isinstance(admin_menus, list)
        assert 'menu_main' in user_menus
        assert 'menu_admin' in admin_menus

    def test_get_menus_by_unknown_level(self, menu_manager):
        """Тест получения меню для неизвестного уровня"""
        menus = menu_manager.get_menus_by_level('unknown')

        assert menus == []

    def test_clear_cache(self, menu_manager):
        """Тест очистки кеша"""
        # Добавляем что-то в кеш
        menu_manager.menu_cache['test'] = Mock()

        assert len(menu_manager.menu_cache) > 0

        menu_manager.clear_cache()

        assert len(menu_manager.menu_cache) == 0

    def test_menu_config(self):
        """Тест конфигурации меню"""
        async def handler():
            pass

        config = MenuConfig('test', handler, UserRole.ADMIN, 'admin', 'Test menu')

        assert config.menu_id == 'test'
        assert config.required_role == UserRole.ADMIN
        assert config.level == 'admin'
        assert config.description == 'Test menu'
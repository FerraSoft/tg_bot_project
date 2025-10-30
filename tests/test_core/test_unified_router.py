"""
Тесты для UnifiedMessageRouter - интеграция всех компонентов.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from telegram import Update, Message, User, CallbackQuery

from core.unified_router import UnifiedMessageRouter
from core.permissions import UserRole


class TestUnifiedMessageRouter:
    """Тесты объединенного маршрутизатора"""

    @pytest.fixture
    def mock_command_router(self):
        """Мок-объект для CommandRouter"""
        router = Mock()
        router.handle_command = AsyncMock()
        return router

    @pytest.fixture
    def mock_message_router(self):
        """Мок-объект для MessageTypeRouter"""
        router = Mock()
        router.route_text_message = AsyncMock(return_value=True)
        router.route_callback = AsyncMock(return_value=True)
        router.route_voice_message = AsyncMock(return_value=True)
        return router

    @pytest.fixture
    def mock_menu_manager(self):
        """Мок-объект для ContextMenuManager"""
        manager = Mock()
        manager.is_menu_available = Mock(return_value=True)
        manager.get_menu_for_user = AsyncMock(return_value=Mock())
        return manager

    @pytest.fixture
    def unified_router(self, mock_command_router, mock_message_router, mock_menu_manager):
        """Фикстура для UnifiedMessageRouter"""
        return UnifiedMessageRouter(
            mock_command_router,
            mock_message_router,
            mock_menu_manager
        )

    @pytest.fixture
    def mock_update_message(self):
        """Мок-объект для обновления с сообщением"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        user.id = 123456789

        message.text = "/start"
        update.message = message
        update.effective_user = user
        update.callback_query = None

        return update

    @pytest.fixture
    def mock_update_callback(self):
        """Мок-объект для обновления с callback"""
        update = Mock(spec=Update)
        callback_query = Mock(spec=CallbackQuery)
        user = Mock(spec=User)
        user.id = 123456789

        callback_query.data = "menu_main"
        update.callback_query = callback_query
        update.effective_user = user
        update.message = None

        return update

    @pytest.fixture
    def mock_context(self):
        """Мок-объект для контекста"""
        return Mock()

    @pytest.mark.asyncio
    async def test_handle_message_command(self, unified_router, mock_update_message, mock_context, mock_command_router):
        """Тест обработки команд"""
        mock_update_message.message.text = "/start"

        result = await unified_router.handle_update(mock_update_message, mock_context)

        assert result == True
        mock_command_router.handle_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_text(self, unified_router, mock_update_message, mock_context, mock_message_router):
        """Тест обработки текстовых сообщений"""
        mock_update_message.message.text = "Hello world"

        result = await unified_router.handle_update(mock_update_message, mock_context)

        assert result == True
        mock_message_router.route_text_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_menu_allowed(self, unified_router, mock_update_callback, mock_context,
                                               mock_menu_manager, mock_message_router):
        """Тест обработки callback с разрешенным меню"""
        mock_menu_manager.is_menu_available.return_value = True

        result = await unified_router.handle_update(mock_update_callback, mock_context)

        assert result == True
        mock_menu_manager.is_menu_available.assert_called_once_with('menu_main', UserRole.USER)
        mock_message_router.route_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_menu_denied(self, unified_router, mock_update_callback, mock_context,
                                              mock_menu_manager):
        """Тест обработки callback с запрещенным меню"""
        mock_menu_manager.is_menu_available.return_value = False

        result = await unified_router.handle_update(mock_update_callback, mock_context)

        assert result == True
        mock_menu_manager.is_menu_available.assert_called_once()
        # route_callback не должен вызываться
        mock_menu_manager.route_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_menu_for_user(self, unified_router, mock_menu_manager):
        """Тест получения меню для пользователя"""
        mock_menu = Mock()
        mock_menu_manager.get_menu_for_user.return_value = mock_menu

        result = await unified_router.get_menu_for_user('menu_main', UserRole.USER)

        assert result == mock_menu
        mock_menu_manager.get_menu_for_user.assert_called_once_with('menu_main', UserRole.USER)

    def test_get_registered_handlers_count(self, unified_router, mock_command_router, mock_message_router):
        """Тест получения статистики обработчиков"""
        mock_command_router.command_handlers = {'start': Mock(), 'help': Mock()}
        mock_command_router.callback_handlers = {'menu': Mock()}
        mock_message_router.get_registered_handlers_count.return_value = {
            'text': 5,
            'callback': 3,
            'voice': 2
        }

        stats = unified_router.get_registered_handlers_count()

        expected = {
            'command_handlers': 2,
            'callback_handlers': 1,
            'message_handlers': {
                'text': 5,
                'callback': 3,
                'voice': 2
            },
            'total': 2 + 1 + 5 + 3 + 2
        }

        assert stats == expected

    def test_clear_menu_cache(self, unified_router, mock_menu_manager):
        """Тест очистки кеша меню"""
        unified_router.clear_menu_cache()

        mock_menu_manager.clear_cache.assert_called_once()
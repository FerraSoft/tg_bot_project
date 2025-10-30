"""
Тесты для MessageTypeRouter.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from telegram import Update, Message, User, CallbackQuery

from core.message_router import MessageTypeRouter, MessageHandlerConfig
from core.permissions import UserRole


class TestMessageTypeRouter:
    """Тесты маршрутизатора типов сообщений"""

    @pytest.fixture
    def message_router(self):
        """Фикстура для MessageTypeRouter"""
        return MessageTypeRouter()

    @pytest.fixture
    def mock_update_text(self):
        """Мок-объект для текстового сообщения"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        user.id = 123456789

        message.text = "Hello world"
        message.voice = None
        message.photo = None
        update.message = message
        update.effective_user = user

        # Mock chat for permission checking
        chat = Mock()
        member = Mock()
        member.status = 'member'
        chat.get_member = AsyncMock(return_value=member)
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_update_voice(self):
        """Мок-объект для голосового сообщения"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        user.id = 123456789
        voice = Mock()

        message.text = None
        message.voice = voice
        message.photo = None
        update.message = message
        update.effective_user = user

        # Mock chat for permission checking
        chat = Mock()
        member = Mock()
        member.status = 'member'
        chat.get_member = AsyncMock(return_value=member)
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_update_callback(self):
        """Мок-объект для callback запроса"""
        update = Mock(spec=Update)
        callback_query = Mock(spec=CallbackQuery)
        user = Mock(spec=User)
        user.id = 123456789

        callback_query.data = "test_callback"
        update.callback_query = callback_query
        update.effective_user = user

        # Mock chat for permission checking
        chat = Mock()
        member = Mock()
        member.status = 'member'
        chat.get_member = AsyncMock(return_value=member)
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_context(self):
        """Мок-объект для контекста"""
        return Mock()

    def test_initialization(self, message_router):
        """Тест инициализации маршрутизатора"""
        assert message_router.text_handlers == {}
        assert message_router.callback_handlers == {}
        assert message_router.voice_handlers == []
        assert len(message_router.photo_handlers) == 0

    def test_register_text_handler(self, message_router):
        """Тест регистрации обработчика текста"""
        async def handler(update, context):
            pass

        message_router.register_text_handler(
            r'hello', handler, UserRole.USER, 1, 'Test handler'
        )

        assert len(message_router.text_handlers) == 1
        pattern, config = list(message_router.text_handlers.items())[0]
        assert config.required_role == UserRole.USER
        assert config.priority == 1
        assert config.description == 'Test handler'

    def test_register_text_handler_invalid_regex(self, message_router):
        """Тест регистрации обработчика с невалидным regex"""
        async def handler(update, context):
            pass

        # Неверный regex не должен вызывать исключение, но и не регистрироваться
        initial_count = len(message_router.text_handlers)

        message_router.register_text_handler(
            r'[invalid', handler, UserRole.USER
        )

        assert len(message_router.text_handlers) == initial_count

    def test_register_callback_handler(self, message_router):
        """Тест регистрации обработчика callback"""
        async def handler(update, context):
            pass

        message_router.register_callback_handler(
            'test_callback', handler, UserRole.USER, 'Test callback handler'
        )

        assert 'test_callback' in message_router.callback_handlers
        config = message_router.callback_handlers['test_callback']
        assert config.required_role == UserRole.USER
        assert config.description == 'Test callback handler'

    def test_register_media_handler(self, message_router):
        """Тест регистрации обработчика медиа"""
        async def handler(update, context):
            pass

        message_router.register_media_handler(
            'photo', handler, UserRole.USER, 'Photo handler'
        )

        assert len(message_router.photo_handlers) == 1
        config = message_router.photo_handlers[0]
        assert config.required_role == UserRole.USER
        assert config.description == 'Photo handler'

    def test_register_voice_handler(self, message_router):
        """Тест регистрации обработчика голосовых сообщений"""
        async def handler(update, context):
            pass

        message_router.register_media_handler(
            'voice', handler, UserRole.USER, 'Voice handler'
        )

        assert len(message_router.voice_handlers) == 1
        config = message_router.voice_handlers[0]
        assert config.required_role == UserRole.USER

    @pytest.mark.asyncio
    async def test_route_text_message_no_match(self, message_router, mock_update_text, mock_context):
        """Тест маршрутизации текста без совпадений"""
        result = await message_router.route_text_message(mock_update_text, mock_context)

        assert result == False

    @pytest.mark.asyncio
    async def test_route_text_message_with_match(self, message_router, mock_update_text, mock_context):
        """Тест маршрутизации текста с совпадением"""
        handler_called = False

        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True

        message_router.register_text_handler(r'hello', test_handler, UserRole.USER)

        result = await message_router.route_text_message(mock_update_text, mock_context)

        # Проверяем, что обработчик был вызван
        assert handler_called == True
        assert result == True

    @pytest.mark.asyncio
    async def test_route_text_message_insufficient_permissions(self, message_router, mock_update_text, mock_context):
        """Тест маршрутизации текста при недостаточных правах"""
        handler_called = False

        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True

        # Регистрируем обработчик требующий админские права
        message_router.register_text_handler(r'hello', test_handler, UserRole.ADMIN)

        result = await message_router.route_text_message(mock_update_text, mock_context)

        assert result == False
        assert handler_called == False

    @pytest.mark.asyncio
    async def test_route_callback_exact_match(self, message_router, mock_update_callback, mock_context):
        """Тест маршрутизации callback с точным совпадением"""
        handler_called = False

        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True

        message_router.register_callback_handler('test_callback', test_handler, UserRole.USER)

        result = await message_router.route_callback(mock_update_callback, mock_context)

        # Проверяем, что обработчик был вызван
        assert handler_called == True
        assert result == True

    @pytest.mark.asyncio
    async def test_route_callback_prefix_match(self, message_router, mock_update_callback, mock_context):
        """Тест маршрутизации callback по префиксу"""
        handler_called = False

        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True

        message_router.register_callback_handler('test_', test_handler, UserRole.USER)

        result = await message_router.route_callback(mock_update_callback, mock_context)

        # Проверяем, что обработчик был вызван
        assert handler_called == True
        assert result == True

    @pytest.mark.asyncio
    async def test_route_callback_no_match(self, message_router, mock_update_callback, mock_context):
        """Тест маршрутизации callback без совпадений"""
        result = await message_router.route_callback(mock_update_callback, mock_context)

        assert result == False

    @pytest.mark.asyncio
    async def test_route_voice_message(self, message_router, mock_update_voice, mock_context):
        """Тест маршрутизации голосовых сообщений"""
        handler_called = False

        async def test_handler(update, context):
            nonlocal handler_called
            handler_called = True

        message_router.register_media_handler('voice', test_handler, UserRole.USER)

        result = await message_router.route_voice_message(mock_update_voice, mock_context)

        # Проверяем, что обработчик был вызван
        assert handler_called == True
        assert result == True

    def test_get_registered_handlers_count(self, message_router):
        """Тест получения статистики обработчиков"""
        # Регистрируем несколько обработчиков
        async def handler(update, context):
            pass

        message_router.register_text_handler(r'test', handler)
        message_router.register_callback_handler('callback', handler)
        message_router.register_media_handler('photo', handler)

        stats = message_router.get_registered_handlers_count()

        assert stats['text'] == 1
        assert stats['callback'] == 1
        assert stats['photo'] == 1
        assert stats['voice'] == 0

    def test_message_handler_config(self):
        """Тест конфигурации обработчика"""
        async def handler():
            pass

        config = MessageHandlerConfig(handler, UserRole.MODERATOR, 5, 'Test config')

        assert config.handler == handler
        assert config.required_role == UserRole.MODERATOR
        assert config.priority == 5
        assert config.description == 'Test config'
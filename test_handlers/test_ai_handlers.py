"""
Тесты для AI обработчиков команд.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from handlers.ai_handlers import AIHandlers
from services.ai_service import ai_integration


class TestAIHandlers:
    """Тесты для AI обработчиков"""

    @pytest.fixture
    def mock_bot(self):
        """Мокаем бота"""
        bot = AsyncMock()
        return bot

    @pytest.fixture
    def mock_user_service(self):
        """Мокаем сервис пользователей"""
        service = AsyncMock()
        service.get_user_role_enum_async.return_value = MagicMock()  # Имитируем роль USER
        return service

    @pytest.fixture
    def ai_handlers(self, mock_bot, mock_user_service):
        """Фикстура для AI обработчиков"""
        return AIHandlers(mock_bot, mock_user_service)

    @pytest.mark.asyncio
    async def test_handle_gigachat_command_no_args(self, ai_handlers):
        """Тест команды /gigachat без аргументов"""
        message = Mock()
        message.get_args.return_value = ""
        message.reply = AsyncMock()

        await ai_handlers.handle_gigachat_command(message)

        message.reply.assert_called_once()
        call_args = message.reply.call_args[0][0]
        assert "GigaChat" in call_args
        assert "Используйте:" in call_args

    @pytest.mark.asyncio
    async def test_handle_gigachat_command_with_args(self, ai_handlers):
        """Тест команды /gigachat с аргументами"""
        message = Mock()
        message.from_user = Mock()
        message.from_user.id = 123
        message.get_args.return_value = "test query"
        message.chat = Mock()
        message.chat.id = 456
        message.reply = AsyncMock()

        with patch.object(ai_integration, 'generate_response', return_value="Test response") as mock_generate:
            await ai_handlers.handle_gigachat_command(message)

            mock_generate.assert_called_once_with('gigachat', 'test query', 123)
            message.reply.assert_called_once()
            call_args = message.reply.call_args[0][0]
            assert "GigaChat:" in call_args
            assert "Test response" in call_args

    @pytest.mark.asyncio
    async def test_handle_yandexgpt_command_no_args(self, ai_handlers):
        """Тест команды /yandexgpt без аргументов"""
        message = Mock()
        message.get_args.return_value = ""
        message.reply = AsyncMock()

        await ai_handlers.handle_yandexgpt_command(message)

        message.reply.assert_called_once()
        call_args = message.reply.call_args[0][0]
        assert "YandexGPT" in call_args
        assert "Персонализированные рекомендации" in call_args

    @pytest.mark.asyncio
    async def test_handle_yandexgpt_command_with_args(self, ai_handlers):
        """Тест команды /yandexgpt с аргументами"""
        message = Mock()
        message.from_user = Mock()
        message.from_user.id = 123
        message.get_args.return_value = "test query"
        message.chat = Mock()
        message.chat.id = 456
        message.reply = AsyncMock()

        with patch.object(ai_integration, 'generate_response', return_value="Personalized response") as mock_generate:
            await ai_handlers.handle_yandexgpt_command(message)

            mock_generate.assert_called_once_with('yandexgpt', 'test query', 123)
            message.reply.assert_called_once()
            call_args = message.reply.call_args[0][0]
            assert "YandexGPT:" in call_args

    @pytest.mark.asyncio
    async def test_handle_ai_help_command(self, ai_handlers):
        """Тест команды /ai_help"""
        message = Mock()
        message.from_user = Mock()
        message.from_user.id = 123
        message.reply = AsyncMock()

        with patch.object(ai_integration, 'get_available_services', return_value=['gigachat', 'yandexgpt']) as mock_available:
            await ai_handlers.handle_ai_help_command(message)

            mock_available.assert_called_once()
            message.reply.assert_called_once()
            call_args = message.reply.call_args[0][0]
            assert "AI Помощники" in call_args
            assert "/gigachat" in call_args
            assert "/yandexgpt" in call_args

    @pytest.mark.asyncio
    async def test_handle_switch_ai_command_no_args(self, ai_handlers):
        """Тест команды /switch_ai без аргументов"""
        message = Mock()
        message.get_args.return_value = ""
        message.reply = AsyncMock()

        with patch.object(ai_integration, 'get_available_services', return_value=['gigachat', 'yandexgpt']) as mock_available:
            await ai_handlers.handle_switch_ai_command(message)

            mock_available.assert_called_once()
            message.reply.assert_called_once()
            call_args = message.reply.call_args[0][0]
            assert "Переключение AI сервиса" in call_args

    @pytest.mark.asyncio
    async def test_handle_switch_ai_command_with_valid_service(self, ai_handlers):
        """Тест команды /switch_ai с валидным сервисом"""
        message = Mock()
        message.from_user = Mock()
        message.from_user.id = 123
        message.get_args.return_value = "yandexgpt"
        message.date = 1234567890
        message.reply = AsyncMock()

        with patch.object(ai_integration, 'switch_service', return_value=True) as mock_switch:
            await ai_handlers.handle_switch_ai_command(message)

            mock_switch.assert_called_once_with(123, 'yandexgpt')
            message.reply.assert_called_once()
            call_args = message.reply.call_args[0][0]
            assert "AI сервис переключен" in call_args
            assert "yandexgpt" in call_args

    @pytest.mark.asyncio
    async def test_handle_switch_ai_command_with_invalid_service(self, ai_handlers):
        """Тест команды /switch_ai с невалидным сервисом"""
        message = Mock()
        message.from_user = Mock()
        message.from_user.id = 123
        message.get_args.return_value = "invalid_service"
        message.reply = AsyncMock()

        with patch.object(ai_integration, 'switch_service', return_value=False) as mock_switch:
            await ai_handlers.handle_switch_ai_command(message)

            mock_switch.assert_called_once_with(123, 'invalid_service')
            message.reply.assert_called_once()
            call_args = message.reply.call_args[0][0]
            assert "не найден или недоступен" in call_args

    @pytest.mark.asyncio
    async def test_handle_max_sync_command(self, ai_handlers):
        """Тест команды /max_sync"""
        message = Mock()
        message.from_user = Mock()
        message.from_user.id = 123
        message.reply = AsyncMock()

        await ai_handlers.handle_max_sync_command(message)

        message.reply.assert_called_once()
        call_args = message.reply.call_args[0][0]
        assert "MAX Интеграция" in call_args
        assert "находится в разработке" in call_args

    @pytest.mark.asyncio
    async def test_handle_ai_message_not_in_ai_mode(self, ai_handlers):
        """Тест обработки AI сообщения когда пользователь не в режиме AI"""
        message = Mock()
        message.from_user = Mock()
        message.from_user.id = 123
        message.text = "test message"
        message.reply = AsyncMock()

        # Пользователь не в ai_states
        await ai_handlers.handle_ai_message(message)

        # Сообщение не должно быть обработано
        message.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_ai_message_in_ai_mode(self, ai_handlers):
        """Тест обработки AI сообщения когда пользователь в режиме AI"""
        message = Mock()
        message.from_user = Mock()
        message.from_user.id = 123
        message.text = "test message"
        message.chat = Mock()
        message.chat.id = 456
        message.reply = AsyncMock()

        # Устанавливаем пользователя в режим AI
        ai_handlers.ai_states[123] = {'service': 'gigachat'}

        with patch.object(ai_integration, 'generate_response', return_value="AI response") as mock_generate:
            await ai_handlers.handle_ai_message(message)

            mock_generate.assert_called_once_with('gigachat', 'test message', 123)
            message.reply.assert_called_once()
            call_args = message.reply.call_args[0][0]
            assert "🤖" in call_args
            assert "AI response" in call_args

    @pytest.mark.asyncio
    async def test_check_ai_access_success(self, ai_handlers, mock_user_service):
        """Тест успешной проверки доступа к AI"""
        from core.permissions import UserRole

        mock_user_service.get_user_role_enum_async.return_value = UserRole.USER

        result = await ai_handlers._check_ai_access(123)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_ai_access_failure(self, ai_handlers, mock_user_service):
        """Тест неудачной проверки доступа к AI"""
        mock_user_service.get_user_role_enum_async.side_effect = Exception("Test error")

        result = await ai_handlers._check_ai_access(123)
        assert result is False

    def test_get_command_handlers(self, ai_handlers):
        """Тест получения словаря команд"""
        handlers = ai_handlers.get_command_handlers()

        assert isinstance(handlers, dict)
        assert 'gigachat' in handlers
        assert 'yandexgpt' in handlers
        assert 'ai_help' in handlers
        assert 'switch_ai' in handlers
        assert 'max_sync' in handlers

    def test_get_message_handlers(self, ai_handlers):
        """Тест получения обработчиков сообщений"""
        handlers = ai_handlers.get_message_handlers()

        assert isinstance(handlers, list)
        assert len(handlers) == 1
        assert handlers[0] == ai_handlers.handle_ai_message


if __name__ == "__main__":
    pytest.main([__file__])
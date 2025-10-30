"""
Интеграционные тесты для MessageTypeRouter с триггерами.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User, CallbackQuery

from core.message_router import MessageTypeRouter, create_message_router
from services.trigger_service import TriggerService


class TestMessageRouterTriggers:
    """Интеграционные тесты маршрутизатора сообщений с триггерами"""

    @pytest.fixture
    def mock_trigger_service(self):
        """Мок сервиса триггеров"""
        service = Mock(spec=TriggerService)
        service.check_triggers = AsyncMock(return_value=[])
        service.execute_trigger_actions = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def message_router_with_triggers(self, mock_trigger_service):
        """Фикстура маршрутизатора с сервисом триггеров"""
        return create_message_router(mock_trigger_service)

    @pytest.fixture
    def mock_update_group_text(self):
        """Мок-объект для текстового сообщения в группе"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock()

        user.id = 123456
        message.text = "hello world"
        message.voice = None
        message.photo = None
        message.message_id = 789
        message.chat_id = 987654
        chat.type = "group"

        update.message = message
        update.effective_user = user
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_update_private_text(self):
        """Мок-объект для текстового сообщения в привате"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock()

        user.id = 123456
        message.text = "private message"
        message.voice = None
        message.photo = None
        chat.type = "private"

        update.message = message
        update.effective_user = user
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_context(self):
        """Мок-объект для контекста"""
        context = Mock()
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        context.bot.send_sticker = AsyncMock()
        context.bot.send_animation = AsyncMock()
        context.bot.set_message_reaction = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_route_text_message_no_triggers_group(self, message_router_with_triggers,
                                                       mock_update_group_text, mock_context):
        """Тест маршрутизации текста в группе без сработавших триггеров"""
        result = await message_router_with_triggers.route_text_message(
            mock_update_group_text, mock_context
        )

        # Проверяем, что проверка триггеров была вызвана для группы
        message_router_with_triggers.trigger_service.check_triggers.assert_called_once_with(
            "hello world", "group"
        )

        # Проверяем, что выполнение действий не было вызвано
        message_router_with_triggers.trigger_service.execute_trigger_actions.assert_not_called()

        assert result == False  # Нет совпадений с текстовыми обработчиками

    @pytest.mark.asyncio
    async def test_route_text_message_no_triggers_private(self, message_router_with_triggers,
                                                         mock_update_private_text, mock_context):
        """Тест маршрутизации текста в привате без сработавших триггеров"""
        result = await message_router_with_triggers.route_text_message(
            mock_update_private_text, mock_context
        )

        # Проверяем, что проверка триггеров НЕ была вызвана для приватного чата
        message_router_with_triggers.trigger_service.check_triggers.assert_not_called()

        # Проверяем, что выполнение действий не было вызвано
        message_router_with_triggers.trigger_service.execute_trigger_actions.assert_not_called()

        assert result == False

    @pytest.mark.asyncio
    async def test_route_text_message_with_trigger_match_group(self, message_router_with_triggers,
                                                              mock_update_group_text, mock_context):
        """Тест маршрутизации текста в группе с сработавшим триггером"""
        # Настраиваем мок триггера
        matched_triggers = [
            {
                'id': 1,
                'name': 'hello_trigger',
                'response_text': 'Hi there!',
                'trigger_count': 5
            }
        ]

        message_router_with_triggers.trigger_service.check_triggers.return_value = matched_triggers
        message_router_with_triggers.trigger_service.execute_trigger_actions.return_value = [
            {
                'type': 'text',
                'content': 'Hi there!',
                'trigger_id': 1,
                'trigger_name': 'hello_trigger'
            }
        ]

        result = await message_router_with_triggers.route_text_message(
            mock_update_group_text, mock_context
        )

        # Проверяем, что проверка триггеров была вызвана
        message_router_with_triggers.trigger_service.check_triggers.assert_called_once_with(
            "hello world", "group"
        )

        # Проверяем, что выполнение действий было вызвано
        message_router_with_triggers.trigger_service.execute_trigger_actions.assert_called_once_with(
            matched_triggers, 987654, "hello world", 789
        )

        assert result == False  # Нет совпадений с текстовыми обработчиками маршрутизатора

    @pytest.mark.asyncio
    async def test_trigger_actions_execution_text(self, message_router_with_triggers,
                                                 mock_update_group_text, mock_context):
        """Тест выполнения действий триггера - текстовый ответ"""
        actions = [
            {
                'type': 'text',
                'content': 'Hello from trigger!',
                'trigger_id': 1,
                'trigger_name': 'test_trigger'
            }
        ]

        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что сообщение было отправлено
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=987654,
            text='Hello from trigger!',
            reply_to_message_id=789
        )

    @pytest.mark.asyncio
    async def test_trigger_actions_execution_sticker(self, message_router_with_triggers,
                                                    mock_update_group_text, mock_context):
        """Тест выполнения действий триггера - стикер"""
        actions = [
            {
                'type': 'sticker',
                'content': 'sticker_file_id',
                'trigger_id': 1,
                'trigger_name': 'sticker_trigger'
            }
        ]

        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что стикер был отправлен
        mock_context.bot.send_sticker.assert_called_once_with(
            chat_id=987654,
            sticker='sticker_file_id',
            reply_to_message_id=789
        )

    @pytest.mark.asyncio
    async def test_trigger_actions_execution_gif(self, message_router_with_triggers,
                                                mock_update_group_text, mock_context):
        """Тест выполнения действий триггера - GIF"""
        actions = [
            {
                'type': 'gif',
                'content': 'gif_file_id',
                'trigger_id': 1,
                'trigger_name': 'gif_trigger'
            }
        ]

        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что GIF был отправлен
        mock_context.bot.send_animation.assert_called_once_with(
            chat_id=987654,
            animation='gif_file_id',
            reply_to_message_id=789
        )

    @pytest.mark.asyncio
    async def test_trigger_actions_execution_reaction(self, message_router_with_triggers,
                                                     mock_update_group_text, mock_context):
        """Тест выполнения действий триггера - реакция"""
        actions = [
            {
                'type': 'reaction',
                'reaction_type': 'emoji',
                'content': '👍',
                'message_id': 789,
                'trigger_id': 1,
                'trigger_name': 'reaction_trigger'
            }
        ]

        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что реакция была установлена
        mock_context.bot.set_message_reaction.assert_called_once_with(
            chat_id=987654,
            message_id=789,
            reaction='👍'
        )

    @pytest.mark.asyncio
    async def test_trigger_actions_execution_multiple_actions(self, message_router_with_triggers,
                                                            mock_update_group_text, mock_context):
        """Тест выполнения множественных действий триггера"""
        actions = [
            {
                'type': 'text',
                'content': 'Hello!',
                'trigger_id': 1,
                'trigger_name': 'multi_trigger'
            },
            {
                'type': 'sticker',
                'content': 'sticker123',
                'trigger_id': 1,
                'trigger_name': 'multi_trigger'
            },
            {
                'type': 'reaction',
                'reaction_type': 'emoji',
                'content': '❤️',
                'message_id': 789,
                'trigger_id': 1,
                'trigger_name': 'multi_trigger'
            }
        ]

        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что все действия были выполнены
        assert mock_context.bot.send_message.call_count == 1
        assert mock_context.bot.send_sticker.call_count == 1
        assert mock_context.bot.set_message_reaction.call_count == 1

    @pytest.mark.asyncio
    async def test_trigger_actions_execution_reaction_priority(self, message_router_with_triggers,
                                                              mock_update_group_text, mock_context):
        """Тест приоритета реакций - только первая реакция выполняется"""
        actions = [
            {
                'type': 'reaction',
                'reaction_type': 'emoji',
                'content': '👍',
                'message_id': 789,
                'trigger_id': 1,
                'trigger_name': 'first_reaction'
            },
            {
                'type': 'reaction',
                'reaction_type': 'emoji',
                'content': '❤️',
                'message_id': 789,
                'trigger_id': 2,
                'trigger_name': 'second_reaction'
            },
            {
                'type': 'text',
                'content': 'Text response',
                'trigger_id': 1,
                'trigger_name': 'text_trigger'
            }
        ]

        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что только первая реакция была установлена
        mock_context.bot.set_message_reaction.assert_called_once_with(
            chat_id=987654,
            message_id=789,
            reaction='👍'
        )

        # Проверяем, что текстовый ответ был отправлен
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=987654,
            text='Text response',
            reply_to_message_id=789
        )

    @pytest.mark.asyncio
    async def test_trigger_actions_execution_empty_actions(self, message_router_with_triggers,
                                                          mock_update_group_text, mock_context):
        """Тест выполнения пустого списка действий"""
        actions = []

        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что ничего не было отправлено
        mock_context.bot.send_message.assert_not_called()
        mock_context.bot.send_sticker.assert_not_called()
        mock_context.bot.send_animation.assert_not_called()
        mock_context.bot.set_message_reaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_actions_execution_unknown_action_type(self, message_router_with_triggers,
                                                                mock_update_group_text, mock_context):
        """Тест выполнения действия с неизвестным типом"""
        actions = [
            {
                'type': 'unknown',
                'content': 'some_content',
                'trigger_id': 1,
                'trigger_name': 'unknown_trigger'
            }
        ]

        # Не должно выбрасывать исключение, просто игнорирует неизвестный тип
        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что ничего не было отправлено
        mock_context.bot.send_message.assert_not_called()
        mock_context.bot.send_sticker.assert_not_called()
        mock_context.bot.send_animation.assert_not_called()
        mock_context.bot.set_message_reaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_text_message_trigger_service_error(self, message_router_with_triggers,
                                                           mock_update_group_text, mock_context):
        """Тест обработки ошибки в сервисе триггеров"""
        message_router_with_triggers.trigger_service.check_triggers.side_effect = Exception("Test error")

        # Не должно выбрасывать исключение
        result = await message_router_with_triggers.route_text_message(
            mock_update_group_text, mock_context
        )

        assert result == False

    @pytest.mark.asyncio
    async def test_execute_trigger_actions_error_handling(self, message_router_with_triggers,
                                                         mock_update_group_text, mock_context):
        """Тест обработки ошибок при выполнении действий триггера"""
        actions = [
            {
                'type': 'text',
                'content': 'Hello!',
                'trigger_id': 1,
                'trigger_name': 'error_trigger'
            }
        ]

        # Настраиваем ошибку при отправке сообщения
        mock_context.bot.send_message.side_effect = Exception("Send error")

        # Не должно выбрасывать исключение наружу
        await message_router_with_triggers._execute_trigger_actions(actions, mock_update_group_text, mock_context)

        # Проверяем, что попытка отправки была
        mock_context.bot.send_message.assert_called_once()

    def test_set_trigger_service(self, message_router_with_triggers, mock_trigger_service):
        """Тест установки сервиса триггеров"""
        new_trigger_service = Mock(spec=TriggerService)
        message_router_with_triggers.set_trigger_service(new_trigger_service)

        assert message_router_with_triggers.trigger_service == new_trigger_service

    def test_create_message_router_with_trigger_service(self, mock_trigger_service):
        """Тест создания маршрутизатора с сервисом триггеров"""
        router = create_message_router(mock_trigger_service)

        assert isinstance(router, MessageTypeRouter)
        assert router.trigger_service == mock_trigger_service

    def test_create_message_router_without_trigger_service(self):
        """Тест создания маршрутизатора без сервиса триггеров"""
        router = create_message_router()

        assert isinstance(router, MessageTypeRouter)
        assert router.trigger_service is None
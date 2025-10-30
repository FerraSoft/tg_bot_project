"""
Тесты для административных обработчиков триггеров.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User, CallbackQuery

from handlers.admin_handlers import AdminHandlers


class TestAdminTriggers:
    """Тесты административных обработчиков триггеров"""

    @pytest.fixture
    def mock_trigger_service(self):
        """Мок сервиса триггеров"""
        service = Mock()
        service.add_trigger = AsyncMock(return_value=1)
        service.update_trigger = AsyncMock(return_value=True)
        service.delete_trigger = AsyncMock(return_value=True)
        service.toggle_trigger = AsyncMock(return_value=True)
        service.get_all_triggers = AsyncMock(return_value=[])
        service.get_trigger_by_id = AsyncMock(return_value=None)
        return service

    @pytest.fixture
    def admin_handlers(self, mock_trigger_service):
        """Фикстура административных обработчиков"""
        with patch('handlers.admin_handlers.TriggerService', return_value=mock_trigger_service):
            handlers = AdminHandlers(
                database_url=':memory:',
                trigger_service=mock_trigger_service
            )
            return handlers

    @pytest.fixture
    def mock_update(self):
        """Мок-объект для Update"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock()

        user.id = 123456
        message.message_id = 789
        chat.id = 987654

        update.message = message
        update.effective_user = user
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_context(self):
        """Мок-объект для контекста"""
        context = Mock()
        context.args = []
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_handle_trigger_add_success(self, admin_handlers, mock_update, mock_context):
        """Тест успешного добавления триггера"""
        mock_update.message.text = "/trigger_add hello Привет!"
        mock_context.args = ["hello", "Привет!"]

        admin_handlers.send_response = AsyncMock()

        await admin_handlers._handle_trigger_add(mock_update, mock_context)

        # Проверяем, что сервис был вызван
        admin_handlers.trigger_service.add_trigger.assert_called_once()
        call_args = admin_handlers.trigger_service.add_trigger.call_args[0][0]

        assert call_args['name'] == 'hello'
        assert call_args['pattern'] == 'hello'
        assert call_args['response_text'] == 'Привет!'
        assert call_args['chat_type'] == 'group'

        # Проверяем, что ответ был отправлен
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "успешно добавлен" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_add_invalid_args(self, admin_handlers, mock_update, mock_context):
        """Тест добавления триггера с некорректными аргументами"""
        mock_update.message.text = "/trigger_add"
        mock_context.args = []

        admin_handlers.send_response = AsyncMock()

        await admin_handlers._handle_trigger_add(mock_update, mock_context)

        # Проверяем, что сервис не был вызван
        admin_handlers.trigger_service.add_trigger.assert_not_called()

        # Проверяем, что отправлено сообщение об ошибке
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "Использование:" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_add_validation_error(self, admin_handlers, mock_update, mock_context):
        """Тест добавления триггера с ошибкой валидации"""
        mock_update.message.text = "/trigger_add test Тест"
        mock_context.args = ["test", "Тест"]

        admin_handlers.send_response = AsyncMock()
        admin_handlers.trigger_service.add_trigger.side_effect = Exception("Validation error")

        await admin_handlers._handle_trigger_add(mock_update, mock_context)

        # Проверяем, что был вызван сервис
        admin_handlers.trigger_service.add_trigger.assert_called_once()

        # Проверяем, что отправлено сообщение об ошибке
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "Ошибка" in response_call[1] or "Не удалось" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_list_empty(self, admin_handlers, mock_update, mock_context):
        """Тест списка триггеров при их отсутствии"""
        admin_handlers.send_response = AsyncMock()

        await admin_handlers._handle_trigger_list(mock_update, mock_context)

        # Проверяем, что отправлено сообщение о пустом списке
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "Нет созданных триггеров" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_list_with_triggers(self, admin_handlers, mock_update, mock_context):
        """Тест списка триггеров с данными"""
        triggers = [
            {
                'id': 1,
                'keywords': ['hello', 'hi'],
                'response': 'Привет!',
                'enabled': True
            },
            {
                'id': 2,
                'keywords': ['bye'],
                'response': 'Пока!',
                'enabled': False
            }
        ]

        admin_handlers.trigger_service.get_all_triggers.return_value = triggers

        with patch('telegram.InlineKeyboardMarkup') as mock_markup, \
             patch('telegram.InlineKeyboardButton') as mock_button:

            admin_handlers.send_response = AsyncMock()

            await admin_handlers._handle_trigger_list(mock_update, mock_context)

            # Проверяем, что ответ был отправлен
            admin_handlers.send_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_trigger_edit_valid_id(self, admin_handlers, mock_update, mock_context):
        """Тест редактирования триггера с валидным ID"""
        mock_context.args = ["1"]

        trigger_data = {
            'id': 1,
            'keywords': ['hello'],
            'response': 'Привет!'
        }

        admin_handlers.trigger_service.get_trigger_by_id.return_value = trigger_data
        admin_handlers.send_response = AsyncMock()

        await admin_handlers._handle_trigger_edit(mock_update, mock_context)

        # Проверяем, что триггер был найден
        admin_handlers.trigger_service.get_trigger_by_id.assert_called_once_with(1)

        # Проверяем, что ID сохранен в user_data
        assert mock_context.user_data['editing_trigger_id'] == 1

        # Проверяем, что отправлена форма редактирования
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "Редактирование триггера" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_edit_invalid_id(self, admin_handlers, mock_update, mock_context):
        """Тест редактирования триггера с невалидным ID"""
        mock_context.args = ["abc"]

        admin_handlers.send_response = AsyncMock()

        await admin_handlers._handle_trigger_edit(mock_update, mock_context)

        # Проверяем, что отправлено сообщение об ошибке
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "Необходимо указать корректный ID" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_edit_not_found(self, admin_handlers, mock_update, mock_context):
        """Тест редактирования несуществующего триггера"""
        mock_context.args = ["999"]

        admin_handlers.trigger_service.get_trigger_by_id.return_value = None
        admin_handlers.send_response = AsyncMock()

        await admin_handlers._handle_trigger_edit(mock_update, mock_context)

        # Проверяем, что отправлено сообщение о ненайденном триггере
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "не найден" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_delete_valid_id(self, admin_handlers, mock_update, mock_context):
        """Тест удаления триггера с валидным ID"""
        mock_context.args = ["1"]

        trigger_data = {
            'id': 1,
            'keywords': ['hello'],
            'response': 'Привет!'
        }

        admin_handlers.trigger_service.get_trigger_by_id.return_value = trigger_data

        with patch('telegram.InlineKeyboardMarkup') as mock_markup, \
             patch('telegram.InlineKeyboardButton') as mock_button:

            admin_handlers.send_response = AsyncMock()

            await admin_handlers._handle_trigger_delete(mock_update, mock_context)

            # Проверяем, что отправлена клавиатура подтверждения
            admin_handlers.send_response.assert_called_once()
            response_call = admin_handlers.send_response.call_args[0]
            assert "Подтверждение удаления" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_toggle_success(self, admin_handlers, mock_update, mock_context):
        """Тест успешного переключения статуса триггера"""
        mock_context.args = ["1"]

        admin_handlers.send_response = AsyncMock()

        await admin_handlers._handle_trigger_toggle(mock_update, mock_context)

        # Проверяем, что сервис был вызван
        admin_handlers.trigger_service.toggle_trigger.assert_called_once_with(1, True)

        # Проверяем, что отправлен ответ
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "успешно" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_toggle_not_found(self, admin_handlers, mock_update, mock_context):
        """Тест переключения статуса несуществующего триггера"""
        mock_context.args = ["999"]

        admin_handlers.trigger_service.toggle_trigger.return_value = False
        admin_handlers.send_response = AsyncMock()

        await admin_handlers._handle_trigger_toggle(mock_update, mock_context)

        # Проверяем, что отправлено сообщение об ошибке
        admin_handlers.send_response.assert_called_once()
        response_call = admin_handlers.send_response.call_args[0]
        assert "не найден" in response_call[1]

    @pytest.mark.asyncio
    async def test_handle_trigger_toggle_callback_success(self, admin_handlers):
        """Тест callback переключения статуса триггера"""
        update = Mock(spec=Update)
        callback_query = Mock(spec=CallbackQuery)
        user = Mock(spec=User)

        callback_query.data = 'trigger_toggle_1'
        user.id = 123456
        callback_query.from_user = user

        update.callback_query = callback_query

        context = Mock()

        with patch('telegram.InlineKeyboardMarkup') as mock_markup, \
             patch('telegram.InlineKeyboardButton') as mock_button:

            callback_query.edit_message_text = AsyncMock()

            await admin_handlers.handle_trigger_toggle_callback(update, context)

            # Проверяем, что сервис был вызван для активации
            admin_handlers.trigger_service.toggle_trigger.assert_called_once_with(1, True)

            # Проверяем, что сообщение было обновлено
            callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_trigger_toggle_callback_deactivate(self, admin_handlers):
        """Тест callback переключения статуса триггера (деактивация)"""
        update = Mock(spec=Update)
        callback_query = Mock(spec=CallbackQuery)
        user = Mock(spec=User)

        callback_query.data = 'trigger_toggle_2'
        user.id = 123456
        callback_query.from_user = user

        update.callback_query = callback_query

        context = Mock()

        with patch('telegram.InlineKeyboardMarkup') as mock_markup, \
             patch('telegram.InlineKeyboardButton') as mock_button:

            callback_query.edit_message_text = AsyncMock()

            await admin_handlers.handle_trigger_toggle_callback(update, context)

            # Проверяем, что сервис был вызван для деактивации
            admin_handlers.trigger_service.toggle_trigger.assert_called_once_with(2, False)

            # Проверяем, что сообщение было обновлено
            callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_trigger_toggle_callback_invalid_data(self, admin_handlers):
        """Тест callback с некорректными данными"""
        update = Mock(spec=Update)
        callback_query = Mock(spec=CallbackQuery)

        callback_query.data = 'trigger_toggle_invalid'

        update.callback_query = callback_query

        context = Mock()

        # Не должно делать ничего (нет исключений)
        await admin_handlers.handle_trigger_toggle_callback(update, context)

        # Сервис не должен вызываться
        admin_handlers.trigger_service.toggle_trigger.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_trigger_delete_callback_confirm(self, admin_handlers):
        """Тест callback подтверждения удаления триггера"""
        update = Mock(spec=Update)
        callback_query = Mock(spec=CallbackQuery)
        user = Mock(spec=User)

        callback_query.data = 'trigger_confirm_delete_1'
        user.id = 123456
        callback_query.from_user = user

        update.callback_query = callback_query

        context = Mock()

        with patch('telegram.InlineKeyboardMarkup') as mock_markup, \
             patch('telegram.InlineKeyboardButton') as mock_button:

            callback_query.edit_message_text = AsyncMock()

            await admin_handlers.handle_trigger_delete_callback(update, context)

            # Проверяем, что сервис был вызван для удаления
            admin_handlers.trigger_service.delete_trigger.assert_called_once_with(1)

            # Проверяем, что сообщение было обновлено
            callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_trigger_delete_callback_cancel(self, admin_handlers):
        """Тест callback отмены удаления триггера"""
        update = Mock(spec=Update)
        callback_query = Mock(spec=CallbackQuery)

        callback_query.data = 'trigger_cancel_delete'

        update.callback_query = callback_query

        context = Mock()

        with patch('telegram.InlineKeyboardMarkup') as mock_markup, \
             patch('telegram.InlineKeyboardButton') as mock_button:

            callback_query.edit_message_text = AsyncMock()

            await admin_handlers.handle_trigger_delete_callback(update, context)

            # Проверяем, что сервис не был вызван для удаления
            admin_handlers.trigger_service.delete_trigger.assert_not_called()

            # Проверяем, что сообщение было обновлено
            callback_query.edit_message_text.assert_called_once()

    def test_safe_execute_trigger_handlers(self, admin_handlers, mock_update, mock_context):
        """Тест защищенного выполнения обработчиков триггеров"""
        async def test_handler(update, context):
            return "success"

        # Тестируем через публичный метод handle_trigger_add
        admin_handlers._AdminHandlers__safe_execute = Mock()
        admin_handlers.handle_trigger_add = Mock()

        # Проверяем, что safe_execute вызывается
        admin_handlers.handle_trigger_add(mock_update, mock_context)

        # Проверяем, что safe_execute был вызван
        assert admin_handlers._AdminHandlers__safe_execute.called
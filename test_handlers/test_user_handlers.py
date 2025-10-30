"""
Тесты для обработчиков пользовательских команд.
Проверяет корректность обработки команд пользователями.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
from handlers.user_handlers import UserHandlers
from services.user_service import UserService, UserProfile
from core.exceptions import ValidationError, PermissionError


class TestUserHandlers:
    """Тесты обработчиков пользовательских команд"""

    @pytest.fixture
    def mock_user_service(self):
        """Мок сервиса пользователей"""
        service = Mock(spec=UserService)
        service.get_or_create_user = AsyncMock()
        service.update_user_activity = AsyncMock()
        service.get_top_users = AsyncMock()
        service.get_rank_progress = Mock()
        from core.permissions import UserRole
        service.get_user_role_enum = Mock()
        service.get_user_role_enum.return_value = UserRole.USER

        # Настройка возвращаемых значений по умолчанию
        service.get_top_users.return_value = []
        service.get_rank_progress.return_value = {
            'current_rank': 'Ученик',
            'next_rank': 'Активист',
            'percentage': 75.0,
            'progress': 75,
            'needed': 100
        }

        return service

    @pytest.fixture
    def user_handlers(self, test_config, mock_user_service):
        """Экземпляр обработчика пользовательских команд"""
        from unittest.mock import Mock
        mock_metrics = Mock()
        return UserHandlers(test_config, mock_metrics, mock_user_service)

    @pytest.fixture
    def mock_update(self, mock_user, mock_chat, mock_message):
        """Мок объекта обновления"""
        update = Mock(spec=Update)
        update.effective_user = mock_user
        update.effective_chat = mock_chat
        update.message = mock_message
        return update

    @pytest.fixture
    def mock_context(self):
        """Мок контекста"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = []
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_handle_start_success(self, user_handlers, mock_update, mock_context, mock_user_service):
        """Тест успешной обработки команды /start"""
        # Мокируем профиль пользователя
        profile = UserProfile(
            user_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            reputation=100,
            rank="Активист"
        )
        mock_user_service.get_or_create_user.return_value = profile

        # Мокируем ответ бота
        mock_update.message.reply_text = AsyncMock()

        # Выполняем обработку команды
        await user_handlers.handle_start(mock_update, mock_context)

        # Проверяем, что пользователь был создан/получен
        mock_user_service.get_or_create_user.assert_called_once_with(
            123456789, "test_user", "Test", "User"
        )

        # Проверяем, что ответ был отправлен
        mock_update.message.reply_text.assert_called_once()
        reply_text = mock_update.message.reply_text.call_args[0][0]

        # Проверяем содержание ответа
        assert "Привет, Test!" in reply_text
        assert "Добро пожаловать в наш бот!" in reply_text

    @pytest.mark.asyncio
    async def test_handle_rank_success(self, user_handlers, mock_update, mock_context, mock_user_service):
        """Тест успешной обработки команды /rank"""
        # Мокируем профиль пользователя
        profile = UserProfile(
            user_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            reputation=150,
            rank="Активист",
            message_count=45,
            warnings=2
        )
        mock_user_service.get_or_create_user.return_value = profile

        # Мокируем прогресс ранга
        rank_progress = {
            'current_rank': 'Активист',
            'next_rank': 'Знаток',
            'percentage': 75.0
        }
        mock_user_service.get_rank_progress.return_value = rank_progress

        # Мокируем ответ бота
        mock_update.message.reply_text = AsyncMock()

        # Выполняем обработку команды
        await user_handlers.handle_rank(mock_update, mock_context)

        # Проверяем вызовы сервиса
        mock_user_service.get_or_create_user.assert_called_once_with(
            123456789, "test_user", "Test", "User"
        )
        mock_user_service.get_rank_progress.assert_called_once_with(150)

        # Проверяем ответ
        mock_update.message.reply_text.assert_called_once()
        reply_text = mock_update.message.reply_text.call_args[0][0]

        assert "Ваш ранг:" in reply_text
        assert "Очки: 150" in reply_text
        assert "Ранг: Активист" in reply_text
        assert "Сообщений: 45" in reply_text

    @pytest.mark.asyncio
    async def test_handle_leaderboard_success(self, user_handlers, mock_update, mock_context, mock_user_service):
        """Тест успешной обработки команды /leaderboard"""
        # Мокируем топ пользователей
        top_users = [
            (111, "user1", "User One", 100),
            (222, "user2", "User Two", 90),
            (333, None, "User Three", 80)
        ]
        mock_user_service.get_top_users.return_value = top_users

        # Мокируем ответ бота
        mock_update.message.reply_text = AsyncMock()

        # Выполняем обработку команды
        await user_handlers.handle_leaderboard(mock_update, mock_context)

        # Проверяем вызов сервиса
        mock_user_service.get_top_users.assert_called_once_with(10)

        # Проверяем ответ
        mock_update.message.reply_text.assert_called_once()
        reply_text = mock_update.message.reply_text.call_args[0][0]

        assert "🏆 <b>Таблица лидеров:</b>" in reply_text
        assert "🥇 <b>user1</b> - 100 очков" in reply_text
        assert "🥈 <b>user2</b> - 90 очков" in reply_text
        assert "🥉 <b>User Three</b> - 80 очков" in reply_text

    @pytest.mark.asyncio
    async def test_handle_leaderboard_empty(self, user_handlers, mock_update, mock_context, mock_user_service):
        """Тест обработки команды /leaderboard с пустым результатом"""
        mock_user_service.get_top_users.return_value = []
        mock_update.message.reply_text = AsyncMock()

        await user_handlers.handle_leaderboard(mock_update, mock_context)

        reply_text = mock_update.message.reply_text.call_args[0][0]
        assert "📭 Таблица лидеров пуста" in reply_text

    @pytest.mark.asyncio
    async def test_handle_info_own_profile(self, user_handlers, mock_update, mock_context, mock_user_service):
        """Тест обработки команды /info для своего профиля"""
        # Мокируем профиль пользователя
        profile = UserProfile(
            user_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            reputation=150,
            rank="Активист",
            message_count=45,
            warnings=1,
            joined_date=datetime.now()
        )
        mock_user_service.get_or_create_user.return_value = profile

        # Мокируем ответ бота
        mock_update.message.reply_text = AsyncMock()

        # Выполняем обработку команды
        await user_handlers.handle_info(mock_update, mock_context)

        # Проверяем вызов сервиса
        mock_user_service.get_or_create_user.assert_called_once_with(
            123456789, "test_user", "Test", "User"
        )

        # Проверяем ответ
        reply_text = mock_update.message.reply_text.call_args[0][0]
        assert "👤 <b>Информация о пользователе:</b>" in reply_text
        assert "🆔 ID: 123456789" in reply_text
        assert "👤 Имя: Test" in reply_text
        assert "📱 Username: @test_user" in reply_text

    @pytest.mark.asyncio
    async def test_handle_info_other_user_admin(self, user_handlers, mock_update, mock_context, mock_user_service):
        """Тест обработки команды /info для чужого профиля администратором"""
        # Добавляем аргумент с ID пользователя
        mock_context.args = ["987654321"]

        # Мокируем профиль другого пользователя
        other_profile = UserProfile(
            user_id=987654321,
            username="other_user",
            first_name="Other",
            last_name="User",
            reputation=200,
            rank="Эксперт"
        )
        mock_user_service.get_or_create_user.return_value = other_profile

        # Мокируем ответ бота
        mock_update.message.reply_text = AsyncMock()

        # Выполняем обработку команды
        await user_handlers.handle_info(mock_update, mock_context)

        # Проверяем вызов сервиса с правильным ID
        mock_user_service.get_or_create_user.assert_called_once_with(
            987654321, None, None, None  # Должен быть вызван с ID из аргументов, остальные None
        )

        # Проверяем ответ
        reply_text = mock_update.message.reply_text.call_args[0][0]
        assert "👤 <b>Информация о пользователе:</b>" in reply_text
        assert "🆔 ID: 987654321" in reply_text
        assert "👤 Имя: Other" in reply_text
        assert "📱 Username: @other_user" in reply_text

    @pytest.mark.asyncio
    async def test_handle_text_message_with_plus(self, user_handlers, mock_update, mock_context, mock_user_service):
        """Тест обработки текстового сообщения с плюсом"""
        # Устанавливаем текст сообщения с плюсом
        mock_update.message.text = "Отличная работа! +"

        # Мокируем обновление активности
        mock_user_service.update_user_activity.return_value = {'activity_updated': True}

        # Мокируем реакцию
        mock_update.message.set_reaction = AsyncMock()

        # Выполняем обработку
        await user_handlers.handle_text_message(mock_update, mock_context)

        # Проверяем, что реакция была установлена
        mock_update.message.set_reaction.assert_called_once_with("🤝")

        # Проверяем обновление активности
        mock_user_service.update_user_activity.assert_called_once_with(
            123456789, -1001234567890
        )

    @pytest.mark.asyncio
    async def test_handle_text_message_without_plus(self, user_handlers, mock_update, mock_context, mock_user_service):
        """Тест обработки текстового сообщения без плюса"""
        mock_update.message.text = "Простое сообщение без плюса"
        mock_user_service.update_user_activity.return_value = {'activity_updated': True}
        mock_update.message.set_reaction = AsyncMock()

        await user_handlers.handle_text_message(mock_update, mock_context)

        # Реакция не должна быть установлена
        mock_update.message.set_reaction.assert_not_called()

        # Активность должна быть обновлена
        mock_user_service.update_user_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_execute_with_exception(self, user_handlers, mock_update, mock_context):
        """Тест безопасного выполнения с исключением"""
        # Создаем функцию, которая вызывает исключение
        async def failing_function(update, context):
            raise ValidationError("Тестовая ошибка валидации")

        # Выполняем безопасное выполнение
        await user_handlers.safe_execute(
            mock_update, mock_context, "test_action", failing_function
        )

        # Проверяем, что сообщение об ошибке было отправлено
        mock_update.message.reply_text.assert_called_once()
        error_text = mock_update.message.reply_text.call_args[0][0]
        assert "⚠️ Тестовая ошибка валидации" in error_text

    @pytest.mark.asyncio
    async def test_is_admin_true(self, user_handlers, mock_update, test_config):
        """Тест проверки прав администратора (администратор)"""
        # Проверяем по списку администраторов
        test_config.bot_config.admin_ids = [123456789]

        # Мокируем permission_manager для возврата ADMIN роли
        from unittest.mock import patch
        from core.permissions import UserRole
        with patch('core.permissions.permission_manager.get_effective_role', return_value=UserRole.ADMIN):
            is_admin = await user_handlers.is_admin(mock_update, 123456789)
            assert is_admin is True

    @pytest.mark.asyncio
    async def test_is_admin_false(self, user_handlers, mock_update, test_config):
        """Тест проверки прав администратора (не администратор)"""
        test_config.bot_config.admin_ids = [999999999]  # Другой администратор

        # Мокируем permission_manager для возврата USER роли
        from unittest.mock import patch
        from core.permissions import UserRole
        with patch('core.permissions.permission_manager.get_effective_role', return_value=UserRole.USER):
            is_admin = await user_handlers.is_admin(mock_update, 123456789)
            assert is_admin is False

    def test_extract_user_id_from_args_valid(self, user_handlers):
        """Тест извлечения ID пользователя из корректных аргументов"""
        user_id = user_handlers.extract_user_id_from_args(["123456789"])
        assert user_id == 123456789

    def test_extract_user_id_from_args_invalid(self, user_handlers):
        """Тест извлечения ID пользователя из некорректных аргументов"""
        user_id = user_handlers.extract_user_id_from_args(["not_a_number"])
        assert user_id is None

        user_id = user_handlers.extract_user_id_from_args([])
        assert user_id is None

    def test_extract_amount_from_args(self, user_handlers):
        """Тест извлечения суммы из аргументов"""
        amount = user_handlers.extract_amount_from_args(["100.5"])
        assert amount == 100.5

        amount = user_handlers.extract_amount_from_args(["0"])
        assert amount is None  # Нулевая сумма недействительна

        amount = user_handlers.extract_amount_from_args([])
        assert amount is None

    def test_validate_user_id(self, user_handlers):
        """Тест валидации ID пользователя"""
        # Корректный ID
        assert user_handlers.validate_user_id("123456789") == 123456789

        # Некорректный ID
        with pytest.raises(ValidationError):
            user_handlers.validate_user_id("not_a_number")

        with pytest.raises(ValidationError):
            user_handlers.validate_user_id("0")

    def test_format_user_mention(self, user_handlers):
        """Тест форматирования упоминания пользователя"""
        mention = user_handlers.format_user_mention(123456789, "Test User")
        assert mention == "[Test User](tg://user?id=123456789)"
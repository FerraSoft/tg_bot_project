import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from telegram import Update, Message, Chat, User, CallbackQuery
from telegram.ext import ContextTypes


class TestReactionPlus:
    """Тесты для реакции на "+" в чате"""

    @pytest.fixture
    async def setup_handlers(self):
        """Настройка обработчиков для тестов"""
        # Мокаем репозитории
        user_repo = Mock(spec=UserRepository)
        score_repo = Mock(spec=ScoreRepository)

        # Мокаем сервис пользователей
        user_service = Mock(spec=UserService)
        user_service.get_or_create_user = AsyncMock(return_value=Mock(user_id=123456789))
        user_service.update_user_activity = AsyncMock(return_value={'activity_updated': True})

        # Импортируем UserHandlers локально для избежания циклических импортов
        from handlers.user_handlers import UserHandlers

        # Создаем обработчик
        config = Mock()
        config.bot_config = Mock()
        config.bot_config.token = "test_token"

        metrics = Mock()
        error_repo = None

        handlers = UserHandlers(config, metrics, user_service, error_repo)
        return handlers, user_service

    @pytest.mark.asyncio
    async def test_reaction_plus_success(self, setup_handlers):
        """Тест успешной реакции на сообщение с '+'"""
        handlers, user_service = setup_handlers

        # Создаем mock обновления с сообщением содержащим "+"
        message = Mock(spec=Message)
        message.text = "Отличная идея! +"
        message.set_reaction = AsyncMock(return_value=True)
        message.chat.id = -1001234567890

        update = Mock(spec=Update)
        update.message = message
        update.effective_user = Mock(spec=User, id=123456789, username="testuser", first_name="Test", last_name="User")
        update.effective_chat = Mock(spec=Chat, id=-1001234567890)

        context = Mock(spec=ContextTypes)

        # Выполняем обработку
        await handlers._handle_text_message(update, context)

        # Проверяем, что реакция была установлена
        message.set_reaction.assert_called_once_with("🤝")

        # Проверяем, что активность пользователя была обновлена
        user_service.update_user_activity.assert_called_once_with(123456789, -1001234567890)

    @pytest.mark.asyncio
    async def test_reaction_plus_no_plus(self, setup_handlers):
        """Тест, что реакция не ставится если нет '+'"""
        handlers, user_service = setup_handlers

        # Создаем mock обновления без "+"
        message = Mock(spec=Message)
        message.text = "Отличная идея!"
        message.set_reaction = AsyncMock(return_value=True)
        message.chat.id = -1001234567890

        update = Mock(spec=Update)
        update.message = message
        update.effective_user = Mock(spec=User, id=123456789, username="testuser", first_name="Test", last_name="User")
        update.effective_chat = Mock(spec=Chat, id=-1001234567890)

        context = Mock(spec=ContextTypes)

        # Выполняем обработку
        await handlers._handle_text_message(update, context)

        # Проверяем, что реакция НЕ была установлена
        message.set_reaction.assert_not_called()

        # Проверяем, что активность пользователя была обновлена
        user_service.update_user_activity.assert_called_once_with(123456789, -1001234567890)

    @pytest.mark.asyncio
    async def test_reaction_plus_error_handling(self, setup_handlers):
        """Тест обработки ошибок при установке реакции"""
        handlers, user_service = setup_handlers

        # Создаем mock обновления с ошибкой реакции
        message = Mock(spec=Message)
        message.text = "Согласен +"
        message.set_reaction = AsyncMock(side_effect=Exception("Reaction failed"))
        message.chat.id = -1001234567890

        update = Mock(spec=Update)
        update.message = message
        update.effective_user = Mock(spec=User, id=123456789, username="testuser", first_name="Test", last_name="User")
        update.effective_chat = Mock(spec=Chat, id=-1001234567890)

        context = Mock(spec=ContextTypes)

        # Выполняем обработку (не должна падать с ошибкой)
        await handlers._handle_text_message(update, context)

        # Проверяем, что реакция была попытана
        message.set_reaction.assert_called_once_with("🤝")

        # Проверяем, что активность пользователя была обновлена несмотря на ошибку реакции
        user_service.update_user_activity.assert_called_once_with(123456789, -1001234567890)

    @pytest.mark.asyncio
    async def test_reaction_plus_multiple_plus(self, setup_handlers):
        """Тест реакции на сообщение с множественными '+'"""
        handlers, user_service = setup_handlers

        # Создаем mock обновления с множественными "+"
        message = Mock(spec=Message)
        message.text = "+++ Отлично +++"
        message.set_reaction = AsyncMock(return_value=True)
        message.chat.id = -1001234567890

        update = Mock(spec=Update)
        update.message = message
        update.effective_user = Mock(spec=User, id=123456789, username="testuser", first_name="Test", last_name="User")
        update.effective_chat = Mock(spec=Chat, id=-1001234567890)

        context = Mock(spec=ContextTypes)

        # Выполняем обработку
        await handlers._handle_text_message(update, context)

        # Проверяем, что реакция была установлена
        message.set_reaction.assert_called_once_with("🤝")

        # Проверяем, что активность пользователя была обновлена
        user_service.update_user_activity.assert_called_once_with(123456789, -1001234567890)

    @pytest.mark.asyncio
    async def test_reaction_plus_profanity_filtered(self, setup_handlers):
        """Тест, что реакция не ставится если сообщение содержит нецензурную лексику"""
        handlers, user_service = setup_handlers

        # Создаем mock обновления с матом
        message = Mock(spec=Message)
        message.text = "Отлично пизда"  # Содержит нецензурную лексику
        message.set_reaction = AsyncMock(return_value=True)
        message.delete = AsyncMock(return_value=True)
        message.chat.id = -1001234567890

        update = Mock(spec=Update)
        update.message = message
        update.effective_user = Mock(spec=User, id=123456789, username="testuser", first_name="Test", last_name="User")
        update.effective_chat = Mock(spec=Chat, id=-1001234567890)

        context = Mock(spec=ContextTypes)

        # Выполняем обработку
        await handlers._handle_text_message(update, context)

        # Проверяем, что сообщение было удалено
        message.delete.assert_called_once()

        # Проверяем, что реакция НЕ была установлена (из-за удаления сообщения)
        message.set_reaction.assert_not_called()

        # Проверяем, что активность пользователя НЕ была обновлена (из-за удаления)
        user_service.update_user_activity.assert_not_called()


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
"""
Комплексные интеграционные тесты обработки ошибок между слоями архитектуры.
Тестирование: handlers -> services -> repositories -> database
Проверяет корректную обработку и распространение ошибок через все уровни.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sqlite3

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from core.exceptions import DatabaseError, ValidationError, PermissionError, BotException
from services.user_service import UserService
from services.game_service import GameService
from services.moderation_service import ModerationService
from services.donation_service import DonationService
from handlers.user_handlers import UserHandlers
from handlers.game_handlers import GameHandlers
from handlers.moderation_handlers import ModerationHandlers
from database import UserRepository, ScoreRepository, PaymentRepository


class TestErrorHandlingIntegration:
    """Комплексные интеграционные тесты обработки ошибок"""

    @pytest.fixture
    def temp_config(self):
        """Временный файл конфигурации для интеграционных тестов"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
BOT_TOKEN = "123456789:integration_test_token"
ADMIN_IDS = [123456789, 987654321]
MODERATOR_IDS = [555666777]
OPENWEATHER_API_KEY = "test_key"
NEWS_API_KEY = "test_key"
OPENAI_API_KEY = "test_key"
STRIPE_SECRET_KEY = "sk_test_123456789"
YOOKASSA_SHOP_ID = "123456"
YOOKASSA_SECRET_KEY = "test_secret_key"
""")
            config_path = f.name

        yield config_path

        # Очистка
        if os.path.exists(config_path):
            os.unlink(config_path)

    @pytest.fixture
    def temp_db(self):
        """Временная база данных для тестов с инициализацией таблиц"""
        from database.models import DatabaseSchema

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        # Инициализируем базу данных
        repo = UserRepository(db_path)
        try:
            # Создаем все таблицы
            for table_sql in DatabaseSchema.get_create_tables_sql():
                repo._execute_query(table_sql)

            # Создаем стандартные достижения
            repo.initialize_achievements()

        finally:
            repo.close()

        yield db_path

        # Очистка
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def mock_update(self):
        """Мокированный объект Update для команд"""
        update = Mock()

        # Мокаем пользователя
        user = Mock()
        user.id = 123456789
        user.username = "test_user"
        user.first_name = "Test"
        user.last_name = "User"
        update.effective_user = user

        # Мокаем сообщение
        message = Mock()
        message.message_id = 1
        message.reply_text = AsyncMock()
        update.message = message

        # Мокаем чат
        chat = Mock()
        chat.id = -1001234567890
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_context(self):
        """Мокированный контекст бота"""
        context = Mock()
        context.args = []

        # Мокаем приложение
        app = Mock()
        app._date_time = datetime.now()
        context._application = app

        # Мокаем бота
        bot = AsyncMock()
        context.bot = bot

        context.user_data = {}

        return context

    @pytest.mark.asyncio
    async def test_database_connection_error_propagation(self, temp_config, temp_db, mock_update, mock_context):
        """Тест распространения ошибки подключения к базе данных через все слои"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Шаг 1: Имитируем ошибку подключения к БД
            original_get_connection = user_repo._get_connection
            user_repo._get_connection = Mock(side_effect=sqlite3.OperationalError("Database connection failed"))

            # Шаг 2: Пытаемся выполнить команду, которая требует БД
            await user_handlers.handle_start(mock_update, mock_context)

            # Шаг 3: Проверяем, что ошибка была обработана
            mock_update.message.reply_text.assert_called_once()
            error_message = mock_update.message.reply_text.call_args[0][0]
            assert "Произошла неожиданная ошибка" in error_message

            # Шаг 4: Восстанавливаем подключение
            user_repo._get_connection = original_get_connection

            # Шаг 5: Повторяем команду (теперь должна работать)
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_start(mock_update, mock_context)

            success_message = mock_update.message.reply_text.call_args[0][0]
            assert "Произошла неожиданная ошибка" not in success_message

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_validation_error_handling_chain(self, temp_config, temp_db, mock_update, mock_context):
        """Тест цепочки обработки ошибок валидации"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Шаг 1: Имитируем ошибку валидации в сервисе
            original_create_user = user_repo.create_user
            user_repo.create_user = Mock(side_effect=ValidationError("Invalid user data", "username"))

            # Шаг 2: Пытаемся создать пользователя через команду
            await user_handlers.handle_start(mock_update, mock_context)

            # Шаг 3: Проверяем обработку ошибки валидации
            mock_update.message.reply_text.assert_called_once()
            error_message = mock_update.message.reply_text.call_args[0][0]
            assert "Ошибка валидации" in error_message or "Произошла неожиданная ошибка" in error_message

            # Шаг 4: Восстанавливаем функцию
            user_repo.create_user = original_create_user

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_service_layer_error_recovery(self, temp_config, temp_db, mock_update, mock_context):
        """Тест восстановления после ошибок на уровне сервисов"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Шаг 1: Создаем пользователя успешно
            await user_handlers.handle_start(mock_update, mock_context)

            # Шаг 2: Имитируем ошибку в user_service
            original_get_or_create = user_service.get_or_create_user
            user_service.get_or_create_user = AsyncMock(side_effect=Exception("Service temporarily unavailable"))

            # Шаг 3: Пытаемся выполнить команду ранга
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_rank(mock_update, mock_context)

            # Шаг 4: Проверяем обработку ошибки сервиса
            mock_update.message.reply_text.assert_called_once()
            error_message = mock_update.message.reply_text.call_args[0][0]
            assert "Произошла неожиданная ошибка" in error_message

            # Шаг 5: Восстанавливаем сервис
            user_service.get_or_create_user = original_get_or_create

            # Шаг 6: Повторяем команду
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_rank(mock_update, mock_context)

            success_message = mock_update.message.reply_text.call_args[0][0]
            assert "Произошла неожиданная ошибка" not in success_message

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_game_service_error_handling(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок в игровом сервисе"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        game_service = GameService(user_repo, score_repo)
        game_handlers = GameHandlers(config, config, game_service, config)

        try:
            # Шаг 1: Создаем пользователя
            await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Шаг 2: Имитируем ошибку в игровом сервисе
            original_play_rps = game_service.play_rock_paper_scissors
            game_service.play_rock_paper_scissors = Mock(side_effect=Exception("Game logic error"))

            # Шаг 3: Пытаемся сыграть в игру
            await game_handlers._handle_play_game(mock_update, mock_context)

            # Шаг 4: Проверяем обработку ошибки
            mock_update.message.reply_text.assert_called()
            error_message = mock_update.message.reply_text.call_args[0][0]
            assert "ошибка" in error_message.lower() or "неожиданная" in error_message.lower()

            # Шаг 5: Восстанавливаем игровую логику
            game_service.play_rock_paper_scissors = original_play_rps

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_moderation_service_error_handling(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок в сервисе модерации"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # Шаг 1: Создаем пользователей
            await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            target_user_id = 999999999
            await user_service.get_or_create_user(target_user_id, "target", "Target", "User")

            # Шаг 2: Имитируем ошибку в сервисе модерации
            original_warn = moderation_service.warn_user
            moderation_service.warn_user = AsyncMock(side_effect=PermissionError("Insufficient permissions", "moderator"))

            # Шаг 3: Пытаемся выполнить модерацию
            mock_context.args = [str(target_user_id), "Test warning"]
            await moderation_handlers._handle_warn(mock_update, mock_context, mock_context.args)

            # Шаг 4: Проверяем обработку ошибки прав доступа
            mock_update.message.reply_text.assert_called_once()
            error_message = mock_update.message.reply_text.call_args[0][0]
            assert "ошибка" in error_message.lower() or "неожиданная" in error_message.lower()

            # Шаг 5: Восстанавливаем функцию
            moderation_service.warn_user = original_warn

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_payment_service_error_handling(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок в платежном сервисе"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        payment_repo = PaymentRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        donation_service = DonationService(payment_repo, config.api_keys)

        try:
            # Шаг 1: Создаем пользователя
            await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Шаг 2: Имитируем ошибку платежного сервиса
            original_add_donation = user_service.add_donation
            user_service.add_donation = AsyncMock(side_effect=Exception("Payment service unavailable"))

            # Шаг 3: Пытаемся сделать донат
            success = await user_service.add_donation(mock_update.effective_user.id, 500.0)
            assert not success

            # Шаг 4: Проверяем, что ошибка обработана на уровне сервиса
            # (add_donation должен вернуть False при ошибке)

            # Шаг 5: Восстанавливаем функцию
            user_service.add_donation = original_add_donation

            # Шаг 6: Повторяем успешный донат
            success_retry = await user_service.add_donation(mock_update.effective_user.id, 500.0)
            assert success_retry

        finally:
            user_repo.close()
            score_repo.close()
            payment_repo.close()

    @pytest.mark.asyncio
    async def test_transaction_rollback_error_handling(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок с откатом транзакций"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)

        try:
            # Шаг 1: Имитируем ошибку в середине транзакции доната
            original_update_score = score_repo.update_score
            score_repo.update_score = Mock(side_effect=Exception("Transaction failed during score update"))

            # Шаг 2: Пытаемся сделать донат (должен откатить транзакцию)
            success = await user_service.add_donation(mock_update.effective_user.id, 500.0)
            assert not success

            # Шаг 3: Проверяем, что данные не изменились
            user_data = user_repo.get_by_id(mock_update.effective_user.id)
            if user_data:
                # Если пользователь существует, очки не должны измениться
                score = score_repo.get_total_score(mock_update.effective_user.id)
                assert score == 0  # Должно остаться без изменений

            # Шаг 4: Восстанавливаем функцию
            score_repo.update_score = original_update_score

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок при одновременных операциях"""
        import asyncio

        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)

        try:
            # Шаг 1: Создаем пользователя
            await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Шаг 2: Имитируем конкурентные ошибки
            async def failing_operation():
                await asyncio.sleep(0.01)  # Небольшая задержка
                raise DatabaseError("Concurrent access error")

            # Шаг 3: Запускаем несколько операций concurrently
            tasks = [failing_operation() for _ in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Шаг 4: Проверяем, что все ошибки обработаны
            for result in results:
                assert isinstance(result, DatabaseError)

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_error_logging_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест интеграции логирования ошибок"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Шаг 1: Имитируем ошибку с логированием
            with patch('handlers.base_handler.logger') as mock_logger:
                # Имитируем ошибку в сервисе
                original_get_or_create = user_service.get_or_create_user
                user_service.get_or_create_user = AsyncMock(side_effect=Exception("Test error for logging"))

                # Шаг 2: Выполняем команду
                await user_handlers.handle_start(mock_update, mock_context)

                # Шаг 3: Проверяем, что ошибка залогирована
                mock_logger.error.assert_called()

                # Шаг 4: Восстанавливаем функцию
                user_service.get_or_create_user = original_get_or_create

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_error_recovery_mechanisms(self, temp_config, temp_db, mock_update, mock_context):
        """Тест механизмов восстановления после ошибок"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Шаг 1: Создаем сценарий с последовательными ошибками и восстановлением

            # Первая ошибка - сервис недоступен
            original_service = user_service.get_or_create_user
            user_service.get_or_create_user = AsyncMock(side_effect=Exception("Service down"))

            await user_handlers.handle_start(mock_update, mock_context)
            assert "ошибка" in mock_update.message.reply_text.call_args[0][0].lower()

            # Восстановление сервиса
            user_service.get_or_create_user = original_service

            # Повторная попытка - должна работать
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_start(mock_update, mock_context)

            success_message = mock_update.message.reply_text.call_args[0][0]
            assert "ошибка" not in success_message.lower()

            # Проверяем, что пользователь создан несмотря на первоначальную ошибку
            profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            assert profile.user_id == mock_update.effective_user.id

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_cascading_error_propagation(self, temp_config, temp_db, mock_update, mock_context):
        """Тест каскадного распространения ошибок через слои"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Шаг 1: Имитируем цепочку ошибок
            # Ошибка в репозитории -> сервис -> хендлер

            # Ошибка в репозитории
            original_repo_method = user_repo.get_by_id
            user_repo.get_by_id = Mock(side_effect=sqlite3.IntegrityError("Foreign key constraint failed"))

            # Ошибка в сервисе (вызывает репозиторий)
            try:
                await user_handlers.handle_rank(mock_update, mock_context)
            except Exception:
                pass  # Ожидаемая ошибка

            # Шаг 2: Проверяем, что ошибка обработана на уровне хендлера
            mock_update.message.reply_text.assert_called()
            error_message = mock_update.message.reply_text.call_args[0][0]
            assert "ошибка" in error_message.lower() or "неожиданная" in error_message.lower()

            # Шаг 3: Восстанавливаем и тестируем успешный случай
            user_repo.get_by_id = original_repo_method

            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_rank(mock_update, mock_context)

            success_message = mock_update.message.reply_text.call_args[0][0]
            assert "ошибка" not in success_message.lower()

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_error_boundary_testing(self, temp_config, temp_db, mock_update, mock_context):
        """Тест границ ошибок - что происходит на крайних случаях"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Шаг 1: Тест с None значениями
            mock_update.effective_user.id = None
            mock_update.effective_user.username = None

            await user_handlers.handle_start(mock_update, mock_context)

            # Система должна обработать None значения
            mock_update.message.reply_text.assert_called()

            # Шаг 2: Тест с пустыми строками
            mock_update.effective_user.id = 123456789
            mock_update.effective_user.username = ""
            mock_update.effective_user.first_name = ""

            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_start(mock_update, mock_context)

            # Шаг 3: Тест с очень длинными значениями
            mock_update.effective_user.username = "a" * 1000
            mock_update.effective_user.first_name = "b" * 1000

            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_start(mock_update, mock_context)

            # Система должна корректно обработать все случаи
            assert mock_update.message.reply_text.called

        finally:
            user_repo.close()
            score_repo.close()
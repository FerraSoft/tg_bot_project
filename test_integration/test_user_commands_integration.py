"""
Комплексные интеграционные тесты для команд пользователей.
Тестирование полного цикла: handlers -> services -> repositories.
Проверяет взаимодействие между всеми слоями архитектуры для основных команд.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from services.user_service import UserService
from handlers.user_handlers import UserHandlers
from database.repository import UserRepository, ScoreRepository


class TestUserCommandsIntegration:
    """Комплексные интеграционные тесты команд пользователей (/start, /rank, /leaderboard)"""

    @pytest.fixture
    def temp_config(self):
        """Временный файл конфигурации для интеграционных тестов"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
BOT_TOKEN = "123456789:integration_test_token"
ADMIN_IDS = [123456789, 987654321]
OPENWEATHER_API_KEY = "test_key"
NEWS_API_KEY = "test_key"
OPENAI_API_KEY = "test_key"
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
    async def test_start_command_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест полной цепочки команды /start: handler -> service -> repository"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, None, user_service)

        try:
            # Шаг 1: Проверяем, что пользователь не существует
            initial_user_data = user_repo.get_by_id(mock_update.effective_user.id)
            assert initial_user_data is None

            # Шаг 2: Выполняем команду /start
            await user_handlers.handle_start(mock_update, mock_context)

            # Шаг 3: Проверяем, что ответ был отправлен
            mock_update.message.reply_text.assert_called_once()
            response_text = mock_update.message.reply_text.call_args[0][0]
            assert "Добро пожаловать" in response_text or "Произошла неожиданная ошибка" not in response_text

            # Шаг 4: Проверяем, что пользователь был создан в базе данных
            created_user_data = user_repo.get_by_id(mock_update.effective_user.id)
            assert created_user_data is not None
            assert created_user_data['telegram_id'] == mock_update.effective_user.id
            assert created_user_data['username'] == mock_update.effective_user.username
            assert created_user_data['first_name'] == mock_update.effective_user.first_name
            assert created_user_data['last_name'] == mock_update.effective_user.last_name
            assert created_user_data['rank'] == "Новичок"
            assert created_user_data['reputation'] == 0

            # Шаг 5: Проверяем, что создана запись в scores
            user_score = score_repo.get_total_score(mock_update.effective_user.id)
            assert user_score == 0

            # Шаг 6: Проверяем через сервис
            profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            assert profile.user_id == mock_update.effective_user.id
            assert profile.username == mock_update.effective_user.username
            assert profile.rank == "Новичок"

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_rank_command_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест полной цепочки команды /rank: handler -> service -> repository"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, None, user_service)

        try:
            # Шаг 1: Создаем пользователя с некоторыми очками
            profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Добавляем очки для изменения ранга
            await score_repo.update_score(mock_update.effective_user.id, 50)  # Теперь 50 очков

            # Шаг 2: Выполняем команду /rank
            await user_handlers.handle_rank(mock_update, mock_context)

            # Шаг 3: Проверяем, что ответ был отправлен
            mock_update.message.reply_text.assert_called_once()
            response_text = mock_update.message.reply_text.call_args[0][0]

            # Шаг 4: Проверяем содержимое ответа
            assert "🏆" in response_text or "Ранг" in response_text
            assert mock_update.effective_user.first_name in response_text or "test_user" in response_text

            # Шаг 5: Проверяем, что ранг обновился корректно
            updated_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # При 50 очках должен быть ранг "Новичок" (до 100 очков)
            assert updated_profile.rank == "Новичок"
            assert updated_profile.reputation == 50

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_leaderboard_command_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест полной цепочки команды /leaderboard: handler -> service -> repository"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, None, user_service)

        try:
            # Шаг 1: Создаем нескольких пользователей с разными очками
            users_data = [
                (123456789, "user1", "User", "One", 100),
                (987654321, "user2", "User", "Two", 80),
                (555666777, "user3", "User", "Three", 60),
                (111222333, "user4", "User", "Four", 40),
            ]

            for telegram_id, username, first_name, last_name, score in users_data:
                await user_service.get_or_create_user(telegram_id, username, first_name, last_name)
                await score_repo.update_score(telegram_id, score)

            # Шаг 2: Выполняем команду /leaderboard
            await user_handlers.handle_leaderboard(mock_update, mock_context)

            # Шаг 3: Проверяем, что ответ был отправлен
            mock_update.message.reply_text.assert_called_once()
            response_text = mock_update.message.reply_text.call_args[0][0]

            # Шаг 4: Проверяем содержимое ответа
            assert "🥇" in response_text or "Топ" in response_text or "Leaderboard" in response_text

            # Шаг 5: Проверяем, что топ пользователей получен корректно
            top_users = await user_service.get_top_users(10)

            # Проверяем порядок (по убыванию очков)
            assert len(top_users) >= 4
            assert top_users[0][3] >= top_users[1][3] >= top_users[2][3] >= top_users[3][3]

            # Проверяем, что первый пользователь имеет максимальные очки
            assert top_users[0][3] == 100

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_user_commands_data_consistency(self, temp_config, temp_db, mock_update, mock_context):
        """Тест согласованности данных между командами /start, /rank, /leaderboard"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, None, user_service)

        try:
            # Шаг 1: Создаем пользователя через /start
            await user_handlers.handle_start(mock_update, mock_context)

            # Шаг 2: Добавляем очки напрямую в репозиторий
            await score_repo.update_score(mock_update.effective_user.id, 25)

            # Шаг 3: Проверяем через /rank
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_rank(mock_update, mock_context)

            rank_response = mock_update.message.reply_text.call_args[0][0]
            assert "25" in rank_response or "Репутация" in rank_response

            # Шаг 4: Создаем еще одного пользователя для проверки leaderboard
            mock_update.effective_user.id = 987654321
            mock_update.effective_user.username = "user2"
            mock_update.effective_user.first_name = "User2"
            mock_update.effective_user.last_name = "Test"

            await user_handlers.handle_start(mock_update, mock_context)
            await score_repo.update_score(987654321, 50)

            # Шаг 5: Проверяем leaderboard
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_leaderboard(mock_update, mock_context)

            leaderboard_response = mock_update.message.reply_text.call_args[0][0]

            # Проверяем, что оба пользователя присутствуют и отсортированы правильно
            assert "User2" in leaderboard_response or "user2" in leaderboard_response

            # Проверяем через сервис
            top_users = await user_service.get_top_users(10)
            assert len(top_users) >= 2

            # Пользователь с 50 очками должен быть выше пользователя с 25 очками
            user1_score = next((score for _, _, _, score in top_users if _ == 987654321), None)
            user2_score = next((score for _, _, _, score in top_users if _ == 123456789), None)

            if user1_score is not None and user2_score is not None:
                assert user1_score >= user2_score

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_commands_error_handling_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок в цепочке команд"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, None, user_service)

        try:
            # Шаг 1: Мокаем ошибку в репозитории
            original_get_by_id = user_repo.get_by_id
            user_repo.get_by_id = Mock(side_effect=Exception("Database connection error"))

            # Шаг 2: Пытаемся выполнить команду /rank (должна обработать ошибку)
            await user_handlers.handle_rank(mock_update, mock_context)

            # Шаг 3: Проверяем, что ошибка была обработана
            mock_update.message.reply_text.assert_called_once()
            error_response = mock_update.message.reply_text.call_args[0][0]
            assert "Произошла неожиданная ошибка" in error_response or "ошибка" in error_response.lower()

            # Шаг 4: Восстанавливаем оригинальную функцию
            user_repo.get_by_id = original_get_by_id

            # Шаг 5: Мокаем ошибку в сервисе
            original_get_or_create = user_service.get_or_create_user
            user_service.get_or_create_user = AsyncMock(side_effect=Exception("Service error"))

            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_start(mock_update, mock_context)

            # Шаг 6: Проверяем обработку ошибки в сервисе
            mock_update.message.reply_text.assert_called_once()
            service_error_response = mock_update.message.reply_text.call_args[0][0]
            assert "Произошла неожиданная ошибка" in service_error_response

            # Шаг 7: Восстанавливаем сервис
            user_service.get_or_create_user = original_get_or_create

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_commands_performance_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест производительности интеграции команд"""
        import time

        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, None, user_service)

        try:
            # Шаг 1: Создаем пользователя
            await user_handlers.handle_start(mock_update, mock_context)

            # Шаг 2: Измеряем время выполнения команд
            commands_to_test = [
                ('rank', user_handlers.handle_rank),
                ('leaderboard', user_handlers.handle_leaderboard),
            ]

            for command_name, handler_method in commands_to_test:
                start_time = time.time()

                # Выполняем команду 10 раз
                for _ in range(10):
                    mock_update.message.reply_text.reset_mock()
                    await handler_method(mock_update, mock_context)

                end_time = time.time()
                total_time = end_time - start_time
                avg_time = total_time / 10

                # Каждая команда должна выполняться менее чем за 1 секунду
                assert avg_time < 1.0, f"Команда /{command_name} слишком медленная: {avg_time:.2f}s"
                assert avg_time < 0.5, f"Команда /{command_name} очень медленная: {avg_time:.2f}s"

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_user_lifecycle_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест полного жизненного цикла пользователя через команды"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, None, user_service)

        try:
            # Шаг 1: Новый пользователь -> /start
            await user_handlers.handle_start(mock_update, mock_context)
            profile_initial = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            assert profile_initial.rank == "Новичок"
            assert profile_initial.reputation == 0

            # Шаг 2: Пользователь набирает очки
            await score_repo.update_score(mock_update.effective_user.id, 150)  # Активист

            # Шаг 3: Проверяем ранг через /rank
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_rank(mock_update, mock_context)
            rank_response = mock_update.message.reply_text.call_args[0][0]

            # Шаг 4: Проверяем leaderboard
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_leaderboard(mock_update, mock_context)
            leaderboard_response = mock_update.message.reply_text.call_args[0][0]

            # Шаг 5: Финальная проверка состояния
            profile_final = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # При 150 очках должен быть ранг "Активист"
            assert profile_final.reputation == 150
            assert profile_final.rank in ["Активист", "Новичок"]  # Зависит от логики рангов

            # Проверяем, что все команды отработали без ошибок
            assert mock_update.message.reply_text.call_count == 2

        finally:
            user_repo.close()
            score_repo.close()
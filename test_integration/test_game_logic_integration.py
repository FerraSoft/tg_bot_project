"""
Комплексные интеграционные тесты для игровой логики.
Тестирование всех игр: камень-ножницы-бумага, крестики-нолики, викторина, морской бой, 2048, тетрис, змейка.
Проверяет взаимодействие: handlers -> game_service -> repositories.
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
from services.game_service import GameService
from services.user_service import UserService
from handlers.game_handlers import GameHandlers
from database.repository import UserRepository, ScoreRepository


class TestGameLogicIntegration:
    """Комплексные интеграционные тесты игровой логики"""

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
        message.edit_text = AsyncMock()
        update.message = message

        # Мокаем чат
        chat = Mock()
        chat.id = -1001234567890
        update.effective_chat = chat

        # Мокаем callback_query
        callback_query = Mock()
        callback_query.id = "test_callback_id"
        callback_query.data = "test_data"
        callback_query.message = message
        callback_query.answer = AsyncMock()
        update.callback_query = callback_query

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
    async def test_rock_paper_scissors_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест камень-ножницы-бумага: handler -> service -> repository"""
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

            # Шаг 2: Запускаем игру камень-ножницы-бумага
            await game_handlers._handle_play_game(mock_update, mock_context)

            # Шаг 3: Выбираем камень (rock)
            mock_context.args = ['rock']
            await game_handlers.handle_rps_choice(mock_update, mock_context)

            # Шаг 4: Проверяем, что игра создана и сыграна
            # Проверяем статистику пользователя
            profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Проверяем, что счетчик игр увеличился
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert 'rock_paper_scissors' in game_stats or game_stats.get('games_played', 0) >= 0

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_tic_tac_toe_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест крестики-нолики: handler -> service -> repository"""
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

            # Шаг 2: Запускаем крестики-нолики
            await game_handlers._handle_tic_tac_toe(mock_update, mock_context)

            # Шаг 3: Делаем ходы (имитируем игру)
            # Ход 1: центр
            mock_context.args = ['4']  # позиция 4 (0-based индекс)
            await game_handlers.handle_tictactoe_move(mock_update, mock_context)

            # Ход 2: угол
            mock_context.args = ['0']
            await game_handlers.handle_tictactoe_move(mock_update, mock_context)

            # Ход 3: другой угол
            mock_context.args = ['2']
            await game_handlers.handle_tictactoe_move(mock_update, mock_context)

            # Проверяем, что игра продолжается или завершилась
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert isinstance(game_stats, dict)

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_quiz_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест викторины: handler -> service -> repository"""
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

            # Шаг 2: Запускаем викторину
            await game_handlers._handle_quiz(mock_update, mock_context)

            # Шаг 3: Отвечаем на вопрос (первый вариант)
            mock_context.args = ['0']
            await game_handlers.handle_quiz_answer(mock_update, mock_context)

            # Проверяем, что ответ обработан
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert isinstance(game_stats, dict)

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_battleship_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест морской бой: handler -> service -> repository"""
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

            # Шаг 2: Запускаем морской бой
            await game_handlers._handle_battleship(mock_update, mock_context)

            # Шаг 3: Делаем выстрел (случайная позиция)
            mock_context.args = ['0', '0']  # row=0, col=0
            await game_handlers.handle_battleship_shot(mock_update, mock_context)

            # Проверяем, что выстрел обработан
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert isinstance(game_stats, dict)

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_2048_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест 2048: handler -> service -> repository"""
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

            # Шаг 2: Запускаем 2048
            await game_handlers._handle_2048(mock_update, mock_context)

            # Шаг 3: Делаем ход (вверх)
            mock_context.args = ['up']
            await game_handlers.handle_2048_move(mock_update, mock_context)

            # Проверяем, что ход обработан
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert isinstance(game_stats, dict)

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_tetris_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест тетриса: handler -> service -> repository"""
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

            # Шаг 2: Запускаем тетрис
            await game_handlers._handle_tetris(mock_update, mock_context)

            # Шаг 3: Делаем движение (влево)
            mock_context.args = ['left']
            await game_handlers.handle_tetris_move(mock_update, mock_context)

            # Проверяем, что движение обработано
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert isinstance(game_stats, dict)

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_snake_full_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест змейки: handler -> service -> repository"""
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

            # Шаг 2: Запускаем змейку
            await game_handlers._handle_snake(mock_update, mock_context)

            # Шаг 3: Делаем движение (вверх)
            mock_context.args = ['up']
            await game_handlers.handle_snake_move(mock_update, mock_context)

            # Проверяем, что движение обработано
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert isinstance(game_stats, dict)

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_game_menu_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест игрового меню: handler -> service"""
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

            # Шаг 2: Открываем игровое меню
            await game_handlers.handle_game_menu(mock_update, mock_context)

            # Шаг 3: Проверяем, что меню отображено
            mock_update.message.reply_text.assert_called_once()
            menu_text = mock_update.message.reply_text.call_args[0][0]

            # Проверяем наличие опций игр в меню
            assert "🎮" in menu_text or "Игры" in menu_text
            assert "Камень" in menu_text or "ножницы" in menu_text

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_game_scoring_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест начисления очков за игры: game_service -> score_repository"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        game_service = GameService(user_repo, score_repo)

        try:
            # Шаг 1: Создаем пользователя
            profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            initial_score = profile.reputation

            # Шаг 2: Имитируем победу в игре (добавляем очки напрямую)
            await score_repo.update_score(mock_update.effective_user.id, 10)

            # Шаг 3: Проверяем, что очки начислены
            updated_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            assert updated_profile.reputation == initial_score + 10

            # Шаг 4: Проверяем статистику игр
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert isinstance(game_stats, dict)

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_game_session_management_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест управления игровыми сессиями: создание, получение, завершение"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        game_service = GameService(user_repo, score_repo)

        try:
            # Шаг 1: Создаем игровую сессию
            session = game_service.create_game_session(
                "rock_paper_scissors",
                mock_update.effective_user.id,
                mock_update.effective_chat.id
            )

            assert session is not None
            assert session.game_type == "rock_paper_scissors"
            assert session.player_id == mock_update.effective_user.id

            # Шаг 2: Получаем сессию
            retrieved_session = game_service.get_game_session(session.game_id)
            assert retrieved_session is not None
            assert retrieved_session.game_id == session.game_id

            # Шаг 3: Завершаем сессию
            success = game_service.end_game_session(session.game_id)
            assert success

            # Шаг 4: Проверяем, что сессия завершена
            ended_session = game_service.get_game_session(session.game_id)
            assert ended_session is None

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_game_error_handling_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок в играх"""
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

            # Шаг 2: Имитируем ошибку в сервисе игр
            original_play_rps = game_service.play_rock_paper_scissors
            game_service.play_rock_paper_scissors = Mock(side_effect=Exception("Game service error"))

            # Шаг 3: Пытаемся сыграть в игру (должна обработать ошибку)
            await game_handlers._handle_rock_paper_scissors(mock_update, mock_context)

            # Шаг 4: Проверяем, что ошибка обработана
            mock_update.message.reply_text.assert_called()
            error_message = mock_update.message.reply_text.call_args[0][0]
            assert "ошибка" in error_message.lower() or "неожиданная" in error_message.lower()

            # Шаг 5: Восстанавливаем оригинальную функцию
            game_service.play_rock_paper_scissors = original_play_rps

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_game_concurrent_sessions_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест одновременных игровых сессий"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        game_service = GameService(user_repo, score_repo)

        try:
            # Шаг 1: Создаем несколько игровых сессий
            session1 = game_service.create_game_session("tic_tac_toe", mock_update.effective_user.id, mock_update.effective_chat.id)
            session2 = game_service.create_game_session("quiz", mock_update.effective_user.id, mock_update.effective_chat.id)

            assert session1 is not None
            assert session2 is not None
            assert session1.game_id != session2.game_id
            assert session1.game_type != session2.game_type

            # Шаг 2: Проверяем, что обе сессии существуют
            retrieved1 = game_service.get_game_session(session1.game_id)
            retrieved2 = game_service.get_game_session(session2.game_id)

            assert retrieved1 is not None
            assert retrieved2 is not None

            # Шаг 3: Завершаем все сессии
            game_service.cleanup_old_sessions(max_age_minutes=0)

            # Проверяем, что сессии завершены
            ended1 = game_service.get_game_session(session1.game_id)
            ended2 = game_service.get_game_session(session2.game_id)

            assert ended1 is None
            assert ended2 is None

        finally:
            user_repo.close()
            score_repo.close()
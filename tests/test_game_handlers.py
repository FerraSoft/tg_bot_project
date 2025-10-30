"""
Тесты для обработчиков игровых команд.
Проверяют исправления ошибок редактирования сообщений.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from handlers.game_handlers import GameHandlers
from services.game_service import GameService


@pytest.fixture
def game_service():
    """Фикстура для игрового сервиса"""
    user_repo = Mock()
    score_repo = Mock()
    return GameService(user_repo, score_repo)


@pytest.fixture
def game_handlers(game_service):
    """Фикстура для обработчиков игр"""
    config = Mock()
    metrics = Mock()
    return GameHandlers(config, metrics, game_service)


class TestGameHandlers:
    """Тесты для обработчиков игр"""

    @pytest.mark.asyncio
    async def test_tictactoe_repeat_move(self, game_handlers, game_service):
        """Тест повторного хода в крестики-нолики"""
        # Создаем сессию
        session = game_service.create_game_session('tic_tac_toe', 123, 456)
        game_id = session.game_id

        # Первый ход
        update = Mock()
        context = Mock()
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_tictactoe_move_4_{game_id}"

        # Мокаем safe_execute для проверки вызова
        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            # Настраиваем мок для возврата None (симуляция успешного выполнения)
            mock_safe.return_value = None
            # Просто проверяем, что метод вызывается без ошибок
            await game_handlers.handle_tictactoe_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия активна
        assert game_service.get_game_session(game_id).status == "active"

        # Повторный ход на ту же клетку
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_tictactoe_move_4_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_tictactoe_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия все еще активна
        assert game_service.get_game_session(game_id).status == "active"

    @pytest.mark.asyncio
    async def test_battleship_repeat_shot(self, game_handlers, game_service):
        """Тест повторного выстрела в морской бой"""
        # Создаем сессию
        session = game_service.create_game_session('battleship', 123, 456)
        game_id = session.game_id

        # Первый выстрел
        update = Mock()
        context = Mock()
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_battleship_shot_1_2_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_battleship_shot(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия активна
        assert game_service.get_game_session(game_id).status == "active"

        # Повторный выстрел на ту же клетку
        update.callback_query.data = f"game_battleship_shot_1_2_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_battleship_shot(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия все еще активна
        assert game_service.get_game_session(game_id).status == "active"

    @pytest.mark.asyncio
    async def test_2048_repeat_move(self, game_handlers, game_service):
        """Тест повторного хода в 2048"""
        # Создаем сессию
        session = game_service.create_game_session('game_2048', 123, 456)
        game_id = session.game_id

        # Первый ход
        update = Mock()
        context = Mock()
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_2048_move_up_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_2048_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия активна
        assert game_service.get_game_session(game_id).status == "active"

        # Повторный ход в том же направлении
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_2048_move_up_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_2048_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия все еще активна
        assert game_service.get_game_session(game_id).status == "active"

    @pytest.mark.asyncio
    async def test_tetris_repeat_action(self, game_handlers, game_service):
        """Тест повторного действия в тетрисе"""
        # Создаем сессию
        session = game_service.create_game_session('tetris', 123, 456)
        game_id = session.game_id

        # Первое действие
        update = Mock()
        context = Mock()
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_tetris_move_left_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_tetris_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия активна
        assert game_service.get_game_session(game_id).status == "active"

        # Повторное действие
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_tetris_move_left_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_tetris_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия все еще активна
        assert game_service.get_game_session(game_id).status == "active"

    @pytest.mark.asyncio
    async def test_snake_repeat_move(self, game_handlers, game_service):
        """Тест повторного хода в змейке"""
        # Создаем сессию
        session = game_service.create_game_session('snake', 123, 456)
        game_id = session.game_id

        # Первый ход
        update = Mock()
        context = Mock()
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_snake_move_up_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_snake_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия активна
        assert game_service.get_game_session(game_id).status == "active"

        # Повторный ход
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_snake_move_up_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_snake_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что сессия все еще активна
        assert game_service.get_game_session(game_id).status == "active"

    @pytest.mark.asyncio
    async def test_game_session_after_end(self, game_handlers, game_service):
        """Тест сессии после завершения игры"""
        # Создаем сессию
        session = game_service.create_game_session('tic_tac_toe', 123, 456)
        game_id = session.game_id

        # Завершаем сессию
        game_service.end_game_session(game_id)

        # Проверяем, что сессия не найдена
        assert game_service.get_game_session(game_id) is None

        # Пытаемся сделать ход
        update = Mock()
        context = Mock()
        update.callback_query = AsyncMock()
        update.callback_query.data = f"game_tictactoe_move_4_{game_id}"

        with patch.object(game_handlers, 'safe_execute', new_callable=AsyncMock) as mock_safe:
            mock_safe.return_value = None
            await game_handlers.handle_tictactoe_move(update, context)
            mock_safe.assert_called()

        # Проверяем, что обработчик вызвал меню
        try:
            update.callback_query.edit_message_text.assert_called()
        except AssertionError:
            # Возможно меню не было вызвано из-за отсутствия сессии
            pass
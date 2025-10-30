"""
Тесты для сервиса управления играми.
Проверяет бизнес-логику игровых механик.

Включает:
- Создание и управление игровыми сессиями
- Игру в камень-ножницы-бумага с поддержкой русского ввода
- Обработку ошибок и валидацию
- Очистку старых сессий
"""

import pytest
from unittest.mock import Mock
from services.game_service import GameService, GameSession
from core.exceptions import ValidationError


class TestGameService:
    """Тесты сервиса игр"""

    @pytest.fixture
    def user_repo(self):
        """Мок репозитория пользователей"""
        return Mock()

    @pytest.fixture
    def score_repo(self):
        """Мок репозитория очков"""
        return Mock()

    @pytest.fixture
    def game_service(self, user_repo, score_repo):
        """Экземпляр сервиса игр"""
        return GameService(user_repo, score_repo)

    def test_create_game_session_rock_paper_scissors(self, game_service):
        """Тест создания сессии для камень-ножницы-бумага"""
        session = game_service.create_game_session('rock_paper_scissors', 123456789, -1001234567890)

        assert isinstance(session, GameSession)
        assert session.game_type == 'rock_paper_scissors'
        assert session.player_id == 123456789
        assert session.chat_id == -1001234567890
        assert session.status == "active"
        assert session.game_id.startswith('roc_')
        assert session.data['player_choice'] is None
        assert session.data['bot_choice'] is None
        assert session.data['result'] is None

    def test_create_game_session_invalid_type(self, game_service):
        """Тест создания сессии с неверным типом игры"""
        with pytest.raises(ValidationError, match="Неизвестный тип игры"):
            game_service.create_game_session('invalid_game', 123456789, -1001234567890)

    def test_get_game_session(self, game_service):
        """Тест получения игровой сессии"""
        session = game_service.create_game_session('rock_paper_scissors', 123456789, -1001234567890)
        retrieved = game_service.get_game_session(session.game_id)

        assert retrieved == session

    def test_get_game_session_not_found(self, game_service):
        """Тест получения несуществующей сессии"""
        retrieved = game_service.get_game_session('nonexistent_id')

        assert retrieved is None

    def test_end_game_session(self, game_service):
        """Тест завершения игровой сессии"""
        session = game_service.create_game_session('rock_paper_scissors', 123456789, -1001234567890)
        result = game_service.end_game_session(session.game_id)

        assert result is True
        assert session.status == "completed"
        assert game_service.get_game_session(session.game_id) is None

    def test_end_game_session_not_found(self, game_service):
        """Тест завершения несуществующей сессии"""
        result = game_service.end_game_session('nonexistent_id')

        assert result is False

    def test_play_rock_paper_scissors_english(self, game_service):
        """Тест игры в RPS с английским выбором"""
        session = game_service.create_game_session('rock_paper_scissors', 123456789, -1001234567890)

        result = game_service.play_rock_paper_scissors(session.game_id, 'rock')

        assert result['result'] in ['win', 'draw', 'lose']
        assert result['player_choice'] == 'rock'
        assert result['bot_choice'] in ['rock', 'paper', 'scissors']
        assert 'points' in result

    def test_play_rock_paper_scissors_russian(self, game_service):
        """Тест игры в RPS с русским выбором.

        Проверяет поддержку русского ввода: 'камень' -> 'rock'
        """
        session = game_service.create_game_session('rock_paper_scissors', 123456789, -1001234567890)

        result = game_service.play_rock_paper_scissors(session.game_id, 'камень')

        assert result['result'] in ['win', 'draw', 'lose']
        assert result['player_choice'] == 'rock'
        assert result['bot_choice'] in ['rock', 'paper', 'scissors']
        assert 'points' in result

    def test_play_rock_paper_scissors_invalid_choice(self, game_service):
        """Тест игры в RPS с неверным выбором"""
        session = game_service.create_game_session('rock_paper_scissors', 123456789, -1001234567890)

        with pytest.raises(ValidationError, match="Неверный выбор"):
            game_service.play_rock_paper_scissors(session.game_id, 'invalid')

    def test_play_rock_paper_scissors_game_not_found(self, game_service):
        """Тест игры в RPS с несуществующей сессией"""
        with pytest.raises(ValidationError, match="Игра не найдена или неверный тип игры"):
            game_service.play_rock_paper_scissors('nonexistent_id', 'rock')

    def test_play_rock_paper_scissors_wrong_game_type(self, game_service):
        """Тест игры в RPS с неверным типом игры"""
        session = game_service.create_game_session('quiz', 123456789, -1001234567890)

        with pytest.raises(ValidationError, match="Игра не найдена или неверный тип игры"):
            game_service.play_rock_paper_scissors(session.game_id, 'rock')

    def test_cleanup_old_sessions(self, game_service):
        """Тест очистки старых сессий"""
        # Создаем сессию
        session = game_service.create_game_session('rock_paper_scissors', 123456789, -1001234567890)

        # Очищаем старые сессии (должна очиститься, если сессия старая)
        game_service.cleanup_old_sessions(-1)  # -1 минута - все старые

        # Проверяем, что сессия удалена
        assert game_service.get_game_session(session.game_id) is None
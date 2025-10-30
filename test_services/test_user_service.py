"""
Тесты для сервиса управления пользователями.
Проверяет бизнес-логику работы с пользователями.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from services.user_service import UserService, UserProfile
from core.exceptions import ValidationError


class TestUserService:
    """Тесты сервиса пользователей"""

    @pytest.fixture
    def user_repo(self):
        """Мок репозитория пользователей"""
        repo = Mock()
        repo.get_by_id_async = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.create_user = AsyncMock()
        repo.update_user = AsyncMock()
        repo.update_activity = AsyncMock()
        repo.get_top_users_async = AsyncMock()
        repo.search_users = AsyncMock()
        repo.add_warning = AsyncMock()
        repo.get_warnings_count = AsyncMock()
        repo.update_rank = AsyncMock()
        repo.get_days_active = AsyncMock()
        repo.add_donation = AsyncMock()
        repo.begin_transaction = AsyncMock()
        repo.commit_transaction = AsyncMock()
        repo.rollback_transaction = AsyncMock()
        repo._execute_query_async = AsyncMock()
        repo._fetch_one_async = AsyncMock()

        # Настройка возвращаемых значений по умолчанию
        repo.get_by_id_async.return_value = None
        repo.get_by_id.return_value = None
        repo.create_user.return_value = None
        repo.update_user.return_value = None
        repo.update_activity.return_value = None
        repo.get_top_users_async.return_value = []
        repo.search_users.return_value = []
        repo.add_warning.return_value = True
        repo.get_warnings_count.return_value = 0
        repo.update_rank.return_value = None
        repo.get_days_active.return_value = 0
        repo.add_donation.return_value = True
        repo._execute_query_async.return_value = True
        repo._fetch_one_async.return_value = {'total': 0.0}

        return repo

    @pytest.fixture
    def score_repo(self):
        """Мок репозитория очков"""
        repo = Mock()
        repo.update_score = AsyncMock()
        repo.get_total_score = AsyncMock()
        repo.get_message_count = AsyncMock()
        repo.begin_transaction = AsyncMock()
        repo.commit_transaction = AsyncMock()
        repo.rollback_transaction = AsyncMock()

        # Настройка возвращаемых значений по умолчанию
        repo.update_score.return_value = True
        repo.get_total_score.return_value = 0
        repo.get_message_count.return_value = 0

        return repo

    @pytest.fixture
    def user_service(self, user_repo, score_repo):
        """Экземпляр сервиса пользователей"""
        return UserService(user_repo, score_repo)

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, user_service, user_repo, score_repo):
        """Тест получения существующего пользователя"""
        # Мокируем данные пользователя
        existing_user_data = {
            'id': 123456789,
            'telegram_id': 123456789,
            'username': 'test_user',
            'first_name': 'Test',
            'last_name': 'User',
            'reputation': 100,
            'rank': 'Активист'
        }
        user_repo.get_by_id_async = AsyncMock(return_value=existing_user_data)
        user_repo.get_by_id = AsyncMock(return_value=existing_user_data)
        user_repo.create_user.return_value = None

        # Выполняем тест
        profile = await user_service.get_or_create_user(123456789, 'test_user', 'Test', 'User')

        # Проверяем результат
        assert isinstance(profile, UserProfile)
        assert profile.user_id == 123456789
        assert profile.username == 'test_user'
        assert profile.first_name == 'Test'
        assert profile.reputation == 100
        assert profile.rank == 'Активист'

        # Проверяем, что репозиторий был вызван корректно (должен быть вызван 2 раза: один раз в начале, второй в _update_user_data)
        assert user_repo.get_by_id_async.call_count == 1
        assert user_repo.get_by_id.call_count == 1
        user_repo.get_by_id_async.assert_any_call(123456789)

    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self, user_service, user_repo, score_repo):
        """Тест создания нового пользователя"""
        # Мокируем отсутствие существующего пользователя
        # Мокируем создание пользователя
        new_user_data = {
            'id': 123456789,
            'telegram_id': 123456789,
            'username': 'new_user',
            'first_name': 'New',
            'last_name': 'User'
        }

        # Настраиваем мок так, чтобы первый вызов возвращал None, а второй - данные пользователя
        user_repo.get_by_id_async = AsyncMock(side_effect=[None, new_user_data])
        user_repo.get_by_id = AsyncMock(return_value=new_user_data)
        user_repo.create_user = AsyncMock(return_value=new_user_data)
        user_repo._execute_query_async = AsyncMock(return_value=True)

        # Выполняем тест
        profile = await user_service.get_or_create_user(123456789, 'new_user', 'New', 'User')

        # Проверяем результат
        assert isinstance(profile, UserProfile)
        assert profile.user_id == 123456789
        assert profile.username == 'new_user'

        # Проверяем вызовы методов (get_by_id_async должен быть вызван 1 раз, get_by_id 1 раз)
        assert user_repo.get_by_id_async.call_count == 1
        assert user_repo.get_by_id.call_count == 1
        user_repo.get_by_id_async.assert_any_call(123456789)
        user_repo._execute_query_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_activity(self, user_service, user_repo, score_repo):
        """Тест обновления активности пользователя"""
        # Мокируем обновление активности
        activity_data = {'updated': True}
        user_repo.update_activity.return_value = activity_data
        score_repo.update_score.return_value = True

        # Выполняем тест
        result = await user_service.update_user_activity(123456789, -1001234567890)

        # Проверяем результат
        assert result['activity_updated'] is True
        assert result['rank_promoted'] is False  # По умолчанию

        # Проверяем вызовы
        user_repo.update_activity.assert_called_once_with(123456789, -1001234567890)
        score_repo.update_score.assert_called_once_with(123456789, 1)

    def test_calculate_rank(self, user_service):
        """Тест расчета ранга пользователя"""
        # Тестируем различные пороги рангов
        assert user_service.calculate_rank(50) == "Новичок"
        assert user_service.calculate_rank(150) == "Ученик"
        assert user_service.calculate_rank(750) == "Активист"
        assert user_service.calculate_rank(1500) == "Знаток"
        assert user_service.calculate_rank(3000) == "Эксперт"

    def test_get_rank_progress(self, user_service):
        """Тест получения прогресса до следующего ранга"""
        progress = user_service.get_rank_progress(150)

        assert progress['current_rank'] == "Ученик"
        assert progress['next_rank'] == "Активист"
        assert progress['current_score'] == 150
        assert 'percentage' in progress
        assert isinstance(progress['percentage'], float)

    @pytest.mark.asyncio
    async def test_add_warning(self, user_service, user_repo):
        """Тест добавления предупреждения"""
        user_repo.add_warning.return_value = True

        result = await user_service.add_warning(123456789, "Нарушение правил", 987654321)

        assert result is True
        user_repo.add_warning.assert_called_once_with(123456789, "Нарушение правил", 987654321)

    @pytest.mark.asyncio
    async def test_get_top_users(self, user_service, user_repo):
        """Тест получения топ пользователей"""
        top_users = [
            (111, "user1", "User One", 100),
            (222, "user2", "User Two", 90)
        ]
        user_repo.get_top_users_async.return_value = top_users

        result = await user_service.get_top_users(5)

        assert result == top_users
        user_repo.get_top_users_async.assert_called_once_with(5)

    def test_calculate_rank_edge_cases(self, user_service):
        """Тест расчета ранга в краевых случаях"""
        # Минимальное значение
        assert user_service.calculate_rank(0) == "Новичок"
        assert user_service.calculate_rank(-100) == "Новичок"

        # Максимальное значение
        assert user_service.calculate_rank(999999999) == "Император"

    def test_get_rank_progress_max_rank(self, user_service):
        """Тест прогресса для максимального ранга"""
        progress = user_service.get_rank_progress(300000)  # Император

        assert progress['current_rank'] == "Император"
        assert progress['next_rank'] == "Император"
        assert progress['percentage'] == 100

    @pytest.mark.asyncio
    async def test_add_donation_success(self, user_service, user_repo, score_repo):
        """Тест успешного добавления доната"""
        # Мокируем пользователя
        user_profile = UserProfile(
            user_id=123456789,
            first_name="Test",
            last_name="User",
            username="test_user"
        )

        # Мокируем методы
        user_service.get_or_create_user = AsyncMock(return_value=user_profile)
        user_service.check_and_unlock_achievements = AsyncMock(return_value=[])
        user_repo.add_donation = AsyncMock(return_value=True)
        score_repo.update_score.return_value = True

        # Выполняем тест
        result = await user_service.add_donation(123456789, 500.0)

        # Проверяем результат
        assert result is True

        # Проверяем вызовы транзакций
        user_repo.begin_transaction.assert_called_once()
        score_repo.begin_transaction.assert_called_once()
        user_repo.commit_transaction.assert_called_once()
        score_repo.commit_transaction.assert_called_once()
        user_repo.rollback_transaction.assert_not_called()
        score_repo.rollback_transaction.assert_not_called()

        # Проверяем бизнес-логику
        user_repo.add_donation.assert_called_once_with(123456789, 500.0, 2025)  # текущий год
        score_repo.update_score.assert_called_once_with(123456789, 5)  # 500 // 100 = 5

    @pytest.mark.asyncio
    async def test_add_donation_failure_rollback(self, user_service, user_repo, score_repo):
        """Тест отката транзакции при ошибке"""
        # Мокируем пользователя
        user_profile = UserProfile(
            user_id=123456789,
            first_name="Test",
            last_name="User",
            username="test_user"
        )

        # Мокируем методы - донат не добавляется
        user_service.get_or_create_user = AsyncMock(return_value=user_profile)
        user_repo.add_donation.return_value = False

        # Выполняем тест
        result = await user_service.add_donation(123456789, 500.0)

        # Проверяем результат
        assert result is False

        # Проверяем вызовы транзакций
        user_repo.begin_transaction.assert_called_once()
        score_repo.begin_transaction.assert_called_once()
        user_repo.rollback_transaction.assert_called_once()
        score_repo.rollback_transaction.assert_called_once()
        user_repo.commit_transaction.assert_not_called()
        score_repo.commit_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_donation_exception_rollback(self, user_service, user_repo, score_repo):
        """Тест отката транзакции при исключении"""
        # Мокируем пользователя
        user_profile = UserProfile(
            user_id=123456789,
            first_name="Test",
            last_name="User",
            username="test_user"
        )

        # Мокируем методы - исключение при обновлении очков
        user_service.get_or_create_user = AsyncMock(return_value=user_profile)
        user_repo.add_donation.return_value = True
        score_repo.update_score.side_effect = Exception("Database error")

        # Выполняем тест
        result = await user_service.add_donation(123456789, 500.0)

        # Проверяем результат
        assert result is False

        # Проверяем вызовы транзакций
        user_repo.begin_transaction.assert_called_once()
        score_repo.begin_transaction.assert_called_once()
        user_repo.rollback_transaction.assert_called_once()
        score_repo.rollback_transaction.assert_called_once()
        user_repo.commit_transaction.assert_not_called()
        score_repo.commit_transaction.assert_not_called()

        progress = user_service.get_rank_progress(300000)  # Император

        assert progress['current_rank'] == "Император"
        assert progress['next_rank'] == "Император"
        assert progress['percentage'] == 100


class TestUserProfile:
    """Тесты профиля пользователя"""

    def test_user_profile_creation(self):
        """Тест создания профиля пользователя"""
        profile = UserProfile(
            user_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            reputation=150,
            rank="Активист"
        )

        assert profile.user_id == 123456789
        assert profile.username == "test_user"
        assert profile.first_name == "Test"
        assert profile.reputation == 150
        assert profile.rank == "Активист"
        assert profile.achievements == []

    def test_user_profile_defaults(self):
        """Тест значений по умолчанию профиля пользователя"""
        profile = UserProfile(
            user_id=123456789,
            first_name="Test",
            username=None,
            last_name=None
        )

        assert profile.username is None
        assert profile.last_name is None
        assert profile.reputation == 0
        assert profile.rank == "Новичок"
        assert profile.message_count == 0
        assert profile.warnings == 0
        assert profile.achievements == []
        assert isinstance(profile.joined_date, datetime)
        assert isinstance(profile.last_activity, datetime)
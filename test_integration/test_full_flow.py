"""
Интеграционные тесты для полного потока работы бота.
Проверяет взаимодействие между всеми компонентами системы.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.application import Application
from core.config import Config
from database.models import User, Score, Error
from services.user_service import UserService
from handlers.user_handlers import UserHandlers
from utils.validators import InputValidator


class TestFullFlowIntegration:
    """Интеграционные тесты полного потока"""

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
        """Временная база данных для тестов"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        yield db_path

        # Очистка
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_config_initialization(self, temp_config):
        """Тест инициализации конфигурации"""
        config = Config(temp_config)

        assert config.bot_config.token == "123456789:integration_test_token"
        assert 123456789 in config.bot_config.admin_ids
        assert 987654321 in config.bot_config.admin_ids
        assert config.api_keys.openweather == "test_key"

    @pytest.mark.asyncio
    async def test_user_service_integration(self, temp_db):
        """Тест интеграции сервиса пользователей с базой данных"""
        from database.repository import UserRepository, ScoreRepository

        # Создаем репозитории
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        # Создаем сервис
        user_service = UserService(user_repo, score_repo)

        # Тестируем создание пользователя
        profile = await user_service.get_or_create_user(
            123456789, "test_user", "Test", "User"
        )

        assert profile.user_id == 123456789
        assert profile.username == "test_user"
        assert profile.first_name == "Test"
        assert profile.rank == "Новичок"

        # Тестируем получение существующего пользователя
        profile2 = await user_service.get_or_create_user(
            123456789, "test_user", "Test", "User"
        )

        assert profile2.user_id == 123456789
        assert profile2.username == "test_user"

        # Закрываем соединения
        user_repo.close()
        score_repo.close()

    @pytest.mark.asyncio
    async def test_donation_full_flow_integration(self, temp_db):
        """Интеграционный тест полного цикла донатов - создание пользователя, донат, очки, достижения"""
        from database.repository import UserRepository, ScoreRepository
        from services.user_service import UserService

        # Создаем репозитории
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        # Инициализируем достижения
        user_repo.initialize_achievements()

        # Создаем сервис
        user_service = UserService(user_repo, score_repo)

        # Шаг 1: Создание пользователя
        user_id = 987654321
        # Создаем пользователя напрямую через репозиторий
        user_data = {
            'telegram_id': user_id,
            'username': "donator_user",
            'first_name': "Donator",
            'last_name': "Test",
            'joined_date': datetime.now(),
            'last_activity': datetime.now()
        }
        created_user = user_repo.create_user(user_data)
        profile = user_service._map_to_profile(created_user)

        assert profile.user_id == 1  # Внутренний ID в БД
        assert profile.username == "donator_user"
        assert profile.first_name == "Donator"
        assert profile.rank == "Новичок"
        assert profile.reputation == 0

        # Проверяем начальные очки
        initial_score = score_repo.get_total_score(user_id)
        assert initial_score == 0

        # Шаг 2: Добавление доната (500 рублей = 5 очков)
        donation_amount = 500.0
        success = await user_service.add_donation(user_id, donation_amount)

        assert success is True

        # Шаг 3: Проверка начисления очков
        updated_score = score_repo.get_total_score(user_id)
        expected_points = int(donation_amount // 100)  # 5 очков
        assert updated_score == expected_points

        # Шаг 4: Проверка обновления профиля пользователя
        # Получаем напрямую из репозитория
        user_data_direct = user_repo.get_by_id(user_id)
        updated_profile = user_service._map_to_profile(user_data_direct)

        assert updated_profile.reputation == expected_points

        # Проверяем ранг (должен остаться Новичок при 5 очках)
        assert updated_profile.rank == "Новичок"

        # Шаг 5: Проверка достижений
        # Получаем достижения через репозиторий
        achievement_badges = user_repo.get_user_achievements(user_id)
        achievement_names = []
        for badge, unlocked_at in achievement_badges:
            # Находим имя достижения по badge
            achievements = user_repo.get_all_achievements()
            for achievement in achievements:
                if achievement['badge'] == badge:
                    achievement_names.append(achievement['name'])
                    break

        assert "Первый донат" in achievement_names

        # Шаг 6: Второй донат для проверки накопления
        second_donation = 300.0
        success2 = await user_service.add_donation(user_id, second_donation)

        assert success2 is True

        # Проверяем итоговые очки (5 + 3 = 8)
        final_score = score_repo.get_total_score(user_id)
        assert final_score == 8

        # Проверяем общую сумму донатов
        total_donations = user_repo.get_total_donations(user_id, 2025)
        assert total_donations == 800.0  # 500 + 300

        # Шаг 7: Добавление большого доната для достижения "Меценат"
        big_donation = 1000.0
        success3 = await user_service.add_donation(user_id, big_donation)

        assert success3 is True

        # Проверяем итоговые очки (8 + 10 = 18)
        final_score_after_big = score_repo.get_total_score(user_id)
        assert final_score_after_big == 18

        # Проверяем достижения - должно появиться "Меценат"
        final_achievement_badges = user_repo.get_user_achievements(user_id)
        final_achievement_names = []
        for badge, unlocked_at in final_achievement_badges:
            achievements = user_repo.get_all_achievements()
            for achievement in achievements:
                if achievement['badge'] == badge:
                    final_achievement_names.append(achievement['name'])
                    break

        assert "Первый донат" in final_achievement_names
        assert "Меценат" in final_achievement_names

        # Закрываем соединения
        user_repo.close()
        score_repo.close()

    def test_validator_integration(self):
        """Тест интеграции валидаторов с другими компонентами"""
        # Тест цепочки валидации
        assert InputValidator.validate_user_id("123456789") is True
        assert InputValidator.validate_username("test_user") is True
        assert InputValidator.validate_email("test@example.com") is True

        # Тест комбинированной валидации
        user_data = {
            'id': "123456789",
            'username': "test_user",
            'email': "test@example.com"
        }

        # Валидация всех полей
        assert InputValidator.validate_user_id(user_data['id']) is True
        assert InputValidator.validate_username(user_data['username']) is True
        assert InputValidator.validate_email(user_data['email']) is True

    @pytest.mark.asyncio
    async def test_handler_service_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест интеграции обработчиков с сервисами"""
        from database.repository import UserRepository, ScoreRepository

        # Создаем компоненты
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)

        # Создаем обработчик
        handler = UserHandlers(config, config, user_service)

        # Мокируем успешное создание пользователя
        profile = UserProfile(
            user_id=123456789,
            username="test_user",
            first_name="Test",
            reputation=100,
            rank="Активист"
        )
        user_service.get_or_create_user = AsyncMock(return_value=profile)

        # Мокируем ответ бота
        mock_update.message.reply_text = AsyncMock()

        # Тестируем обработку команды /start
        await handler.handle_start(mock_update, mock_context)

        # Проверяем, что пользователь был получен/создан
        user_service.get_or_create_user.assert_called_once()

        # Проверяем, что ответ был отправлен
        mock_update.message.reply_text.assert_called_once()

        # Закрываем соединения
        user_repo.close()
        score_repo.close()

    def test_exception_handling_integration(self):
        """Тест интеграции системы исключений"""
        from core.exceptions import ValidationError, DatabaseError, PermissionError

        # Тест цепочки обработки ошибок
        try:
            raise ValidationError("Ошибка валидации", "email")
        except Exception as e:
            assert isinstance(e, ValidationError)
            assert e.error_code == "VALIDATION_ERROR"
            assert e.field == "email"

        # Тест наследования
        assert issubclass(ValidationError, Exception)
        assert issubclass(DatabaseError, Exception)
        assert issubclass(PermissionError, Exception)


class TestComponentInteraction:
    """Тесты взаимодействия компонентов"""

    def test_config_and_validators_integration(self, temp_config):
        """Тест интеграции конфигурации с валидаторами"""
        config = Config(temp_config)

        # Используем данные из конфигурации для валидации
        admin_ids = config.bot_config.admin_ids

        for admin_id in admin_ids:
            assert InputValidator.validate_user_id(str(admin_id)) is True

    def test_formatters_and_models_integration(self):
        """Тест интеграции форматтеров с моделями данных"""
        from utils.formatters import MessageFormatter

        # Создаем тестовые данные модели
        user_data = {
            'id': 123456789,
            'name': 'Test User',
            'username': 'test_user',
            'reputation': 150,
            'rank': 'Активист',
            'message_count': 45,
            'joined_date': datetime.now().strftime('%Y-%m-%d')
        }

        # Тестируем форматирование
        formatted = MessageFormatter.format_user_info(user_data)

        assert "👤 <b>Информация о пользователе:</b>" in formatted
        assert "🆔 ID: 123456789" in formatted
        assert "🏆 Репутация: 150" in formatted

    def test_helpers_and_validators_integration(self):
        """Тест интеграции хелперов с валидаторами"""
        from utils.helpers import generate_user_mention, clean_string

        # Тестируем комбинированное использование
        user_id = 123456789
        name = "Test   User"  # С лишними пробелами

        # Очищаем имя и генерируем упоминание
        clean_name = clean_string(name)
        mention = generate_user_mention(user_id, clean_name)

        assert mention == "[Test User](tg://user?id=123456789)"

        # Проверяем, что ID валиден
        assert InputValidator.validate_user_id(str(user_id)) is True


class TestErrorHandlingFlow:
    """Тесты потока обработки ошибок"""

    @pytest.mark.asyncio
    async def test_error_handling_in_handlers(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок в обработчиках"""
        from database.repository import UserRepository, ScoreRepository
        from core.exceptions import ValidationError

        # Создаем компоненты
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        handler = UserHandlers(config, config, user_service)

        # Мокируем ошибку в сервисе
        async def failing_service(*args, **kwargs):
            raise ValidationError("Ошибка валидации данных пользователя")

        user_service.get_or_create_user = failing_service
        mock_update.message.reply_text = AsyncMock()

        # Тестируем обработку команды с ошибкой
        await handler.handle_start(mock_update, mock_context)

        # Проверяем, что сообщение об ошибке было отправлено
        mock_update.message.reply_text.assert_called_once()
        error_message = mock_update.message.reply_text.call_args[0][0]
        assert "⚠️ Ошибка валидации данных пользователя" in error_message

        # Закрываем соединения
        user_repo.close()
        score_repo.close()

    def test_error_propagation_through_layers(self):
        """Тест распространения ошибок через слои архитектуры"""
        from core.exceptions import DatabaseError, ValidationError

        # Тест, что ошибки правильно распространяются
        try:
            raise ValidationError("Ошибка валидации")
        except ValidationError as e:
            # Ошибка должна сохранять свою информацию
            assert e.error_code == "VALIDATION_ERROR"
            assert "Ошибка валидации" in str(e)

        # Тест преобразования ошибок
        original_error = ValueError("Базовая ошибка")
        db_error = DatabaseError("Ошибка базы данных", original_error)

        assert db_error.original_error == original_error
        assert db_error.error_code == "DATABASE_ERROR"


class TestPerformanceIntegration:
    """Тесты производительности интеграции"""

    def test_config_loading_performance(self, temp_config):
        """Тест производительности загрузки конфигурации"""
        import time

        start_time = time.time()

        # Загружаем конфигурацию несколько раз
        for _ in range(100):
            config = Config(temp_config)

        end_time = time.time()
        total_time = end_time - start_time

        # Должно быть быстро (менее 1 секунды для 100 загрузок)
        assert total_time < 1.0

    def test_validator_performance(self):
        """Тест производительности валидаторов"""
        import time

        test_data = [
            ("123456789", "user123", "test@example.com"),
            ("987654321", "test_user", "admin@test.com"),
            ("555666777", "another_user", "user@domain.org")
        ] * 50  # Увеличиваем объем для тестирования

        start_time = time.time()

        for user_id, username, email in test_data:
            InputValidator.validate_user_id(user_id)
            InputValidator.validate_username(username)
            InputValidator.validate_email(email)

        end_time = time.time()
        total_time = end_time - start_time

        # Должно быть быстро даже для большого количества данных
        assert total_time < 0.5


class TestDataConsistencyIntegration:
    """Тесты согласованности данных"""

    @pytest.mark.asyncio
    async def test_user_data_consistency(self, temp_db):
        """Тест согласованности данных пользователя"""
        from database.repository import UserRepository, ScoreRepository

        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)

        # Создаем пользователя
        profile1 = await user_service.get_or_create_user(
            123456789, "test_user", "Test", "User"
        )

        # Получаем пользователя снова
        profile2 = await user_service.get_or_create_user(
            123456789, "test_user", "Test", "User"
        )

        # Данные должны быть согласованными
        assert profile1.user_id == profile2.user_id
        assert profile1.username == profile2.username
        assert profile1.reputation == profile2.reputation

        user_repo.close()
        score_repo.close()

    def test_formatter_data_consistency(self):
        """Тест согласованности данных в форматтерах"""
        from utils.formatters import MessageFormatter

        # Тестовые данные пользователя
        user_data = {
            'id': 123456789,
            'name': 'Test User',
            'username': 'test_user',
            'reputation': 150,
            'rank': 'Активист',
            'message_count': 45,
            'joined_date': '2024-01-15'
        }

        # Форматируем данные
        formatted = MessageFormatter.format_user_info(user_data)

        # Проверяем, что все поля присутствуют в форматированном выводе
        assert str(user_data['id']) in formatted
        assert user_data['name'] in formatted
        assert user_data['username'] in formatted
        assert str(user_data['reputation']) in formatted
        assert user_data['rank'] in formatted
        assert str(user_data['message_count']) in formatted
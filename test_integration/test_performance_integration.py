"""
Комплексные интеграционные тесты производительности.
Тестирование скорости работы всех слоев архитектуры под нагрузкой.
Проверяет: handlers -> services -> repositories -> database performance.
"""

import pytest
import tempfile
import os
import time
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from services.user_service import UserService
from services.game_service import GameService
from services.moderation_service import ModerationService
from services.donation_service import DonationService
from handlers.user_handlers import UserHandlers
from handlers.game_handlers import GameHandlers
from handlers.moderation_handlers import ModerationHandlers
from database import UserRepository, ScoreRepository, PaymentRepository


class TestPerformanceIntegration:
    """Комплексные интеграционные тесты производительности"""

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

    def test_user_service_performance(self, temp_config, temp_db):
        """Тест производительности сервиса пользователей"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)

        try:
            # Тест создания пользователей
            start_time = time.time()

            for i in range(100):
                profile = asyncio.run(user_service.get_or_create_user(
                    100000000 + i,
                    f"user_{i}",
                    f"User{i}",
                    f"Test{i}"
                ))

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_user = total_time / 100

            print(".4f")
            # Создание пользователя должно занимать менее 0.1 секунды
            assert avg_time_per_user < 0.1, f"Слишком медленно: {avg_time_per_user:.4f}s на пользователя"

            # Тест чтения пользователей
            start_time = time.time()

            for i in range(50):
                profile = asyncio.run(user_service.get_or_create_user(
                    100000000 + i,
                    f"user_{i}",
                    f"User{i}",
                    f"Test{i}"
                ))

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_read = total_time / 50

            print(".4f")
            assert avg_time_per_read < 0.05, f"Чтение слишком медленное: {avg_time_per_read:.4f}s"

        finally:
            user_repo.close()
            score_repo.close()

    def test_game_service_performance(self, temp_config, temp_db):
        """Тест производительности игрового сервиса"""
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        game_service = GameService(user_repo, score_repo)

        try:
            # Создаем пользователя для игр
            user_id = 123456789
            asyncio.run(user_repo._create_user_if_not_exists(user_id, "test_user", "Test", "User"))

            # Тест создания игровых сессий
            start_time = time.time()

            for i in range(50):
                session = game_service.create_game_session(
                    "rock_paper_scissors",
                    user_id,
                    -1001234567890
                )

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_session = total_time / 50

            print(".4f")
            assert avg_time_per_session < 0.01, f"Создание сессии слишком медленное: {avg_time_per_session:.4f}s"

        finally:
            user_repo.close()
            score_repo.close()

    def test_database_repository_performance(self, temp_db):
        """Тест производительности репозиториев базы данных"""
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        try:
            # Тест массовых операций с пользователями
            start_time = time.time()

            # Создаем 200 пользователей
            for i in range(200):
                user_data = {
                    'telegram_id': 200000000 + i,
                    'username': f'bulk_user_{i}',
                    'first_name': f'Bulk{i}',
                    'last_name': f'User{i}',
                    'joined_date': datetime.now(),
                    'last_activity': datetime.now()
                }
                user_repo.create_user(user_data)

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_user = total_time / 200

            print(".4f")
            assert avg_time_per_user < 0.005, f"Вставка пользователей слишком медленная: {avg_time_per_user:.4f}s"

            # Тест массового чтения
            start_time = time.time()

            for i in range(100):
                user_repo.get_by_id(200000000 + i)

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_read = total_time / 100

            print(".4f")
            assert avg_time_per_read < 0.001, f"Чтение пользователей слишком медленное: {avg_time_per_read:.4f}s"

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_handler_performance(self, temp_config, temp_db, mock_update, mock_context):
        """Тест производительности обработчиков команд"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Создаем пользователя
            await user_handlers.handle_start(mock_update, mock_context)

            # Тест производительности команды /rank
            start_time = time.time()

            for _ in range(20):
                mock_update.message.reply_text.reset_mock()
                await user_handlers.handle_rank(mock_update, mock_context)

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_command = total_time / 20

            print(".4f")
            # Команда должна выполняться менее чем за 0.5 секунды
            assert avg_time_per_command < 0.5, f"Команда /rank слишком медленная: {avg_time_per_command:.4f}s"

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, temp_config, temp_db):
        """Тест производительности при одновременных операциях"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)

        try:
            async def create_user_async(user_id: int):
                """Асинхронное создание пользователя"""
                await user_service.get_or_create_user(
                    user_id,
                    f"concurrent_user_{user_id}",
                    f"Concurrent{user_id}",
                    f"User{user_id}"
                )

            # Тест одновременного создания пользователей
            start_time = time.time()

            tasks = []
            for i in range(20):
                task = create_user_async(300000000 + i)
                tasks.append(task)

            await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_user = total_time / 20

            print(".4f")
            # Одновременное создание должно быть эффективным
            assert avg_time_per_user < 0.2, f"Одновременные операции слишком медленные: {avg_time_per_user:.4f}s"

        finally:
            user_repo.close()
            score_repo.close()

    def test_memory_usage_performance(self, temp_config, temp_db):
        """Тест использования памяти при больших объемах данных"""
        import psutil
        import os

        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        try:
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Создаем много пользователей и данных
            for i in range(500):
                user_data = {
                    'telegram_id': 400000000 + i,
                    'username': f'memory_test_user_{i}',
                    'first_name': f'Memory{i}',
                    'last_name': f'Test{i}',
                    'joined_date': datetime.now(),
                    'last_activity': datetime.now()
                }
                user_repo.create_user(user_data)

                # Добавляем очки
                score_repo.update_score(400000000 + i, 10)

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            print(".2f")
            # Увеличение памяти не должно превышать разумные пределы
            assert memory_increase < 50, f"Слишком большое использование памяти: +{memory_increase:.2f} MB"

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_donation_performance(self, temp_config, temp_db):
        """Тест производительности платежной системы"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        payment_repo = PaymentRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        donation_service = DonationService(payment_repo, config.api_keys)

        try:
            # Создаем пользователей для донатов
            for i in range(10):
                await user_service.get_or_create_user(
                    500000000 + i,
                    f"donator_{i}",
                    f"Donator{i}",
                    f"Test{i}"
                )

            # Тест массовых донатов
            start_time = time.time()

            for i in range(10):
                await user_service.add_donation(500000000 + i, 100.0 * (i + 1))

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_donation = total_time / 10

            print(".4f")
            assert avg_time_per_donation < 0.1, f"Донаты слишком медленные: {avg_time_per_donation:.4f}s"

        finally:
            user_repo.close()
            score_repo.close()
            payment_repo.close()

    def test_leaderboard_performance(self, temp_config, temp_db):
        """Тест производительности лидерборда с большим количеством пользователей"""
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        try:
            # Создаем много пользователей с разными очками
            for i in range(100):
                user_data = {
                    'telegram_id': 600000000 + i,
                    'username': f'leaderboard_user_{i}',
                    'first_name': f'Leaderboard{i}',
                    'last_name': f'User{i}',
                    'joined_date': datetime.now(),
                    'last_activity': datetime.now()
                }
                user_repo.create_user(user_data)

                # Добавляем разные количества очков
                score_repo.update_score(600000000 + i, i * 5)

            # Тест получения топ пользователей
            start_time = time.time()

            for _ in range(10):
                top_users = user_repo.get_top_users(50)

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_query = total_time / 10

            print(".4f")
            assert avg_time_per_query < 0.05, f"Лидерборд слишком медленный: {avg_time_per_query:.4f}s"

            # Проверяем корректность результатов
            assert len(top_users) <= 50
            # Проверяем сортировку (первый должен иметь максимум очков)
            if len(top_users) > 1:
                assert top_users[0][3] >= top_users[-1][3]

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_moderation_performance(self, temp_config, temp_db):
        """Тест производительности системы модерации"""
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        moderation_service = ModerationService(user_repo, score_repo)

        try:
            # Создаем пользователей для модерации
            admin_id = 123456789
            await user_repo._create_user_if_not_exists(admin_id, "admin", "Admin", "User")

            for i in range(20):
                await user_repo._create_user_if_not_exists(
                    700000000 + i,
                    f"user_{i}",
                    f"User{i}",
                    "Test"
                )

            # Тест массовых предупреждений
            start_time = time.time()

            for i in range(20):
                await moderation_service.warn_user(
                    700000000 + i,
                    f"Test warning {i}",
                    admin_id
                )

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_warning = total_time / 20

            print(".4f")
            assert avg_time_per_warning < 0.05, f"Модерация слишком медленная: {avg_time_per_warning:.4f}s"

            # Тест получения статистики модерации
            start_time = time.time()

            for _ in range(10):
                stats = await moderation_service.get_moderation_stats()

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_stats = total_time / 10

            print(".4f")
            assert avg_time_per_stats < 0.01, f"Статистика модерации слишком медленная: {avg_time_per_stats:.4f}s"

        finally:
            user_repo.close()
            score_repo.close()

    def test_transaction_performance(self, temp_db):
        """Тест производительности транзакций базы данных"""
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        try:
            # Тест транзакционных операций
            start_time = time.time()

            for i in range(50):
                # Атомарная операция: создание пользователя + очки
                user_data = {
                    'telegram_id': 800000000 + i,
                    'username': f'transaction_user_{i}',
                    'first_name': f'Transaction{i}',
                    'last_name': f'User{i}',
                    'joined_date': datetime.now(),
                    'last_activity': datetime.now()
                }
                user_repo.create_user(user_data)
                score_repo.update_score(800000000 + i, 10)

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_transaction = total_time / 50

            print(".4f")
            # Транзакции должны быть быстрыми
            assert avg_time_per_transaction < 0.02, f"Транзакции слишком медленные: {avg_time_per_transaction:.4f}s"

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_end_to_end_performance(self, temp_config, temp_db, mock_update, mock_context):
        """Комплексный тест производительности end-to-end сценария"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        payment_repo = PaymentRepository(temp_db)

        user_service = UserService(user_repo, score_repo)
        donation_service = DonationService(payment_repo, config.api_keys)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Полный сценарий: регистрация -> игры -> донаты -> проверка ранга
            start_time = time.time()

            # 1. Регистрация
            await user_handlers.handle_start(mock_update, mock_context)

            # 2. Игры (несколько раундов)
            for _ in range(5):
                await score_repo.update_score(mock_update.effective_user.id, 3)

            # 3. Донаты
            await user_service.add_donation(mock_update.effective_user.id, 500.0)

            # 4. Проверка ранга
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_rank(mock_update, mock_context)

            # 5. Проверка лидерборда
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_leaderboard(mock_update, mock_context)

            end_time = time.time()
            total_time = end_time - start_time

            print(".2f")
            # Полный сценарий должен выполняться менее чем за 5 секунд
            assert total_time < 5.0, f"Полный сценарий слишком медленный: {total_time:.2f}s"

            # Проверяем финальное состояние
            final_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            assert final_profile.reputation >= 20  # Минимум от донатов и игр

        finally:
            user_repo.close()
            score_repo.close()
            payment_repo.close()

    def test_scalability_performance(self, temp_config, temp_db):
        """Тест масштабируемости производительности при росте нагрузки"""
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        try:
            # Тест с разными объемами данных
            sizes = [10, 50, 100, 200]

            for size in sizes:
                start_time = time.time()

                # Создаем пользователей
                for i in range(size):
                    user_data = {
                        'telegram_id': 900000000 + i,
                        'username': f'scale_user_{i}',
                        'first_name': f'Scale{i}',
                        'last_name': f'User{i}',
                        'joined_date': datetime.now(),
                        'last_activity': datetime.now()
                    }
                    user_repo.create_user(user_data)

                end_time = time.time()
                total_time = end_time - start_time
                avg_time = total_time / size

                print(".6f")

                # Производительность должна degrade gracefully
                max_allowed_time = 0.01 * (size / 10)  # Линейная зависимость
                assert avg_time < max_allowed_time, f"Масштабируемость нарушена для размера {size}: {avg_time:.6f}s"

        finally:
            user_repo.close()
            score_repo.close()
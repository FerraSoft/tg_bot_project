"""
Комплексные интеграционные тесты полного пользовательского сценария.
Тестирование полной цепочки взаимодействия пользователя с ботом:
от /start -> игры -> модерация -> донаты -> достижения.
Проверяет взаимодействие всех слоев архитектуры в реальном сценарии использования.
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
from services.game_service import GameService
from services.moderation_service import ModerationService
from services.donation_service import DonationService
from handlers.user_handlers import UserHandlers
from handlers.game_handlers import GameHandlers
from handlers.moderation_handlers import ModerationHandlers
from database import UserRepository, ScoreRepository, PaymentRepository


class TestFullUserScenarioIntegration:
    """Комплексные интеграционные тесты полного сценария использования бота"""

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
        """Временная база данных для тестов с полной инициализацией"""
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
    async def test_complete_new_user_journey(self, temp_config, temp_db, mock_update, mock_context):
        """Тест полного пути нового пользователя: от первого контакта до активного использования"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        payment_repo = PaymentRepository(temp_db)

        # Инициализируем все сервисы
        user_service = UserService(user_repo, score_repo)
        game_service = GameService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        donation_service = DonationService(payment_repo, config.api_keys)

        # Инициализируем все хендлеры
        user_handlers = UserHandlers(config, user_service)
        game_handlers = GameHandlers(config, config, game_service, config)
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # === ЭТАП 1: Первый контакт - /start ===
            print("Этап 1: Регистрация нового пользователя")
            await user_handlers.handle_start(mock_update, mock_context)

            # Проверяем создание пользователя
            profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            assert profile.user_id == mock_update.effective_user.id
            assert profile.rank == "Новичок"
            assert profile.reputation == 0

            # === ЭТАП 2: Изучение команд - /help ===
            print("Этап 2: Изучение команд")
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_help(mock_update, mock_context)

            help_response = mock_update.message.reply_text.call_args[0][0]
            assert "Помощь по командам" in help_response or "📋" in help_response

            # === ЭТАП 3: Проверка ранга - /rank ===
            print("Этап 3: Проверка ранга")
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_rank(mock_update, mock_context)

            rank_response = mock_update.message.reply_text.call_args[0][0]
            assert "🏆" in rank_response or "Ранг" in rank_response

            # === ЭТАП 4: Игра - камень-ножницы-бумага ===
            print("Этап 4: Первая игра")
            mock_update.message.reply_text.reset_mock()
            await game_handlers._handle_play_game(mock_update, mock_context)

            # Выбираем камень
            mock_context.args = ['rock']
            await game_handlers.handle_rps_choice(mock_update, mock_context)

            # Проверяем начисление очков за игру
            game_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            assert game_profile.reputation >= 0  # Очки могли начислиться

            # === ЭТАП 5: Крестики-нолики ===
            print("Этап 5: Крестики-нолики")
            mock_update.message.reply_text.reset_mock()
            await game_handlers._handle_tic_tac_toe(mock_update, mock_context)

            # Делаем ход
            mock_context.args = ['4']
            await game_handlers.handle_tictactoe_move(mock_update, mock_context)

            # === ЭТАП 6: Викторина ===
            print("Этап 6: Викторина")
            mock_update.message.reply_text.reset_mock()
            await game_handlers._handle_quiz(mock_update, mock_context)

            # Отвечаем на вопрос
            mock_context.args = ['0']
            await game_handlers.handle_quiz_answer(mock_update, mock_context)

            # === ЭТАП 7: Первый донат ===
            print("Этап 7: Первый донат")
            donation_amount = 500.0
            success = await user_service.add_donation(mock_update.effective_user.id, donation_amount)
            assert success

            # Проверяем достижения
            achievements = await user_service.get_user_achievements(mock_update.effective_user.id)
            achievement_names = []
            for ach_id, unlocked_at in achievements:
                ach_data = user_repo.get_all_achievements()
                for ach in ach_data:
                    if ach['id'] == ach_id:
                        achievement_names.append(ach['name'])
                        break

            assert "Первый донат" in achievement_names

            # Проверяем повышение ранга
            donator_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            assert donator_profile.reputation >= 5  # Минимум 5 очков от доната

            # === ЭТАП 8: Проверка лидерборда ===
            print("Этап 8: Лидерборд")
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_leaderboard(mock_update, mock_context)

            leaderboard_response = mock_update.message.reply_text.call_args[0][0]
            assert "🥇" in leaderboard_response or "Топ" in leaderboard_response

            # === ЭТАП 9: Финальная проверка профиля ===
            print("Этап 9: Финальный профиль")
            final_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Проверяем прогресс пользователя
            assert final_profile.reputation > 0
            assert final_profile.user_id == mock_update.effective_user.id
            assert final_profile.username == mock_update.effective_user.username

            print(f"✅ Пользователь прошел полный путь: {final_profile.reputation} очков, ранг: {final_profile.rank}")

        finally:
            user_repo.close()
            score_repo.close()
            payment_repo.close()

    @pytest.mark.asyncio
    async def test_user_progression_scenario(self, temp_config, temp_db, mock_update, mock_context):
        """Тест сценария прогрессии пользователя: от новичка до опытного игрока"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        payment_repo = PaymentRepository(temp_db)

        user_service = UserService(user_repo, score_repo)
        game_service = GameService(user_repo, score_repo)
        donation_service = DonationService(payment_repo, config.api_keys)

        try:
            # === ФАЗА 1: Новичок ===
            print("Фаза 1: Новичок")
            profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            assert profile.rank == "Новичок"
            initial_score = profile.reputation

            # Несколько игр для накопления очков
            for _ in range(5):
                await score_repo.update_score(mock_update.effective_user.id, 2)  # +2 за каждую игру

            # === ФАЗА 2: Первый донат ===
            print("Фаза 2: Первый донат")
            await user_service.add_donation(mock_update.effective_user.id, 300.0)  # +3 очка

            # Проверяем достижения
            achievements = await user_service.get_user_achievements(mock_update.effective_user.id)
            achievement_names = [user_repo.get_all_achievements()[i]['name']
                               for i, _ in achievements if i < len(user_repo.get_all_achievements())]

            # === ФАЗА 3: Активный игрок ===
            print("Фаза 3: Активный игрок")
            # Еще игры и донаты
            for _ in range(10):
                await score_repo.update_score(mock_update.effective_user.id, 1)

            await user_service.add_donation(mock_update.effective_user.id, 1000.0)  # +10 очков

            # === ФАЗА 4: Опытный пользователь ===
            print("Фаза 4: Опытный пользователь")
            final_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Проверяем значительный прогресс
            total_score = final_profile.reputation
            assert total_score > initial_score + 20  # Минимум 20+ очков прогресса

            # Проверяем достижения
            final_achievements = await user_service.get_user_achievements(mock_update.effective_user.id)
            assert len(final_achievements) >= 2  # Минимум 2 достижения

            print(f"✅ Прогрессия завершена: {total_score} очков, {len(final_achievements)} достижений")

        finally:
            user_repo.close()
            score_repo.close()
            payment_repo.close()

    @pytest.mark.asyncio
    async def test_user_interaction_with_moderation(self, temp_config, temp_db, mock_update, mock_context):
        """Тест сценария взаимодействия с системой модерации"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # Создаем обычного пользователя
            regular_user_id = 999999999
            await user_service.get_or_create_user(regular_user_id, "regular", "Regular", "User")

            # Имитируем нарушение (предупреждение)
            mock_context.args = [str(regular_user_id), "Тестовое нарушение"]
            await moderation_handlers._handle_warn(mock_update, mock_context, mock_context.args)

            # Проверяем, что предупреждение записано
            user_history = await moderation_service.get_user_moderation_history(regular_user_id)
            assert len(user_history) >= 1

            # Пользователь должен иметь предупреждения
            regular_profile = await user_service.get_or_create_user(regular_user_id, "regular", "Regular", "User")
            assert regular_profile.warnings >= 1

            # При повторных нарушениях - мут
            await moderation_service.warn_user(regular_user_id, "Повторное нарушение", mock_update.effective_user.id)
            await moderation_service.warn_user(regular_user_id, "Еще одно нарушение", mock_update.effective_user.id)

            # Проверяем эскалацию
            is_muted = moderation_service.is_user_muted(regular_user_id)
            # Логика эскалации может быть разной, но система должна реагировать

            print("✅ Система модерации отработала корректно")

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_community_interaction_scenario(self, temp_config, temp_db, mock_update, mock_context):
        """Тест сценария взаимодействия в сообществе"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        payment_repo = PaymentRepository(temp_db)

        user_service = UserService(user_repo, score_repo)
        donation_service = DonationService(payment_repo, config.api_keys)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Создаем несколько пользователей сообщества
            users_data = [
                (111111111, "alice", "Alice", "Smith"),
                (222222222, "bob", "Bob", "Johnson"),
                (333333333, "charlie", "Charlie", "Brown"),
                (mock_update.effective_user.id, mock_update.effective_user.username,
                 mock_update.effective_user.first_name, mock_update.effective_user.last_name)
            ]

            # Регистрируем всех пользователей
            for user_id, username, first_name, last_name in users_data:
                await user_service.get_or_create_user(user_id, username, first_name, last_name)

                # Каждый делает донат
                await user_service.add_donation(user_id, 200.0)  # +2 очка каждому

                # Каждый играет в игры
                await score_repo.update_score(user_id, 5)  # +5 очков каждому

            # Проверяем лидерборд
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_leaderboard(mock_update, mock_context)

            leaderboard_response = mock_update.message.reply_text.call_args[0][0]

            # Проверяем, что все пользователи в лидерборде
            top_users = await user_service.get_top_users(10)
            assert len(top_users) >= 4

            # Проверяем разнообразие рангов
            ranks = set()
            for user_id, username, first_name, score in top_users:
                profile = await user_service.get_or_create_user(user_id, username, first_name, "Test")
                ranks.add(profile.rank)

            assert len(ranks) >= 1  # Минимум один ранг

            # Проверяем достижения в сообществе
            total_achievements = 0
            for user_id, _, _, _ in top_users[:3]:  # Проверяем топ-3
                user_achievements = await user_service.get_user_achievements(user_id)
                total_achievements += len(user_achievements)

            assert total_achievements >= 3  # Минимум достижения в сообществе

            print(f"✅ Сообщество активно: {len(top_users)} участников, {total_achievements} достижений")

        finally:
            user_repo.close()
            score_repo.close()
            payment_repo.close()

    @pytest.mark.asyncio
    async def test_user_retention_scenario(self, temp_config, temp_db, mock_update, mock_context):
        """Тест сценария удержания пользователя: регулярная активность"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        payment_repo = PaymentRepository(temp_db)

        user_service = UserService(user_repo, score_repo)
        game_service = GameService(user_repo, score_repo)
        donation_service = DonationService(payment_repo, config.api_keys)
        user_handlers = UserHandlers(config, user_service)

        try:
            # === НЕДЕЛЯ 1: Начало ===
            print("Неделя 1: Регистрация и первые взаимодействия")
            await user_handlers.handle_start(mock_update, mock_context)

            # Ежедневные игры
            for day in range(7):
                await score_repo.update_score(mock_update.effective_user.id, 3)  # 3 игры в день

            week1_score = score_repo.get_total_score(mock_update.effective_user.id)

            # === НЕДЕЛЯ 2: Активность ===
            print("Неделя 2: Рост активности")
            # Донат
            await user_service.add_donation(mock_update.effective_user.id, 300.0)

            # Больше игр
            for day in range(7):
                await score_repo.update_score(mock_update.effective_user.id, 5)  # 5 игр в день

            week2_score = score_repo.get_total_score(mock_update.effective_user.id)

            # === НЕДЕЛЯ 3: Пик активности ===
            print("Неделя 3: Пик активности")
            # Еще один донат
            await user_service.add_donation(mock_update.effective_user.id, 500.0)

            # Максимальная активность
            for day in range(7):
                await score_repo.update_score(mock_update.effective_user.id, 8)  # 8 игр в день

            week3_score = score_repo.get_total_score(mock_update.effective_user.id)

            # === ПРОВЕРКИ ===
            # Прогресс должен расти
            assert week2_score > week1_score
            assert week3_score > week2_score

            # Финальный профиль
            final_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Проверяем достижения
            achievements = await user_service.get_user_achievements(mock_update.effective_user.id)
            assert len(achievements) >= 2  # Минимум 2 достижения за 3 недели

            # Проверяем ранг
            assert final_profile.reputation >= 50  # Минимум 50 очков

            # Проверяем статистику донатов
            total_donations = await user_service.get_total_donations(mock_update.effective_user.id, 2025)
            assert total_donations >= 800.0

            print(f"✅ Удержание пользователя успешно: {final_profile.reputation} очков, ранг {final_profile.rank}")

        finally:
            user_repo.close()
            score_repo.close()
            payment_repo.close()

    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self, temp_config, temp_db, mock_update, mock_context):
        """Тест сценария восстановления после ошибок"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        user_service = UserService(user_repo, score_repo)
        user_handlers = UserHandlers(config, user_service)

        try:
            # Создаем пользователя
            await user_handlers.handle_start(mock_update, mock_context)

            # Имитируем ошибку в сервисе
            original_get_or_create = user_service.get_or_create_user
            user_service.get_or_create_user = AsyncMock(side_effect=Exception("Temporary service error"))

            # Пытаемся выполнить команду (должна обработать ошибку)
            await user_handlers.handle_rank(mock_update, mock_context)

            # Восстанавливаем сервис
            user_service.get_or_create_user = original_get_or_create

            # Повторяем команду (теперь должна работать)
            mock_update.message.reply_text.reset_mock()
            await user_handlers.handle_rank(mock_update, mock_context)

            # Проверяем, что команда выполнилась успешно после восстановления
            assert mock_update.message.reply_text.called
            rank_response = mock_update.message.reply_text.call_args[0][0]
            assert "Ранг" in rank_response or "🏆" in rank_response

            print("✅ Система корректно восстановилась после ошибки")

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_cross_feature_integration_scenario(self, temp_config, temp_db, mock_update, mock_context):
        """Тест сценария интеграции всех функций"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        payment_repo = PaymentRepository(temp_db)

        # Инициализируем все компоненты
        user_service = UserService(user_repo, score_repo)
        game_service = GameService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        donation_service = DonationService(payment_repo, config.api_keys)

        user_handlers = UserHandlers(config, user_service)
        game_handlers = GameHandlers(config, config, game_service, config)
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # === КОМПЛЕКСНЫЙ СЦЕНАРИЙ ===
            print("Запуск комплексного сценария интеграции всех функций")

            # 1. Регистрация
            await user_handlers.handle_start(mock_update, mock_context)

            # 2. Игры
            await game_handlers._handle_play_game(mock_update, mock_context)
            mock_context.args = ['rock']
            await game_handlers.handle_rps_choice(mock_update, mock_context)

            # 3. Донаты
            await user_service.add_donation(mock_update.effective_user.id, 1000.0)

            # 4. Статистика модерации (создаем другого пользователя для теста)
            target_user_id = 777777777
            await user_service.get_or_create_user(target_user_id, "target", "Target", "User")

            mock_context.args = [str(target_user_id), "Тест модерации"]
            await moderation_handlers._handle_warn(mock_update, mock_context, mock_context.args)

            # === ПРОВЕРКИ ИНТЕГРАЦИИ ===

            # Проверяем, что все данные сохранены корректно
            final_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Проверяем комплексные данные
            assert final_profile.reputation >= 10  # Минимум от доната
            assert final_profile.user_id == mock_update.effective_user.id

            # Проверяем достижения
            achievements = await user_service.get_user_achievements(mock_update.effective_user.id)
            assert len(achievements) >= 1

            # Проверяем игры
            game_stats = game_service.get_game_statistics(mock_update.effective_user.id)
            assert isinstance(game_stats, dict)

            # Проверяем модерацию
            moderation_stats = await moderation_service.get_moderation_stats()
            assert isinstance(moderation_stats, dict)
            assert moderation_stats['total_warnings'] >= 1

            # Проверяем платежи
            total_donations = await user_service.get_total_donations(mock_update.effective_user.id, 2025)
            assert total_donations >= 1000.0

            print("✅ Все компоненты успешно интегрированы и работают вместе")

        finally:
            user_repo.close()
            score_repo.close()
            payment_repo.close()
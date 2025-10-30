"""
Комплексные интеграционные тесты для системы уведомлений.
Тестирование полной цепочки: пользователь → модерация → уведомление
Проверяет взаимодействие: handlers -> moderation_service -> notification_service -> repositories
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from services.user_service import UserService
from services.moderation_service import ModerationService
from services.notification_service import NotificationService
from handlers.moderation_handlers import ModerationHandlers
from database.repository import UserRepository, ScoreRepository


class TestNotificationsIntegration:
    """Комплексные интеграционные тесты системы уведомлений"""

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

        # Мокаем пользователя (администратора)
        user = Mock()
        user.id = 123456789
        user.username = "admin_user"
        user.first_name = "Admin"
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
    async def test_notification_chain_user_profanity_moderation(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест полной цепочки: пользователь отправляет сообщение с матом → автоматическое предупреждение → уведомление о модерации"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        notification_service = NotificationService("123456789:integration_test_token", [123456789, 987654321])
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # Шаг 1: Создаем пользователя и добавляем слово в фильтр
            target_user_id = 987654321
            await user_service.get_or_create_user(
                target_user_id, "target_user", "Target", "User"
            )

            moderation_service.add_profanity_word("плохое_слово")

            # Шаг 2: Имитируем сообщение с матом через модерацию
            profane_message = "Это сообщение содержит плохое_слово"

            # Мокаем отправку уведомления о предупреждении
            with patch.object(notification_service, 'send_custom_notification', new_callable=AsyncMock) as mock_notify:
                # Шаг 3: Выполняем модерацию сообщения
                await moderation_service.moderate_message(
                    target_user_id,
                    profane_message,
                    mock_update.effective_chat.id
                )

                # Шаг 4: Проверяем, что уведомление было отправлено
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert call_args[0][0] == target_user_id  # user_id
                assert "предупреждение" in call_args[0][1].lower()  # message содержит предупреждение

            # Шаг 5: Проверяем, что предупреждение записано в базу
            moderation_stats = await moderation_service.get_moderation_stats()
            assert moderation_stats['total_warnings'] >= 1

            # Шаг 6: Проверяем историю модерации пользователя
            user_history = await moderation_service.get_user_moderation_history(target_user_id)
            assert len(user_history) >= 1
            assert user_history[0]['action_type'] == 'warn'

            # Шаг 7: Проверяем обновление профиля пользователя
            updated_profile = await user_service.get_or_create_user(
                target_user_id, "target_user", "Target", "User"
            )
            assert updated_profile.warnings >= 1

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_notification_chain_moderator_actions(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест цепочки уведомлений при действиях модератора"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        notification_service = NotificationService("123456789:integration_test_token", [123456789, 987654321])
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # Шаг 1: Создаем администратора и целевого пользователя
            admin_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            target_user_id = 987654321
            target_profile = await user_service.get_or_create_user(
                target_user_id, "target_user", "Target", "User"
            )

            # Шаг 2: Тестируем предупреждение с уведомлением
            with patch.object(notification_service, 'send_custom_notification', new_callable=AsyncMock) as mock_notify:
                mock_context.args = [str(target_user_id), "Тестовое предупреждение"]
                await moderation_handlers._handle_warn(mock_update, mock_context, mock_context.args)

                # Проверяем уведомление пользователю
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert call_args[0][0] == target_user_id
                assert "предупреждение" in call_args[0][1].lower()

            # Шаг 3: Тестируем мут с уведомлением
            with patch.object(notification_service, 'send_custom_notification', new_callable=AsyncMock) as mock_notify:
                mock_context.args = [str(target_user_id), "Тестовый мут", "60"]
                await moderation_handlers._handle_mute(mock_update, mock_context, mock_context.args)

                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert call_args[0][0] == target_user_id
                assert "мут" in call_args[0][1].lower()

            # Шаг 4: Тестируем бан с уведомлением
            with patch.object(notification_service, 'send_custom_notification', new_callable=AsyncMock) as mock_notify:
                mock_context.args = [str(target_user_id), "Тестовый бан"]
                await moderation_handlers._handle_ban(mock_update, mock_context, mock_context.args)

                mock_notify.assert_called_once()
                call_args = mock_notify.call_args
                assert call_args[0][0] == target_user_id
                assert "бан" in call_args[0][1].lower() or "заблокирован" in call_args[0][1].lower()

            # Шаг 5: Проверяем состояние пользователя после всех действий
            assert moderation_service.is_user_banned(target_user_id)
            assert moderation_service.is_user_muted(target_user_id)

            # Шаг 6: Проверяем историю модерации
            user_history = await moderation_service.get_user_moderation_history(target_user_id)
            action_types = [h['action_type'] for h in user_history]
            assert 'warn' in action_types
            assert 'mute' in action_types
            assert 'ban' in action_types

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_notification_chain_with_real_dependencies(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест с реальными зависимостями UserRepository и ScoreRepository"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        notification_service = NotificationService("123456789:integration_test_token", [123456789, 987654321])
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # Шаг 1: Создаем нескольких пользователей
            users = [
                (123456789, "admin", "Admin", "User"),
                (987654321, "user1", "User", "One"),
                (111222333, "user2", "User", "Two"),
                (444555666, "user3", "User", "Three")
            ]

            for user_id, username, first_name, last_name in users:
                await user_service.get_or_create_user(user_id, username, first_name, last_name)

            # Шаг 2: Добавляем достижения пользователям через ScoreRepository
            for user_id, _, _, _ in users[1:]:  # Пропускаем админа
                score_repo.add_score_transaction(user_id, 100, "Тестовое достижение")

            # Шаг 3: Выполняем массовую модерацию с уведомлениями
            notification_calls = []

            def mock_notification(user_id, message, parse_mode=None):
                notification_calls.append((user_id, message))

            with patch.object(notification_service, 'send_custom_notification', new_callable=AsyncMock, side_effect=mock_notification):
                # Предупреждаем всех пользователей
                for user_id, _, _, _ in users[1:]:
                    mock_context.args = [str(user_id), f"Массовое предупреждение для {user_id}"]
                    await moderation_handlers._handle_warn(mock_update, mock_context, mock_context.args)

            # Шаг 4: Проверяем, что все уведомления отправлены
            assert len(notification_calls) == 3  # Три пользователя (без админа)

            for user_id, _, _, _ in users[1:]:
                user_notifications = [call for call in notification_calls if call[0] == user_id]
                assert len(user_notifications) == 1
                assert "предупреждение" in user_notifications[0][1].lower()

            # Шаг 5: Проверяем, что данные корректно сохранены в репозиториях
            for user_id, _, _, _ in users[1:]:
                # Проверяем профиль через UserService
                profile = await user_service.get_or_create_user(user_id, f"user{user_id}", "User", str(user_id))
                assert profile.warnings >= 1

                # Проверяем достижения через ScoreRepository
                achievements = score_repo.get_user_achievements(user_id)
                assert len(achievements) >= 1

            # Шаг 6: Проверяем общую статистику модерации
            stats = await moderation_service.get_moderation_stats()
            assert stats['total_warnings'] >= 3

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_notification_error_handling_integration(self, temp_config, temp_db, mock_update, mock_context):
        """Тест обработки ошибок в цепочке уведомлений"""
        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        notification_service = NotificationService("invalid_token", [123456789, 987654321])
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # Шаг 1: Создаем пользователя
            target_user_id = 987654321
            await user_service.get_or_create_user(
                target_user_id, "target_user", "Target", "User"
            )

            # Шаг 2: Имитируем ошибку отправки уведомления
            with patch.object(notification_service, 'send_custom_notification', new_callable=AsyncMock, side_effect=Exception("Network error")):
                # Шаг 3: Пытаемся выполнить модерацию
                mock_context.args = [str(target_user_id), "Тестовое предупреждение"]
                await moderation_handlers._handle_warn(mock_update, mock_context, mock_context.args)

            # Шаг 4: Проверяем, что несмотря на ошибку уведомления, модерация прошла
            moderation_stats = await moderation_service.get_moderation_stats()
            assert moderation_stats['total_warnings'] >= 1

            # Шаг 5: Проверяем, что пользователь получил предупреждение
            updated_profile = await user_service.get_or_create_user(
                target_user_id, "target_user", "Target", "User"
            )
            assert updated_profile.warnings >= 1

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_notification_chain_performance(self, temp_config, temp_db, mock_update, mock_context):
        """Тест производительности цепочки уведомлений"""
        import time

        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        notification_service = NotificationService("123456789:integration_test_token", [123456789, 987654321])
        moderation_handlers = ModerationHandlers(config, config, user_service, moderation_service)

        try:
            # Шаг 1: Создаем несколько пользователей
            user_ids = []
            for i in range(10):
                user_id = 100000000 + i
                user_ids.append(user_id)
                await user_service.get_or_create_user(
                    user_id, f"user{i}", f"User{i}", f"Test{i}"
                )

            # Шаг 2: Замеряем время массовой отправки уведомлений
            start_time = time.time()

            with patch.object(notification_service, 'send_custom_notification', new_callable=AsyncMock):
                for user_id in user_ids:
                    mock_context.args = [str(user_id), f"Массовое уведомление {user_id}"]
                    await moderation_handlers._handle_warn(mock_update, mock_context, mock_context.args)

            end_time = time.time()
            duration = end_time - start_time

            # Шаг 3: Проверяем, что время выполнения разумное (менее 5 секунд для 10 пользователей)
            assert duration < 5.0, f"Слишком долгое выполнение: {duration} секунд"

            # Шаг 4: Проверяем, что все действия выполнены
            stats = await moderation_service.get_moderation_stats()
            assert stats['total_warnings'] >= 10

        finally:
            user_repo.close()
            score_repo.close()
"""
Интеграционный тест для проверки работы системы предупреждений.
Тестирует весь путь: добавление предупреждения → отображение в /info команде.
Проверяет поддержку русского языка, эмодзи и UTF-8 кодировки.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from datetime import datetime

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.application import Application
from core.config import Config


class TestWarningsIntegration:
    """Интеграционные тесты системы предупреждений с поддержкой UTF-8"""

    @pytest.fixture
    def temp_config(self):
        """Временный файл конфигурации для интеграционных тестов"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
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
        from database.repository import UserRepository, ScoreRepository

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
        user.first_name = "Тестовый"
        user.last_name = "Пользователь"
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
    async def test_full_warnings_flow_utf8(self, temp_config, temp_db, mock_update, mock_context):
        """Интеграционный тест полного цикла предупреждений с поддержкой UTF-8"""
        # Создаем конфигурацию
        config = Config(temp_config)

        # Создаем репозитории и сервисы
        from database.repository import UserRepository, ScoreRepository
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)

        from services.user_service import UserService
        user_service = UserService(user_repo, score_repo)

        from services.moderation_service import ModerationService
        moderation_service = ModerationService(user_repo, score_repo)

        # Создаем обработчик команд
        from handlers.user_handlers import UserHandlers
        user_handlers = UserHandlers(config, config, user_service)

        try:
            # Шаг 1: Создаем пользователя
            user_profile = await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )
            assert user_profile is not None, "Пользователь должен быть создан"
            assert user_profile.warnings == 0, "Изначально предупреждений должно быть 0"

            # Шаг 2: Добавляем предупреждение с UTF-8 текстом
            test_reasons = [
                "Спам в чате 🚫",
                "Нецензурная лексика с эмодзи 😡",
                "Нарушение правил поведения 📋",
                "Русский текст с UTF-8 символами: Привет мир! 🌍",
                "Специальные символы: àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ",
                "Кириллица: АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"
            ]

            admin_id = 987654321  # ID администратора

            for i, reason in enumerate(test_reasons):
                print(f"[TEST] Добавляем предупреждение {i+1}: '{reason}'")
                result = await moderation_service.warn_user(
                    mock_update.effective_user.id,
                    reason,
                    admin_id
                )

                assert result['success'] == True, f"Предупреждение {i+1} должно быть добавлено успешно"
                assert result['warnings_count'] == i + 1, f"Количество предупреждений должно быть {i+1}"
                assert result['reason'] == reason, f"Причина предупреждения должна сохраниться: {reason}"

                # Проверяем, что предупреждение сохранено в базе данных
                current_warnings = user_repo.get_warnings_count(mock_update.effective_user.id)
                assert current_warnings == i + 1, f"В базе данных должно быть {i+1} предупреждение(й)"

            # Шаг 3: Проверяем отображение в команде /info
            await user_handlers.handle_info(mock_update, mock_context)

            # Проверяем, что ответ был отправлен
            mock_update.message.reply_text.assert_called_once()

            # Получаем отправленный текст
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]  # Первый позиционный аргумент

            # Проверяем содержимое ответа
            assert "👤" in response_text, "Ответ должен содержать иконку пользователя"
            assert "Информация о пользователе" in response_text, "Ответ должен содержать заголовок"
            assert "Тестовый" in response_text, "Должно отображаться имя пользователя"
            assert f"⚠️ Предупреждений: {len(test_reasons)}" in response_text, f"Должно отображаться {len(test_reasons)} предупреждений"

            # Проверяем, что все UTF-8 символы сохранены корректно
            for reason in test_reasons:
                # Проверяем, что ключевые части причин присутствуют в ответе
                if "Спам в чате" in reason:
                    assert "Спам" in response_text, "Текст с кириллицей должен отображаться корректно"
                if "🚫" in reason:
                    assert "🚫" in response_text, "Эмодзи должны отображаться корректно"
                if "🌍" in reason:
                    assert "🌍" in response_text, "Эмодзи должны отображаться корректно"

            print("[SUCCESS] Все предупреждения корректно сохранены и отображаются в /info")

        finally:
            # Очищаем ресурсы
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_warnings_with_special_characters(self, temp_config, temp_db):
        """Тест предупреждений с специальными символами UTF-8"""
        from database.repository import UserRepository, ScoreRepository
        from services.user_service import UserService
        from services.moderation_service import ModerationService

        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)

        try:
            test_user_id = 111111111
            admin_id = 222222222

            # Создаем пользователя
            await user_service.get_or_create_user(test_user_id, "testuser", "Тест", "Юзер")

            # Тестируем различные специальные символы
            special_reasons = [
                "Математические символы: ∑∏√∫∆∞≠≈≤≥",
                "Стрелки: ←↑→↓↔⇄⇅",
                "Фигурки: ●○■□◆◇★☆♡♢♤♧",
                "Валюты: ¢£¤¥€₽₿",
                "Дроби: ½⅓¼¾⅕⅙⅛⅔⅖⅚⅜⅗⅘⅙⅚⅛⅜⅝⅞⅟",
                "Надстрочные: ⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ",
                "Подстрочные: ₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎",
                "Акценты: àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ",
                "Греческий: αβγδεζηθικλμνξοπρστυφχψω",
                "Китайские иероглифы: 你好世界こんにちは안녕하세요"
            ]

            for reason in special_reasons:
                print(f"[TEST] Тестируем специальную строку: '{reason}'")
                result = await moderation_service.warn_user(test_user_id, reason, admin_id)

                assert result['success'] == True, f"Предупреждение с символами '{reason[:20]}...' должно быть добавлено"
                assert result['reason'] == reason, f"Текст предупреждения должен сохраниться без изменений: {reason}"

                # Проверяем в базе данных
                warnings_count = user_repo.get_warnings_count(test_user_id)
                assert warnings_count > 0, "Предупреждение должно быть сохранено в БД"

            print("[SUCCESS] Все специальные символы UTF-8 корректно обработаны")

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_warnings_display_in_info_command(self, temp_config, temp_db, mock_update, mock_context):
        """Тест отображения предупреждений в команде /info"""
        from database.repository import UserRepository, ScoreRepository
        from services.user_service import UserService
        from services.moderation_service import ModerationService
        from handlers.user_handlers import UserHandlers
        from core.config import Config

        config = Config(temp_config)
        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)
        user_handlers = UserHandlers(config, config, user_service)

        try:
            # Создаем пользователя
            await user_service.get_or_create_user(
                mock_update.effective_user.id,
                mock_update.effective_user.username,
                mock_update.effective_user.first_name,
                mock_update.effective_user.last_name
            )

            # Добавляем несколько предупреждений с эмодзи
            warnings_to_add = [
                "Первое предупреждение ⚠️",
                "Второе нарушение 🚫",
                "Третье замечание 📋"
            ]

            for reason in warnings_to_add:
                await moderation_service.warn_user(
                    mock_update.effective_user.id,
                    reason,
                    987654321
                )

            # Выполняем команду /info
            await user_handlers.handle_info(mock_update, mock_context)

            # Получаем ответ
            call_args = mock_update.message.reply_text.call_args
            response_text = call_args[0][0]

            # Проверяем отображение количества предупреждений
            assert "⚠️ Предупреждений: 3" in response_text, "Должно отображаться правильное количество предупреждений"

            # Проверяем, что имя пользователя отображается корректно
            assert "Тестовый" in response_text, "Имя пользователя должно отображаться"

            print("[SUCCESS] Команда /info корректно отображает предупреждения")

        finally:
            user_repo.close()
            score_repo.close()

    @pytest.mark.asyncio
    async def test_warnings_persistence_across_sessions(self, temp_config, temp_db):
        """Тест сохранения предупреждений между сессиями"""
        from database.repository import UserRepository, ScoreRepository
        from services.user_service import UserService
        from services.moderation_service import ModerationService

        # Первая "сессия" - добавляем предупреждения
        user_repo1 = UserRepository(temp_db)
        score_repo1 = ScoreRepository(temp_db)
        user_service1 = UserService(user_repo1, score_repo1)
        moderation_service1 = ModerationService(user_repo1, score_repo1)

        try:
            test_user_id = 333333333
            admin_id = 444444444

            # Создаем пользователя и добавляем предупреждения
            await user_service1.get_or_create_user(test_user_id, "persist_test", "Персист", "Тест")

            test_reason = "Тест persistence с эмодзи 💾"
            await moderation_service1.warn_user(test_user_id, test_reason, admin_id)

            initial_count = user_repo1.get_warnings_count(test_user_id)
            assert initial_count == 1, "Предупреждение должно быть сохранено"

        finally:
            user_repo1.close()
            score_repo1.close()

        # Вторая "сессия" - проверяем, что предупреждения сохранились
        user_repo2 = UserRepository(temp_db)
        score_repo2 = ScoreRepository(temp_db)
        user_service2 = UserService(user_repo2, score_repo2)

        try:
            # Получаем профиль пользователя
            user_profile = await user_service2.get_or_create_user(test_user_id, "persist_test", "Персист", "Тест")

            # Проверяем, что предупреждения сохранились
            final_count = user_repo2.get_warnings_count(test_user_id)
            assert final_count == 1, "Предупреждение должно сохраниться между сессиями"

            assert user_profile.warnings == 1, "Количество предупреждений в профиле должно быть корректным"

            print("[SUCCESS] Предупреждения корректно сохраняются между сессиями")

        finally:
            user_repo2.close()
            score_repo2.close()

    @pytest.mark.asyncio
    async def test_multiple_users_warnings_isolation(self, temp_config, temp_db):
        """Тест изоляции предупреждений между пользователями"""
        from database.repository import UserRepository, ScoreRepository
        from services.user_service import UserService
        from services.moderation_service import ModerationService

        user_repo = UserRepository(temp_db)
        score_repo = ScoreRepository(temp_db)
        user_service = UserService(user_repo, score_repo)
        moderation_service = ModerationService(user_repo, score_repo)

        try:
            # Создаем двух пользователей
            user1_id = 555555555
            user2_id = 666666666
            admin_id = 777777777

            await user_service.get_or_create_user(user1_id, "user1", "Пользователь", "Первый")
            await user_service.get_or_create_user(user2_id, "user2", "Пользователь", "Второй")

            # Добавляем предупреждения первому пользователю
            await moderation_service.warn_user(user1_id, "Предупреждение для первого пользователя 👤", admin_id)
            await moderation_service.warn_user(user1_id, "Второе предупреждение для первого 🚨", admin_id)

            # Добавляем одно предупреждение второму пользователю
            await moderation_service.warn_user(user2_id, "Предупреждение для второго пользователя 🎯", admin_id)

            # Проверяем изоляцию
            user1_warnings = user_repo.get_warnings_count(user1_id)
            user2_warnings = user_repo.get_warnings_count(user2_id)

            assert user1_warnings == 2, "Первый пользователь должен иметь 2 предупреждения"
            assert user2_warnings == 1, "Второй пользователь должен иметь 1 предупреждение"

            print("[SUCCESS] Предупреждения пользователей изолированы друг от друга")

        finally:
            user_repo.close()
            score_repo.close()
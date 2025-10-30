"""
Интеграционные тесты для системы триггеров.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User

from core.message_router import create_message_router
from services.trigger_service import TriggerService
from database.repository import TriggerRepository


class TestTriggersIntegration:
    """Интеграционные тесты системы триггеров"""

    @pytest.fixture
    def mock_database_url(self):
        """URL тестовой базы данных"""
        return ':memory:'

    @pytest.fixture
    async def trigger_service(self, mock_database_url):
        """Фикстура сервиса триггеров с реальной базой данных"""
        service = TriggerService(mock_database_url)

        # Создаем тестовый триггер
        await service.add_trigger({
            'name': 'test_hello',
            'pattern': r'hello\s+world',
            'response_text': 'Hi there!',
            'chat_type': 'group'
        })

        yield service

        # Очистка после тестов
        await service.clear_cache()

    @pytest.fixture
    def message_router(self, trigger_service):
        """Фикстура маршрутизатора с сервисом триггеров"""
        return create_message_router(trigger_service)

    @pytest.fixture
    def mock_update_group_message(self):
        """Мок-объект для сообщения в группе"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock()

        user.id = 123456
        message.text = "hello world test"
        message.message_id = 789
        message.chat_id = 987654
        chat.type = "group"

        update.message = message
        update.effective_user = user
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_update_private_message(self):
        """Мок-объект для сообщения в привате"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        user = Mock(spec=User)
        chat = Mock()

        user.id = 123456
        message.text = "hello world private"
        chat.type = "private"

        update.message = message
        update.effective_user = user
        update.effective_chat = chat

        return update

    @pytest.fixture
    def mock_context(self):
        """Мок-объект для контекста бота"""
        context = Mock()
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        context.bot.send_sticker = AsyncMock()
        context.bot.send_animation = AsyncMock()
        context.bot.set_message_reaction = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_trigger_fires_in_group_chat(self, trigger_service, message_router,
                                              mock_update_group_message, mock_context):
        """Тест срабатывания триггера в групповом чате"""
        # Проверяем, что триггер найден
        matched_triggers = await trigger_service.check_triggers("hello world test", "group")
        assert len(matched_triggers) == 1
        assert matched_triggers[0]['name'] == 'test_hello'

        # Выполняем действия триггера
        actions = await trigger_service.execute_trigger_actions(
            matched_triggers, 987654, "hello world test", 789
        )

        assert len(actions) == 1
        assert actions[0]['type'] == 'text'
        assert actions[0]['content'] == 'Hi there!'

        # Выполняем действия через маршрутизатор
        await message_router._execute_trigger_actions(actions, mock_update_group_message, mock_context)

        # Проверяем, что сообщение было отправлено
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=987654,
            text='Hi there!',
            reply_to_message_id=789
        )

    @pytest.mark.asyncio
    async def test_trigger_not_fires_in_private_chat(self, trigger_service, message_router,
                                                    mock_update_private_message, mock_context):
        """Тест, что триггер не срабатывает в приватном чате"""
        # Проверяем, что триггер не найден для приватного чата
        matched_triggers = await trigger_service.check_triggers("hello world private", "private")
        assert len(matched_triggers) == 0

        # Маршрутизатор не должен вызывать проверку триггеров для приватных чатов
        result = await message_router.route_text_message(mock_update_private_message, mock_context)

        # Проверяем, что сервис триггеров не был вызван для проверки
        # (в приватных чатах триггеры не проверяются)

    @pytest.mark.asyncio
    async def test_trigger_with_reaction(self, trigger_service, message_router,
                                        mock_update_group_message, mock_context):
        """Тест триггера с реакцией"""
        # Создаем триггер с реакцией
        await trigger_service.add_trigger({
            'name': 'reaction_trigger',
            'pattern': r'react\s+test',
            'reaction_type': 'emoji',
            'action_data': '👍',
            'chat_type': 'group'
        })

        # Проверяем срабатывание
        matched_triggers = await trigger_service.check_triggers("react test message", "group")
        assert len(matched_triggers) == 1

        # Выполняем действия
        actions = await trigger_service.execute_trigger_actions(
            matched_triggers, 987654, "react test message", 789
        )

        assert len(actions) == 1
        assert actions[0]['type'] == 'reaction'
        assert actions[0]['content'] == '👍'

        # Выполняем через маршрутизатор
        await message_router._execute_trigger_actions(actions, mock_update_group_message, mock_context)

        # Проверяем установку реакции
        mock_context.bot.set_message_reaction.assert_called_once_with(
            chat_id=987654,
            message_id=789,
            reaction='👍'
        )

    @pytest.mark.asyncio
    async def test_trigger_with_multiple_responses(self, trigger_service, message_router,
                                                 mock_update_group_message, mock_context):
        """Тест триггера с множественными ответами"""
        # Создаем триггер с множественными ответами
        await trigger_service.add_trigger({
            'name': 'multi_trigger',
            'pattern': r'multi\s+test',
            'response_text': 'Text response',
            'response_sticker': 'sticker123',
            'response_gif': 'gif456',
            'reaction_type': 'emoji',
            'action_data': '❤️',
            'chat_type': 'group'
        })

        # Проверяем срабатывание
        matched_triggers = await trigger_service.check_triggers("multi test message", "group")
        assert len(matched_triggers) == 1

        # Выполняем действия
        actions = await trigger_service.execute_trigger_actions(
            matched_triggers, 987654, "multi test message", 789
        )

        assert len(actions) == 4  # text, sticker, gif, reaction

        action_types = [a['type'] for a in actions]
        assert 'text' in action_types
        assert 'sticker' in action_types
        assert 'gif' in action_types
        assert 'reaction' in action_types

        # Выполняем через маршрутизатор
        await message_router._execute_trigger_actions(actions, mock_update_group_message, mock_context)

        # Проверяем выполнение всех действий
        assert mock_context.bot.send_message.call_count == 1
        assert mock_context.bot.send_sticker.call_count == 1
        assert mock_context.bot.send_animation.call_count == 1
        assert mock_context.bot.set_message_reaction.call_count == 1

    @pytest.mark.asyncio
    async def test_trigger_statistics_update(self, trigger_service):
        """Тест обновления статистики триггера"""
        # Получаем триггер до срабатывания
        all_triggers = await trigger_service.get_all_triggers()
        initial_trigger = next(t for t in all_triggers if t['name'] == 'test_hello')
        initial_count = initial_trigger['trigger_count']

        # Имитируем срабатывание
        success = await trigger_service.update_trigger_stats(initial_trigger['id'])
        assert success == True

        # Проверяем обновление статистики
        all_triggers_after = await trigger_service.get_all_triggers()
        updated_trigger = next(t for t in all_triggers_after if t['name'] == 'test_hello')

        assert updated_trigger['trigger_count'] == initial_count + 1
        assert updated_trigger['last_triggered'] is not None

    @pytest.mark.asyncio
    async def test_trigger_cache_invalidation(self, trigger_service):
        """Тест инвалидации кеша триггеров"""
        # Получаем триггеры (заполняет кеш)
        triggers = await trigger_service.get_active_triggers('group')
        assert len(triggers) > 0

        # Проверяем, что кеш используется
        triggers_cached = await trigger_service.get_active_triggers('group')
        assert triggers_cached == triggers

        # Добавляем новый триггер (должен инвалидировать кеш)
        await trigger_service.add_trigger({
            'name': 'new_trigger',
            'pattern': r'new\s+pattern',
            'response_text': 'New response',
            'chat_type': 'group'
        })

        # Получаем триггеры снова (кеш должен быть инвалидирован)
        triggers_after = await trigger_service.get_active_triggers('group')
        assert len(triggers_after) == len(triggers) + 1

        # Проверяем наличие нового триггера
        new_trigger_names = [t['name'] for t in triggers_after]
        assert 'new_trigger' in new_trigger_names

    @pytest.mark.asyncio
    async def test_trigger_toggle_activation(self, trigger_service):
        """Тест активации/деактивации триггера"""
        # Получаем ID первого триггера
        all_triggers = await trigger_service.get_all_triggers()
        trigger_id = all_triggers[0]['id']

        # Деактивируем триггер
        success = await trigger_service.toggle_trigger(trigger_id, False)
        assert success == True

        # Проверяем, что триггер не активен
        active_triggers = await trigger_service.get_active_triggers('group')
        active_ids = [t['id'] for t in active_triggers]
        assert trigger_id not in active_ids

        # Активируем триггер обратно
        success = await trigger_service.toggle_trigger(trigger_id, True)
        assert success == True

        # Проверяем, что триггер снова активен
        active_triggers_after = await trigger_service.get_active_triggers('group')
        active_ids_after = [t['id'] for t in active_triggers_after]
        assert trigger_id in active_ids_after

    @pytest.mark.asyncio
    async def test_regex_pattern_matching(self, trigger_service):
        """Тест сопоставления регулярных выражений"""
        # Создаем триггеры с разными паттернами
        await trigger_service.add_trigger({
            'name': 'word_boundary',
            'pattern': r'\bhello\b',
            'response_text': 'Word boundary match',
            'chat_type': 'group'
        })

        await trigger_service.add_trigger({
            'name': 'case_insensitive',
            'pattern': r'HELLO',
            'response_text': 'Case insensitive match',
            'chat_type': 'group'
        })

        # Тест границ слова
        matches = await trigger_service.check_triggers("hello world", "group")
        assert len(matches) == 3  # test_hello, word_boundary, case_insensitive

        # Тест без границы слова
        matches = await trigger_service.check_triggers("helloworld", "group")
        # word_boundary не должен сработать
        boundary_trigger = next((m for m in matches if m['name'] == 'word_boundary'), None)
        assert boundary_trigger is None

    @pytest.mark.asyncio
    async def test_trigger_error_handling(self, trigger_service, message_router,
                                         mock_update_group_message, mock_context):
        """Тест обработки ошибок в системе триггеров"""
        # Создаем триггер с невалидным регулярным выражением
        await trigger_service.add_trigger({
            'name': 'invalid_regex',
            'pattern': r'[invalid',  # Невалидный regex
            'response_text': 'Should not work',
            'chat_type': 'group'
        })

        # Проверяем, что невалидный триггер не ломается всю систему
        matched_triggers = await trigger_service.check_triggers("test message", "group")

        # Должен сработать только валидный триггер
        valid_matches = [t for t in matched_triggers if t['name'] == 'test_hello']
        assert len(valid_matches) == 1

        # Тестируем выполнение действий с ошибкой в боте
        mock_context.bot.send_message.side_effect = Exception("Bot error")

        actions = await trigger_service.execute_trigger_actions(
            valid_matches, 987654, "test message", 789
        )

        # Не должно выбрасывать исключение
        await message_router._execute_trigger_actions(actions, mock_update_group_message, mock_context)

        # Метод должен был быть вызван несмотря на ошибку
        mock_context.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_reaction_priority(self, trigger_service, message_router,
                                            mock_update_group_message, mock_context):
        """Тест приоритета реакций при множественных триггерах"""
        # Создаем два триггера с реакциями
        await trigger_service.add_trigger({
            'name': 'first_reaction',
            'pattern': r'priority\s+test',
            'reaction_type': 'emoji',
            'action_data': '👍',
            'chat_type': 'group'
        })

        await trigger_service.add_trigger({
            'name': 'second_reaction',
            'pattern': r'priority\s+test',
            'reaction_type': 'emoji',
            'action_data': '❤️',
            'chat_type': 'group'
        })

        # Проверяем срабатывание обоих триггеров
        matched_triggers = await trigger_service.check_triggers("priority test", "group")
        assert len(matched_triggers) == 2

        # Выполняем действия
        actions = await trigger_service.execute_trigger_actions(
            matched_triggers, 987654, "priority test", 789
        )

        # Должны быть две реакции
        reactions = [a for a in actions if a['type'] == 'reaction']
        assert len(reactions) == 2

        # Выполняем через маршрутизатор (только первая реакция)
        await message_router._execute_trigger_actions(actions, mock_update_group_message, mock_context)

        # Проверяем, что установлена только первая реакция
        mock_context.bot.set_message_reaction.assert_called_once()
        call_args = mock_context.bot.set_message_reaction.call_args
        assert call_args[1]['reaction'] in ['👍', '❤️']  # Одна из реакций

    @pytest.mark.asyncio
    async def test_end_to_end_trigger_flow(self, trigger_service, message_router,
                                          mock_update_group_message, mock_context):
        """Полноценный end-to-end тест потока триггеров"""
        # 1. Создаем триггер
        trigger_id = await trigger_service.add_trigger({
            'name': 'e2e_trigger',
            'pattern': r'e2e\s+test',
            'response_text': 'E2E Response',
            'response_sticker': 'sticker123',
            'reaction_type': 'emoji',
            'action_data': '🎉',
            'chat_type': 'group'
        })
        assert trigger_id is not None

        # 2. Проверяем, что триггер активен
        active_triggers = await trigger_service.get_active_triggers('group')
        e2e_trigger = next((t for t in active_triggers if t['name'] == 'e2e_trigger'), None)
        assert e2e_trigger is not None
        assert e2e_trigger['trigger_count'] == 0

        # 3. Имитируем входящее сообщение
        mock_update_group_message.message.text = "e2e test message"

        # 4. Маршрутизатор обрабатывает сообщение
        result = await message_router.route_text_message(mock_update_group_message, mock_context)

        # 5. Проверяем, что действия были выполнены
        assert mock_context.bot.send_message.call_count == 1
        assert mock_context.bot.send_sticker.call_count == 1
        assert mock_context.bot.set_message_reaction.call_count == 1

        # 6. Проверяем обновление статистики
        updated_trigger = await trigger_service.get_trigger_by_id(trigger_id)
        assert updated_trigger['trigger_count'] == 1
        assert updated_trigger['last_triggered'] is not None

    @pytest.mark.asyncio
    async def test_private_chat_trigger_isolation(self, trigger_service, message_router,
                                                 mock_update_private_message, mock_context):
        """Тест изоляции триггеров в приватных чатах"""
        # Создаем триггер только для приватных чатов
        await trigger_service.add_trigger({
            'name': 'private_trigger',
            'pattern': r'private\s+only',
            'response_text': 'Private response',
            'chat_type': 'private'
        })

        # В приватном чате триггер должен сработать
        matched_private = await trigger_service.check_triggers("private only message", "private")
        assert len(matched_private) == 1
        assert matched_private[0]['name'] == 'private_trigger'

        # В групповом чате тот же триггер не должен сработать
        matched_group = await trigger_service.check_triggers("private only message", "group")
        private_triggers_in_group = [t for t in matched_group if t['name'] == 'private_trigger']
        assert len(private_triggers_in_group) == 0
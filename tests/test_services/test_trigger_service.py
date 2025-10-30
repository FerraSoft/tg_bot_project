"""
Unit-тесты для TriggerService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from services.trigger_service import TriggerService
from core.exceptions import ValidationError


class TestTriggerService:
    """Тесты сервиса триггеров"""

    @pytest.fixture
    def mock_repository(self):
        """Мок репозитория триггеров"""
        repo = Mock()
        repo.get_active_triggers_async = AsyncMock(return_value=[
            {
                'id': 1,
                'name': 'test_trigger',
                'pattern': r'hello',
                'response_text': 'Hi there!',
                'is_active': True,
                'chat_type': 'group'
            }
        ])
        repo.update_trigger_stats = Mock(return_value=True)
        return repo

    @pytest.fixture
    def trigger_service(self, mock_repository):
        """Фикстура сервиса триггеров с мок репозиторием"""
        with patch('services.trigger_service.TriggerRepository', return_value=mock_repository):
            service = TriggerService(':memory:')
            return service

    @pytest.mark.asyncio
    async def test_check_triggers_empty_text(self, trigger_service):
        """Тест проверки триггеров с пустым текстом"""
        result = await trigger_service.check_triggers("")
        assert result == []

        result = await trigger_service.check_triggers(None)
        assert result == []

    @pytest.mark.asyncio
    async def test_check_triggers_no_match(self, trigger_service):
        """Тест проверки триггеров без совпадений"""
        result = await trigger_service.check_triggers("goodbye")
        assert result == []

    @pytest.mark.asyncio
    async def test_check_triggers_match(self, trigger_service):
        """Тест проверки триггеров с совпадением"""
        result = await trigger_service.check_triggers("hello world")

        assert len(result) == 1
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'test_trigger'

    @pytest.mark.asyncio
    async def test_check_triggers_invalid_regex(self, trigger_service):
        """Тест обработки невалидного регулярного выражения"""
        # Меняем паттерн на невалидный
        trigger_service.repository.get_active_triggers_async.return_value = [
            {
                'id': 2,
                'name': 'invalid_trigger',
                'pattern': r'[invalid',
                'response_text': 'Invalid regex',
                'is_active': True,
                'chat_type': 'group'
            }
        ]

        result = await trigger_service.check_triggers("test")
        assert result == []  # Никакие триггеры не должны сработать

    @pytest.mark.asyncio
    async def test_get_active_triggers_cache_hit(self, trigger_service):
        """Тест получения активных триггеров из кеша"""
        # Заполняем кеш
        trigger_service._triggers_cache = [{'id': 1, 'name': 'cached'}]
        trigger_service._last_cache_update = datetime.now()

        result = await trigger_service.get_active_triggers()

        assert result == [{'id': 1, 'name': 'cached'}]
        # Репозиторий не должен вызываться при хите кеша
        trigger_service.repository.get_active_triggers_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_active_triggers_cache_miss(self, trigger_service):
        """Тест получения активных триггеров из базы при отсутствии кеша"""
        result = await trigger_service.get_active_triggers()

        assert len(result) == 1
        assert result[0]['id'] == 1
        trigger_service.repository.get_active_triggers_async.assert_called_once_with('group')

    @pytest.mark.asyncio
    async def test_get_active_triggers_private_chat(self, trigger_service):
        """Тест получения активных триггеров для приватного чата"""
        result = await trigger_service.get_active_triggers('private')

        trigger_service.repository.get_active_triggers_async.assert_called_once_with('private')

    @pytest.mark.asyncio
    async def test_execute_trigger_actions_text_response(self, trigger_service):
        """Тест выполнения действий триггера с текстовым ответом"""
        matched_triggers = [
            {
                'id': 1,
                'name': 'text_trigger',
                'response_text': 'Hello!',
                'response_sticker': None,
                'response_gif': None,
                'reaction_type': None
            }
        ]

        actions = await trigger_service.execute_trigger_actions(
            matched_triggers, 123456, "test message", 789
        )

        assert len(actions) == 1
        assert actions[0]['type'] == 'text'
        assert actions[0]['content'] == 'Hello!'
        assert actions[0]['trigger_id'] == 1

        # Проверяем обновление статистики
        trigger_service.repository.update_trigger_stats.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_execute_trigger_actions_reaction(self, trigger_service):
        """Тест выполнения действий триггера с реакцией"""
        matched_triggers = [
            {
                'id': 2,
                'name': 'reaction_trigger',
                'response_text': None,
                'response_sticker': None,
                'response_gif': None,
                'reaction_type': 'emoji',
                'action_data': '👍'
            }
        ]

        actions = await trigger_service.execute_trigger_actions(
            matched_triggers, 123456, "test message", 789
        )

        assert len(actions) == 1
        assert actions[0]['type'] == 'reaction'
        assert actions[0]['reaction_type'] == 'emoji'
        assert actions[0]['content'] == '👍'
        assert actions[0]['message_id'] == 789

    @pytest.mark.asyncio
    async def test_execute_trigger_actions_multiple_responses(self, trigger_service):
        """Тест выполнения действий триггера с множественными ответами"""
        matched_triggers = [
            {
                'id': 3,
                'name': 'multi_trigger',
                'response_text': 'Text response',
                'response_sticker': 'sticker_id',
                'response_gif': None,
                'reaction_type': 'emoji',
                'action_data': '❤️'
            }
        ]

        actions = await trigger_service.execute_trigger_actions(
            matched_triggers, 123456, "test message", 789
        )

        assert len(actions) == 3  # text, sticker, reaction

        action_types = [a['type'] for a in actions]
        assert 'text' in action_types
        assert 'sticker' in action_types
        assert 'reaction' in action_types

    @pytest.mark.asyncio
    async def test_update_trigger_stats_success(self, trigger_service):
        """Тест успешного обновления статистики триггера"""
        result = await trigger_service.update_trigger_stats(1)

        assert result == True
        trigger_service.repository.update_trigger_stats.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_update_trigger_stats_failure(self, trigger_service):
        """Тест неудачного обновления статистики триггера"""
        trigger_service.repository.update_trigger_stats.return_value = False

        result = await trigger_service.update_trigger_stats(1)

        assert result == False

    @pytest.mark.asyncio
    async def test_add_trigger_success(self, trigger_service):
        """Тест успешного добавления триггера"""
        trigger_data = {
            'name': 'new_trigger',
            'pattern': r'test\s+pattern',
            'response_text': 'Test response',
            'chat_type': 'group'
        }

        trigger_service.repository.add_trigger.return_value = 5

        result = await trigger_service.add_trigger(trigger_data)

        assert result == 5
        trigger_service.repository.add_trigger.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_trigger_validation_error(self, trigger_service):
        """Тест добавления триггера с ошибкой валидации"""
        trigger_data = {
            'name': '',  # Пустое имя
            'pattern': r'test',
            'chat_type': 'group'
        }

        with pytest.raises(ValidationError):
            await trigger_service.add_trigger(trigger_data)

    @pytest.mark.asyncio
    async def test_add_trigger_invalid_regex(self, trigger_service):
        """Тест добавления триггера с невалидным regex"""
        trigger_data = {
            'name': 'invalid_trigger',
            'pattern': r'[invalid',  # Невалидный regex
            'chat_type': 'group'
        }

        with pytest.raises(ValidationError):
            await trigger_service.add_trigger(trigger_data)

    @pytest.mark.asyncio
    async def test_update_trigger_success(self, trigger_service):
        """Тест успешного обновления триггера"""
        update_data = {'name': 'updated_name'}

        result = await trigger_service.update_trigger(1, update_data)

        assert result == True
        trigger_service.repository.update_trigger.assert_called_once_with(1, update_data)

    @pytest.mark.asyncio
    async def test_delete_trigger_success(self, trigger_service):
        """Тест успешного удаления триггера"""
        result = await trigger_service.delete_trigger(1)

        assert result == True
        trigger_service.repository.delete_trigger.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_toggle_trigger_success(self, trigger_service):
        """Тест успешного переключения статуса триггера"""
        result = await trigger_service.toggle_trigger(1, True)

        assert result == True
        trigger_service.repository.toggle_trigger.assert_called_once_with(1, True)

    @pytest.mark.asyncio
    async def test_get_all_triggers(self, trigger_service):
        """Тест получения всех триггеров"""
        trigger_service.repository.get_all_triggers.return_value = [
            {'id': 1, 'name': 'trigger1'},
            {'id': 2, 'name': 'trigger2'}
        ]

        result = await trigger_service.get_all_triggers()

        assert len(result) == 2
        trigger_service.repository.get_all_triggers.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_trigger_by_id(self, trigger_service):
        """Тест получения триггера по ID"""
        trigger_service.repository.get_trigger_by_id.return_value = {'id': 1, 'name': 'test'}

        result = await trigger_service.get_trigger_by_id(1)

        assert result['id'] == 1
        trigger_service.repository.get_trigger_by_id.assert_called_once_with(1)

    def test_build_trigger_actions_text_only(self, trigger_service):
        """Тест построения действий триггера только с текстом"""
        trigger = {
            'id': 1,
            'name': 'text_trigger',
            'response_text': 'Hello!',
            'response_sticker': None,
            'response_gif': None,
            'reaction_type': None
        }

        actions = trigger_service._build_trigger_actions(trigger, 123, "test", 456)

        assert len(actions) == 1
        assert actions[0]['type'] == 'text'
        assert actions[0]['content'] == 'Hello!'

    def test_build_trigger_actions_reaction_only(self, trigger_service):
        """Тест построения действий триггера только с реакцией"""
        trigger = {
            'id': 2,
            'name': 'reaction_trigger',
            'response_text': None,
            'response_sticker': None,
            'response_gif': None,
            'reaction_type': 'emoji',
            'action_data': '👍'
        }

        actions = trigger_service._build_trigger_actions(trigger, 123, "test", 456)

        assert len(actions) == 1
        assert actions[0]['type'] == 'reaction'
        assert actions[0]['reaction_type'] == 'emoji'
        assert actions[0]['content'] == '👍'
        assert actions[0]['message_id'] == 456

    def test_build_trigger_actions_reaction_no_message_id(self, trigger_service):
        """Тест построения действий триггера с реакцией без message_id"""
        trigger = {
            'id': 3,
            'name': 'reaction_trigger',
            'response_text': None,
            'response_sticker': None,
            'response_gif': None,
            'reaction_type': 'emoji',
            'action_data': '👍'
        }

        actions = trigger_service._build_trigger_actions(trigger, 123, "test", None)

        assert len(actions) == 0  # Реакция не должна добавляться без message_id

    def test_build_trigger_actions_multiple_types(self, trigger_service):
        """Тест построения действий триггера со множественными типами"""
        trigger = {
            'id': 4,
            'name': 'multi_trigger',
            'response_text': 'Text response',
            'response_sticker': 'sticker123',
            'response_gif': 'gif456',
            'reaction_type': 'emoji',
            'action_data': '❤️'
        }

        actions = trigger_service._build_trigger_actions(trigger, 123, "test", 789)

        assert len(actions) == 4
        action_types = [a['type'] for a in actions]
        assert 'text' in action_types
        assert 'sticker' in action_types
        assert 'gif' in action_types
        assert 'reaction' in action_types

    def test_validate_trigger_data_valid(self, trigger_service):
        """Тест валидации корректных данных триггера"""
        data = {
            'name': 'Valid Trigger',
            'pattern': r'hello\s+world',
            'chat_type': 'group'
        }

        # Не должно выбрасывать исключение
        trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_missing_name(self, trigger_service):
        """Тест валидации данных триггера без имени"""
        data = {
            'pattern': r'test',
            'chat_type': 'group'
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_empty_name(self, trigger_service):
        """Тест валидации данных триггера с пустым именем"""
        data = {
            'name': '',
            'pattern': r'test',
            'chat_type': 'group'
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_long_name(self, trigger_service):
        """Тест валидации данных триггера с слишком длинным именем"""
        data = {
            'name': 'a' * 101,  # 101 символ
            'pattern': r'test',
            'chat_type': 'group'
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_missing_pattern(self, trigger_service):
        """Тест валидации данных триггера без паттерна"""
        data = {
            'name': 'Test Trigger',
            'chat_type': 'group'
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_empty_pattern(self, trigger_service):
        """Тест валидации данных триггера с пустым паттерном"""
        data = {
            'name': 'Test Trigger',
            'pattern': '',
            'chat_type': 'group'
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_long_pattern(self, trigger_service):
        """Тест валидации данных триггера с слишком длинным паттерном"""
        data = {
            'name': 'Test Trigger',
            'pattern': 'a' * 501,  # 501 символ
            'chat_type': 'group'
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_invalid_chat_type(self, trigger_service):
        """Тест валидации данных триггера с некорректным типом чата"""
        data = {
            'name': 'Test Trigger',
            'pattern': r'test',
            'chat_type': 'invalid'
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_reaction_without_action_data(self, trigger_service):
        """Тест валидации данных триггера с реакцией без action_data"""
        data = {
            'name': 'Test Trigger',
            'pattern': r'test',
            'chat_type': 'group',
            'reaction_type': 'emoji'
            # action_data отсутствует
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_trigger_data_invalid_reaction_type(self, trigger_service):
        """Тест валидации данных триггера с некорректным типом реакции"""
        data = {
            'name': 'Test Trigger',
            'pattern': r'test',
            'chat_type': 'group',
            'reaction_type': 'invalid_type',
            'action_data': 'test'
        }

        with pytest.raises(ValidationError):
            trigger_service._validate_trigger_data(data)

    def test_validate_regex_pattern_valid(self, trigger_service):
        """Тест валидации корректного регулярного выражения"""
        # Не должно выбрасывать исключение
        trigger_service._validate_regex_pattern(r'hello\s+world')

    def test_validate_regex_pattern_invalid(self, trigger_service):
        """Тест валидации некорректного регулярного выражения"""
        with pytest.raises(ValidationError):
            trigger_service._validate_regex_pattern(r'[invalid')

    def test_should_use_cache_no_cache(self, trigger_service):
        """Тест проверки использования кеша при отсутствии кеша"""
        assert trigger_service._should_use_cache() == False

    def test_should_use_cache_expired(self, trigger_service):
        """Тест проверки использования кеша при истекшем кеше"""
        trigger_service._triggers_cache = [{'id': 1}]
        trigger_service._last_cache_update = datetime.now()
        trigger_service._cache_ttl_seconds = 0  # Кеш сразу истекает

        assert trigger_service._should_use_cache() == False

    def test_should_use_cache_valid(self, trigger_service):
        """Тест проверки использования кеша при валидном кеше"""
        trigger_service._triggers_cache = [{'id': 1}]
        trigger_service._last_cache_update = datetime.now()

        assert trigger_service._should_use_cache() == True

    def test_invalidate_cache(self, trigger_service):
        """Тест инвалидации кеша"""
        trigger_service._triggers_cache = [{'id': 1}]
        trigger_service._last_cache_update = datetime.now()

        trigger_service._invalidate_cache()

        assert trigger_service._triggers_cache is None
        assert trigger_service._last_cache_update is None

    @pytest.mark.asyncio
    async def test_clear_cache(self, trigger_service):
        """Тест очистки кеша"""
        trigger_service._triggers_cache = [{'id': 1}]
        trigger_service._last_cache_update = datetime.now()

        await trigger_service.clear_cache()

        assert trigger_service._triggers_cache is None
        assert trigger_service._last_cache_update is None
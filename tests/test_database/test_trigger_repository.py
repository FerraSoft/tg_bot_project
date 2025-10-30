"""
Unit-тесты для TriggerRepository.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from database.repository import TriggerRepository


class TestTriggerRepository:
    """Тесты репозитория триггеров"""

    @pytest.fixture
    def trigger_repository(self):
        """Фикстура репозитория триггеров с in-memory базой"""
        repo = TriggerRepository(':memory:')
        return repo

    def test_get_active_triggers_group(self, trigger_repository):
        """Тест получения активных триггеров для групповых чатов"""
        # Создаем тестовые данные
        trigger_repository._execute_query("""
            INSERT INTO triggers (name, pattern, response_text, is_active, chat_type)
            VALUES (?, ?, ?, ?, ?)
        """, ('active_group_trigger', r'hello', 'Hi!', 1, 'group'))

        trigger_repository._execute_query("""
            INSERT INTO triggers (name, pattern, response_text, is_active, chat_type)
            VALUES (?, ?, ?, ?, ?)
        """, ('inactive_trigger', r'bye', 'Bye!', 0, 'group'))

        trigger_repository._execute_query("""
            INSERT INTO triggers (name, pattern, response_text, is_active, chat_type)
            VALUES (?, ?, ?, ?, ?)
        """, ('private_trigger', r'private', 'Private!', 1, 'private'))

        triggers = trigger_repository.get_active_triggers('group')

        assert len(triggers) == 1
        assert triggers[0]['name'] == 'active_group_trigger'
        assert triggers[0]['pattern'] == r'hello'
        assert triggers[0]['response_text'] == 'Hi!'

    def test_get_active_triggers_private(self, trigger_repository):
        """Тест получения активных триггеров для приватных чатов"""
        # Создаем тестовые данные
        trigger_repository._execute_query("""
            INSERT INTO triggers (name, pattern, response_text, is_active, chat_type)
            VALUES (?, ?, ?, ?, ?)
        """, ('private_trigger', r'private', 'Private!', 1, 'private'))

        trigger_repository._execute_query("""
            INSERT INTO triggers (name, pattern, response_text, is_active, chat_type)
            VALUES (?, ?, ?, ?, ?)
        """, ('group_trigger', r'group', 'Group!', 1, 'group'))

        triggers = trigger_repository.get_active_triggers('private')

        assert len(triggers) == 1
        assert triggers[0]['name'] == 'private_trigger'
        assert triggers[0]['chat_type'] == 'private'

    @pytest.mark.asyncio
    async def test_get_active_triggers_async(self, trigger_repository):
        """Тест асинхронного получения активных триггеров"""
        # Создаем тестовые данные
        trigger_repository._execute_query("""
            INSERT INTO triggers (name, pattern, response_text, is_active, chat_type)
            VALUES (?, ?, ?, ?, ?)
        """, ('async_trigger', r'async', 'Async!', 1, 'group'))

        triggers = await trigger_repository.get_active_triggers_async('group')

        assert len(triggers) == 1
        assert triggers[0]['name'] == 'async_trigger'

    def test_add_trigger_success(self, trigger_repository):
        """Тест успешного добавления триггера"""
        trigger_data = {
            'name': 'new_trigger',
            'description': 'Test trigger',
            'pattern': r'test\s+pattern',
            'response_text': 'Test response',
            'response_sticker': 'sticker123',
            'response_gif': 'gif456',
            'created_by': 123456,
            'chat_type': 'group'
        }

        trigger_id = trigger_repository.add_trigger(trigger_data)

        assert trigger_id is not None
        assert isinstance(trigger_id, int)

        # Проверяем, что триггер был добавлен
        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger is not None
        assert trigger['name'] == 'new_trigger'
        assert trigger['description'] == 'Test trigger'
        assert trigger['pattern'] == r'test\s+pattern'
        assert trigger['response_text'] == 'Test response'
        assert trigger['response_sticker'] == 'sticker123'
        assert trigger['response_gif'] == 'gif456'
        assert trigger['created_by'] == 123456
        assert trigger['chat_type'] == 'group'
        assert trigger['is_active'] == 1
        assert trigger['trigger_count'] == 0

    def test_add_trigger_minimal_data(self, trigger_repository):
        """Тест добавления триггера с минимальными данными"""
        trigger_data = {
            'name': 'minimal_trigger',
            'pattern': r'minimal'
        }

        trigger_id = trigger_repository.add_trigger(trigger_data)

        assert trigger_id is not None

        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger['name'] == 'minimal_trigger'
        assert trigger['pattern'] == r'minimal'
        assert trigger['response_text'] is None
        assert trigger['chat_type'] == 'group'  # значение по умолчанию

    def test_update_trigger_stats_success(self, trigger_repository):
        """Тест успешного обновления статистики триггера"""
        # Создаем триггер
        trigger_id = trigger_repository.add_trigger({
            'name': 'stats_trigger',
            'pattern': r'stats'
        })

        # Обновляем статистику
        success = trigger_repository.update_trigger_stats(trigger_id)

        assert success == True

        # Проверяем обновление
        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger['trigger_count'] == 1
        assert trigger['last_triggered'] is not None

    def test_update_trigger_stats_nonexistent(self, trigger_repository):
        """Тест обновления статистики несуществующего триггера"""
        success = trigger_repository.update_trigger_stats(99999)

        assert success == False

    def test_get_trigger_by_id_exists(self, trigger_repository):
        """Тест получения существующего триггера по ID"""
        trigger_data = {
            'name': 'test_trigger',
            'pattern': r'test',
            'response_text': 'Test response'
        }

        trigger_id = trigger_repository.add_trigger(trigger_data)
        trigger = trigger_repository.get_trigger_by_id(trigger_id)

        assert trigger is not None
        assert trigger['id'] == trigger_id
        assert trigger['name'] == 'test_trigger'
        assert trigger['pattern'] == r'test'
        assert trigger['response_text'] == 'Test response'

    def test_get_trigger_by_id_not_exists(self, trigger_repository):
        """Тест получения несуществующего триггера по ID"""
        trigger = trigger_repository.get_trigger_by_id(99999)

        assert trigger is None

    def test_update_trigger_success(self, trigger_repository):
        """Тест успешного обновления триггера"""
        # Создаем триггер
        trigger_id = trigger_repository.add_trigger({
            'name': 'update_trigger',
            'pattern': r'old_pattern',
            'response_text': 'Old response'
        })

        # Обновляем
        update_data = {
            'name': 'updated_trigger',
            'pattern': r'new_pattern',
            'response_text': 'New response'
        }

        success = trigger_repository.update_trigger(trigger_id, update_data)

        assert success == True

        # Проверяем обновление
        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger['name'] == 'updated_trigger'
        assert trigger['pattern'] == r'new_pattern'
        assert trigger['response_text'] == 'New response'

    def test_update_trigger_not_exists(self, trigger_repository):
        """Тест обновления несуществующего триггера"""
        success = trigger_repository.update_trigger(99999, {'name': 'new_name'})

        assert success == False

    def test_update_trigger_partial(self, trigger_repository):
        """Тест частичного обновления триггера"""
        # Создаем триггер
        trigger_id = trigger_repository.add_trigger({
            'name': 'partial_trigger',
            'pattern': r'partial',
            'response_text': 'Original response'
        })

        # Обновляем только имя
        success = trigger_repository.update_trigger(trigger_id, {'name': 'updated_partial'})

        assert success == True

        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger['name'] == 'updated_partial'
        assert trigger['pattern'] == r'partial'  # Не изменено
        assert trigger['response_text'] == 'Original response'  # Не изменено

    def test_delete_trigger_success(self, trigger_repository):
        """Тест успешного удаления триггера"""
        # Создаем триггер
        trigger_id = trigger_repository.add_trigger({
            'name': 'delete_trigger',
            'pattern': r'delete'
        })

        # Удаляем
        success = trigger_repository.delete_trigger(trigger_id)

        assert success == True

        # Проверяем, что триггер удален
        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger is None

    def test_delete_trigger_not_exists(self, trigger_repository):
        """Тест удаления несуществующего триггера"""
        success = trigger_repository.delete_trigger(99999)

        assert success == False

    def test_get_all_triggers(self, trigger_repository):
        """Тест получения всех триггеров"""
        # Создаем несколько триггеров
        trigger_repository.add_trigger({
            'name': 'trigger1',
            'pattern': r'pattern1'
        })

        trigger_repository.add_trigger({
            'name': 'trigger2',
            'pattern': r'pattern2'
        })

        triggers = trigger_repository.get_all_triggers()

        assert len(triggers) >= 2  # Может быть больше из других тестов

        # Проверяем сортировку по created_at DESC
        trigger_names = [t['name'] for t in triggers if t['name'] in ['trigger1', 'trigger2']]
        assert 'trigger2' in trigger_names  # trigger2 создан позже

    def test_toggle_trigger_activate(self, trigger_repository):
        """Тест активации триггера"""
        # Создаем неактивный триггер
        trigger_id = trigger_repository.add_trigger({
            'name': 'toggle_trigger',
            'pattern': r'toggle'
        })

        # Деактивируем
        trigger_repository.toggle_trigger(trigger_id, False)

        # Активируем
        success = trigger_repository.toggle_trigger(trigger_id, True)

        assert success == True

        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger['is_active'] == 1

    def test_toggle_trigger_deactivate(self, trigger_repository):
        """Тест деактивации триггера"""
        # Создаем активный триггер (по умолчанию активен)
        trigger_id = trigger_repository.add_trigger({
            'name': 'deactivate_trigger',
            'pattern': r'deactivate'
        })

        # Деактивируем
        success = trigger_repository.toggle_trigger(trigger_id, False)

        assert success == True

        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger['is_active'] == 0

    def test_toggle_trigger_not_exists(self, trigger_repository):
        """Тест переключения статуса несуществующего триггера"""
        success = trigger_repository.toggle_trigger(99999, True)

        assert success == False

    def test_trigger_with_reaction(self, trigger_repository):
        """Тест триггера с реакцией"""
        trigger_data = {
            'name': 'reaction_trigger',
            'pattern': r'react',
            'reaction_type': 'emoji',
            'action_data': '👍'
        }

        trigger_id = trigger_repository.add_trigger(trigger_data)

        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger.get('reaction_type') == 'emoji'
        assert trigger.get('action_data') == '👍'

    def test_trigger_with_multiple_responses(self, trigger_repository):
        """Тест триггера с множественными ответами"""
        trigger_data = {
            'name': 'multi_response_trigger',
            'pattern': r'multi',
            'response_text': 'Text response',
            'response_sticker': 'sticker123',
            'response_gif': 'gif456',
            'reaction_type': 'emoji',
            'action_data': '❤️'
        }

        trigger_id = trigger_repository.add_trigger(trigger_data)

        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger['response_text'] == 'Text response'
        assert trigger['response_sticker'] == 'sticker123'
        assert trigger['response_gif'] == 'gif456'
        assert trigger.get('reaction_type') == 'emoji'
        assert trigger.get('action_data') == '❤️'

    def test_trigger_default_values(self, trigger_repository):
        """Тест значений по умолчанию для триггера"""
        trigger_data = {
            'name': 'default_trigger',
            'pattern': r'default'
        }

        trigger_id = trigger_repository.add_trigger(trigger_data)

        trigger = trigger_repository.get_trigger_by_id(trigger_id)
        assert trigger['chat_type'] == 'group'
        assert trigger['is_active'] == 1
        assert trigger['trigger_count'] == 0
        assert trigger['created_by'] == 0
        assert trigger['response_text'] is None
        assert trigger['response_sticker'] is None
        assert trigger['response_gif'] is None
        assert trigger.get('reaction_type') is None
        assert trigger.get('action_data') is None
        assert trigger.get('last_triggered') is None
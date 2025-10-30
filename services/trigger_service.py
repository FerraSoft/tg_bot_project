"""
Сервис управления триггерами сообщений.
Отвечает за проверку триггеров, их активацию и обновление статистики.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from database.repository import TriggerRepository
from core.exceptions import ValidationError, DatabaseError


class TriggerService:
    """
    Сервис для управления триггерами сообщений.

    Отвечает за:
    - Проверку текста сообщений на совпадение с триггерами
    - Выполнение действий при срабатывании триггеров
    - Обновление статистики использования триггеров
    - Управление активными триггерами
    """

    def __init__(self, database_url: str):
        """
        Инициализация сервиса триггеров.

        Args:
            database_url: URL базы данных
        """
        self.logger = logging.getLogger(__name__)
        self.repository = TriggerRepository(database_url)
        self._triggers_cache: Optional[List[Dict]] = None
        self._last_cache_update: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 минут

    async def check_triggers(self, message_text: str, chat_type: str = "group") -> List[Dict]:
        """
        Проверка текста сообщения на совпадение с активными триггерами.

        Args:
            message_text: Текст сообщения для проверки
            chat_type: Тип чата ("group" или "private")

        Returns:
            Список сработавших триггеров с их данными
        """
        if not message_text or not isinstance(message_text, str):
            return []

        try:
            # Получаем активные триггеры
            active_triggers = await self.get_active_triggers(chat_type)

            if not active_triggers:
                return []

            matched_triggers = []

            for trigger in active_triggers:
                try:
                    # Компилируем регулярное выражение
                    pattern = re.compile(trigger['pattern'], re.IGNORECASE | re.MULTILINE)

                    # Проверяем совпадение
                    if pattern.search(message_text.strip()):
                        matched_triggers.append(trigger)

                        # Обновляем статистику асинхронно (не ждем завершения)
                        self._update_trigger_stats_async(trigger['id'])

                except re.error as e:
                    self.logger.error(f"Invalid regex pattern in trigger {trigger['id']}: {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Error checking trigger {trigger['id']}: {e}")
                    continue

            return matched_triggers

        except Exception as e:
            self.logger.error(f"Error in check_triggers: {e}")
            return []

    async def get_active_triggers(self, chat_type: str = "group") -> List[Dict]:
        """
        Получение активных триггеров для указанного типа чата.

        Args:
            chat_type: Тип чата ("group" или "private")

        Returns:
            Список активных триггеров
        """
        try:
            # Проверяем кеш
            if self._should_use_cache():
                return self._triggers_cache or []

            # Получаем из базы данных
            triggers = await self.repository.get_active_triggers_async(chat_type)

            # Обновляем кеш
            self._triggers_cache = triggers
            self._last_cache_update = datetime.now()

            return triggers

        except DatabaseError as e:
            self.logger.error(f"Database error getting active triggers: {e}")
            return self._triggers_cache or []
        except Exception as e:
            self.logger.error(f"Error getting active triggers: {e}")
            return []

    async def execute_trigger_actions(self, matched_triggers: List[Dict],
                                    chat_id: int, message_text: str, message_id: int = None) -> List[Dict]:
        """
        Выполнение действий для сработавших триггеров.

        Args:
            matched_triggers: Список сработавших триггеров
            chat_id: ID чата
            message_text: Оригинальный текст сообщения
            message_id: ID сообщения (для реакций)

        Returns:
            Список действий для выполнения
        """
        actions = []

        for trigger in matched_triggers:
            try:
                trigger_actions = self._build_trigger_actions(trigger, chat_id, message_text, message_id)
                actions.extend(trigger_actions)

                # Обновляем статистику
                await self.update_trigger_stats(trigger['id'])

            except Exception as e:
                self.logger.error(f"Error executing actions for trigger {trigger['id']}: {e}")
                continue

        return actions

    def _build_trigger_actions(self, trigger: Dict, chat_id: int, message_text: str, message_id: int = None) -> List[Dict]:
        """
        Построение списка действий для триггера.

        Args:
            trigger: Данные триггера
            chat_id: ID чата
            message_text: Текст сообщения
            message_id: ID сообщения (для реакций)

        Returns:
            Список действий
        """
        actions = []

        # Текстовый ответ
        if trigger.get('response_text'):
            actions.append({
                'type': 'text',
                'content': trigger['response_text'],
                'trigger_id': trigger['id'],
                'trigger_name': trigger['name']
            })

        # Стикер
        if trigger.get('response_sticker'):
            actions.append({
                'type': 'sticker',
                'content': trigger['response_sticker'],
                'trigger_id': trigger['id'],
                'trigger_name': trigger['name']
            })

        # GIF
        if trigger.get('response_gif'):
            actions.append({
                'type': 'gif',
                'content': trigger['response_gif'],
                'trigger_id': trigger['id'],
                'trigger_name': trigger['name']
            })

        # Реакция
        if trigger.get('reaction_type') and trigger.get('action_data') and message_id is not None:
            actions.append({
                'type': 'reaction',
                'reaction_type': trigger['reaction_type'],
                'content': trigger['action_data'],  # emoji
                'message_id': message_id,
                'trigger_id': trigger['id'],
                'trigger_name': trigger['name']
            })

        return actions

    async def update_trigger_stats(self, trigger_id: int) -> bool:
        """
        Обновление статистики срабатывания триггера.

        Args:
            trigger_id: ID триггера

        Returns:
            True если обновление успешно
        """
        try:
            success = self.repository.update_trigger_stats(trigger_id)

            # Инвалидируем кеш
            self._invalidate_cache()

            return success

        except Exception as e:
            self.logger.error(f"Error updating trigger stats for {trigger_id}: {e}")
            return False

    def _update_trigger_stats_async(self, trigger_id: int):
        """Асинхронное обновление статистики триггера (не ждет завершения)"""
        import asyncio
        asyncio.create_task(self.update_trigger_stats(trigger_id))

    async def add_trigger(self, trigger_data: Dict) -> Optional[int]:
        """
        Добавление нового триггера.

        Args:
            trigger_data: Данные триггера

        Returns:
            ID созданного триггера или None при ошибке
        """
        try:
            # Валидация данных
            self._validate_trigger_data(trigger_data)

            # Проверяем регулярное выражение
            self._validate_regex_pattern(trigger_data['pattern'])

            trigger_id = self.repository.add_trigger(trigger_data)

            # Инвалидируем кеш
            self._invalidate_cache()

            self.logger.info(f"Created new trigger: {trigger_data['name']} (ID: {trigger_id})")
            return trigger_id

        except ValidationError as e:
            self.logger.warning(f"Validation error creating trigger: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating trigger: {e}")
            return None

    async def update_trigger(self, trigger_id: int, update_data: Dict) -> bool:
        """
        Обновление триггера.

        Args:
            trigger_id: ID триггера
            update_data: Данные для обновления

        Returns:
            True если обновление успешно
        """
        try:
            # Валидация данных
            if 'pattern' in update_data:
                self._validate_regex_pattern(update_data['pattern'])

            success = self.repository.update_trigger(trigger_id, update_data)

            # Инвалидируем кеш
            self._invalidate_cache()

            if success:
                self.logger.info(f"Updated trigger {trigger_id}")
            else:
                self.logger.warning(f"Trigger {trigger_id} not found for update")

            return success

        except ValidationError as e:
            self.logger.warning(f"Validation error updating trigger {trigger_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating trigger {trigger_id}: {e}")
            return False

    async def delete_trigger(self, trigger_id: int) -> bool:
        """
        Удаление триггера.

        Args:
            trigger_id: ID триггера

        Returns:
            True если удаление успешно
        """
        try:
            success = self.repository.delete_trigger(trigger_id)

            # Инвалидируем кеш
            self._invalidate_cache()

            if success:
                self.logger.info(f"Deleted trigger {trigger_id}")
            else:
                self.logger.warning(f"Trigger {trigger_id} not found for deletion")

            return success

        except Exception as e:
            self.logger.error(f"Error deleting trigger {trigger_id}: {e}")
            return False

    async def toggle_trigger(self, trigger_id: int, is_active: bool) -> bool:
        """
        Включение/выключение триггера.

        Args:
            trigger_id: ID триггера
            is_active: Статус активности

        Returns:
            True если обновление успешно
        """
        try:
            success = self.repository.toggle_trigger(trigger_id, is_active)

            # Инвалидируем кеш
            self._invalidate_cache()

            if success:
                status = "activated" if is_active else "deactivated"
                self.logger.info(f"Trigger {trigger_id} {status}")
            else:
                self.logger.warning(f"Trigger {trigger_id} not found for toggle")

            return success

        except Exception as e:
            self.logger.error(f"Error toggling trigger {trigger_id}: {e}")
            return False

    async def get_all_triggers(self) -> List[Dict]:
        """
        Получение всех триггеров (для администрирования).

        Returns:
            Список всех триггеров
        """
        try:
            return self.repository.get_all_triggers()
        except Exception as e:
            self.logger.error(f"Error getting all triggers: {e}")
            return []

    async def get_trigger_by_id(self, trigger_id: int) -> Optional[Dict]:
        """
        Получение триггера по ID.

        Args:
            trigger_id: ID триггера

        Returns:
            Данные триггера или None
        """
        try:
            return self.repository.get_trigger_by_id(trigger_id)
        except Exception as e:
            self.logger.error(f"Error getting trigger {trigger_id}: {e}")
            return None

    def _validate_trigger_data(self, data: Dict):
        """Валидация данных триггера"""
        if not data.get('name') or not isinstance(data['name'], str):
            raise ValidationError("Trigger name is required and must be a string")

        if not data.get('pattern') or not isinstance(data['pattern'], str):
            raise ValidationError("Trigger pattern is required and must be a string")

        if len(data['name'].strip()) < 1 or len(data['name']) > 100:
            raise ValidationError("Trigger name must be between 1 and 100 characters")

        if len(data['pattern'].strip()) < 1 or len(data['pattern']) > 500:
            raise ValidationError("Trigger pattern must be between 1 and 500 characters")

        chat_type = data.get('chat_type', 'group')
        if chat_type not in ['group', 'private']:
            raise ValidationError("Chat type must be 'group' or 'private'")

        # Валидация полей реакции
        reaction_type = data.get('reaction_type')
        if reaction_type is not None:
            if not isinstance(reaction_type, str):
                raise ValidationError("Reaction type must be a string")
            if reaction_type not in ['emoji']:
                raise ValidationError("Reaction type must be 'emoji'")

            # action_data обязательно при наличии reaction_type
            if not data.get('action_data') or not isinstance(data['action_data'], str):
                raise ValidationError("Action data is required when reaction type is specified")

            if len(data['action_data'].strip()) < 1 or len(data['action_data']) > 100:
                raise ValidationError("Action data must be between 1 and 100 characters")

    def _validate_regex_pattern(self, pattern: str):
        """Валидация регулярного выражения"""
        try:
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        except re.error as e:
            raise ValidationError(f"Invalid regex pattern: {e}")

    def _should_use_cache(self) -> bool:
        """Проверка необходимости использования кеша"""
        if self._triggers_cache is None or self._last_cache_update is None:
            return False

        time_diff = (datetime.now() - self._last_cache_update).total_seconds()
        return time_diff < self._cache_ttl_seconds

    def _invalidate_cache(self):
        """Инвалидация кеша"""
        self._triggers_cache = None
        self._last_cache_update = None

    async def clear_cache(self):
        """Очистка кеша"""
        self._invalidate_cache()
        self.logger.debug("Trigger cache cleared")
"""
Маршрутизатор сообщений по типам с учетом прав доступа.
Отвечает за разделение обработки различных типов сообщений.
"""

import re
import logging
from typing import Dict, List, Callable, Pattern, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from .permissions import UserRole, permission_manager
from services.trigger_service import TriggerService


class MessageHandlerConfig:
    """Конфигурация обработчика сообщений"""
    def __init__(self, handler: Callable, required_role: UserRole = UserRole.USER,
                 priority: int = 0, description: str = ""):
        self.handler = handler
        self.required_role = required_role
        self.priority = priority  # Приоритет для сортировки (выше = раньше)
        self.description = description


class MessageTypeRouter:
    """
    Маршрутизатор сообщений по типам.

    Обеспечивает:
    - Разделение обработки по типам контента
    - Регистрацию обработчиков с учетом прав
    - Приоритетную обработку сообщений
    - Валидацию доступа к обработчикам
    """

    def __init__(self, trigger_service: Optional[TriggerService] = None):
        self.logger = logging.getLogger(__name__)
        self.trigger_service = trigger_service

        # Обработчики текстовых сообщений (с паттернами)
        self.text_handlers: Dict[Pattern, MessageHandlerConfig] = {}

        # Обработчики медиа-сообщений
        self.media_handlers: Dict[str, MessageHandlerConfig] = {}
        self.voice_handlers: List[MessageHandlerConfig] = []
        self.audio_handlers: List[MessageHandlerConfig] = []
        self.document_handlers: List[MessageHandlerConfig] = []
        self.video_handlers: List[MessageHandlerConfig] = []
        self.photo_handlers: List[MessageHandlerConfig] = []

        # Обработчики callback запросов
        self.callback_handlers: Dict[str, MessageHandlerConfig] = {}

        # Обработчики инлайновых запросов
        self.inline_handlers: List[MessageHandlerConfig] = []

    def register_text_handler(self, pattern: str, handler: Callable,
                            required_role: UserRole = UserRole.USER,
                            priority: int = 0, description: str = ""):
        """
        Регистрация обработчика текстовых сообщений.

        Args:
            pattern: Регулярное выражение для сопоставления текста
            handler: Функция обработчик
            required_role: Требуемая роль
            priority: Приоритет (выше = обрабатывается раньше)
            description: Описание обработчика
        """
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            config = MessageHandlerConfig(handler, required_role, priority, description)
            self.text_handlers[compiled_pattern] = config
            self.logger.debug(f"Registered text handler: {pattern} (role: {required_role.value})")
        except re.error as e:
            self.logger.error(f"Invalid regex pattern '{pattern}': {e}")

    def register_media_handler(self, media_type: str, handler: Callable,
                             required_role: UserRole = UserRole.USER, description: str = ""):
        """
        Регистрация обработчика медиа-сообщений.

        Args:
            media_type: Тип медиа (photo, video, audio, document, voice)
            handler: Функция обработчик
            required_role: Требуемая роль
            description: Описание обработчика
        """
        config = MessageHandlerConfig(handler, required_role, description=description)

        if media_type == 'photo':
            self.photo_handlers.append(config)
        elif media_type == 'video':
            self.video_handlers.append(config)
        elif media_type == 'audio':
            self.audio_handlers.append(config)
        elif media_type == 'document':
            self.document_handlers.append(config)
        elif media_type == 'voice':
            self.voice_handlers.append(config)
        else:
            self.media_handlers[media_type] = config

        self.logger.debug(f"Registered media handler: {media_type} (role: {required_role.value})")

    def register_callback_handler(self, callback_pattern: str, handler: Callable,
                                required_role: UserRole = UserRole.USER, description: str = ""):
        """
        Регистрация обработчика callback запросов.

        Args:
            callback_pattern: Паттерн callback данных
            handler: Функция обработчик
            required_role: Требуемая роль
            description: Описание обработчика
        """
        config = MessageHandlerConfig(handler, required_role, description=description)
        self.callback_handlers[callback_pattern] = config
        self.logger.debug(f"Registered callback handler: {callback_pattern} (role: {required_role.value})")

    def register_inline_handler(self, handler: Callable,
                              required_role: UserRole = UserRole.USER, description: str = ""):
        """
        Регистрация обработчика инлайновых запросов.

        Args:
            handler: Функция обработчик
            required_role: Требуемая роль
            description: Описание обработчика
        """
        config = MessageHandlerConfig(handler, required_role, description=description)
        self.inline_handlers.append(config)
        self.logger.debug(f"Registered inline handler (role: {required_role.value})")

    async def route_text_message(self, update: Update, context: ContextTypes) -> bool:
        """
        Маршрутизация текстовых сообщений.

        Args:
            update: Обновление от Telegram
            context: Контекст бота

        Returns:
            True если сообщение было обработано
        """
        if not update.message or not update.message.text:
            return False

        text = update.message.text.strip()
        if not text:
            return False

        # Определяем тип чата
        chat_type = "private" if update.message.chat.type == "private" else "group"

        # Проверяем триггеры только в групповых чатах
        if chat_type == "group" and self.trigger_service:
            try:
                matched_triggers = await self.trigger_service.check_triggers(text, chat_type)
                if matched_triggers:
                    await self._execute_trigger_actions(matched_triggers, update, context)
            except Exception as e:
                self.logger.error(f"Error checking triggers: {e}")

        # Получение роли пользователя
        user_role = await self._get_user_role(update)

        # Сортировка обработчиков по приоритету (выше приоритет = раньше)
        sorted_handlers = sorted(
            self.text_handlers.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )

        # Поиск подходящего обработчика
        for pattern, config in sorted_handlers:
            if pattern.search(text):
                # Проверка прав доступа
                if not self._check_permission(user_role, config.required_role):
                    continue

                try:
                    self.logger.debug(f"Routing text message to handler: {config.description}")
                    await config.handler(update, context)
                    return True
                except Exception as e:
                    self.logger.error(f"Error in text handler: {e}")
                    return False

        return False

    async def route_media_message(self, update: Update, context: ContextTypes) -> bool:
        """
        Маршрутизация медиа-сообщений.

        Args:
            update: Обновление от Telegram
            context: Контекст бота

        Returns:
            True если сообщение было обработано
        """
        if not update.message:
            return False

        message = update.message
        user_role = await self._get_user_role(update)

        # Определение типа медиа и выбор обработчиков
        handlers_to_check = []

        if message.photo:
            handlers_to_check = self.photo_handlers
        elif message.video:
            handlers_to_check = self.video_handlers
        elif message.audio:
            handlers_to_check = self.audio_handlers
        elif message.voice:
            handlers_to_check = self.voice_handlers
        elif message.document:
            handlers_to_check = self.document_handlers

        # Обработка первым доступным обработчиком
        for config in handlers_to_check:
            if self._check_permission(user_role, config.required_role):
                try:
                    self.logger.debug(f"Routing media message to handler: {config.description}")
                    await config.handler(update, context)
                    return True
                except Exception as e:
                    self.logger.error(f"Error in media handler: {e}")
                    return False

        return False

    async def route_voice_message(self, update: Update, context: ContextTypes) -> bool:
        """
        Маршрутизация голосовых сообщений.

        Args:
            update: Обновление от Telegram
            context: Контекст бота

        Returns:
            True если сообщение было обработано
        """
        if not update.message or not update.message.voice:
            return False

        user_role = await self._get_user_role(update)

        for config in self.voice_handlers:
            if self._check_permission(user_role, config.required_role):
                try:
                    self.logger.debug(f"Routing voice message to handler: {config.description}")
                    await config.handler(update, context)
                    return True
                except Exception as e:
                    self.logger.error(f"Error in voice handler: {e}")
                    return False

        return False

    async def route_callback(self, update: Update, context: ContextTypes) -> bool:
        """
        Маршрутизация callback запросов.

        Args:
            update: Обновление от Telegram
            context: Контекст бота

        Returns:
            True если callback был обработан
        """
        if not update.callback_query or not update.callback_query.data:
            return False

        callback_data = update.callback_query.data
        user_role = await self._get_user_role(update)

        # Поиск точного совпадения
        if callback_data in self.callback_handlers:
            config = self.callback_handlers[callback_data]
            if self._check_permission(user_role, config.required_role):
                try:
                    self.logger.debug(f"Routing callback to handler: {config.description}")
                    await config.handler(update, context)
                    return True
                except Exception as e:
                    self.logger.error(f"Error in callback handler: {e}")
                    return False

        # Поиск по префиксу
        for pattern, config in self.callback_handlers.items():
            if callback_data.startswith(pattern) and pattern != callback_data:
                if self._check_permission(user_role, config.required_role):
                    try:
                        self.logger.debug(f"Routing callback (prefix) to handler: {config.description}")
                        await config.handler(update, context)
                        return True
                    except Exception as e:
                        self.logger.error(f"Error in callback handler: {e}")
                        return False

        self.logger.debug(f"No handler found for callback: {callback_data}")
        return False

    async def route_inline_query(self, update: Update, context: ContextTypes) -> bool:
        """
        Маршрутизация инлайновых запросов.

        Args:
            update: Обновление от Telegram
            context: Контекст бота

        Returns:
            True если запрос был обработан
        """
        if not update.inline_query:
            return False

        user_role = await self._get_user_role(update)

        for config in self.inline_handlers:
            if self._check_permission(user_role, config.required_role):
                try:
                    self.logger.debug(f"Routing inline query to handler: {config.description}")
                    await config.handler(update, context)
                    return True
                except Exception as e:
                    self.logger.error(f"Error in inline handler: {e}")
                    return False

        return False

    async def _get_user_role(self, update) -> UserRole:
        """Получение роли пользователя"""
        try:
            user = update.effective_user
            if user:
                # Интеграция с permission_manager для получения эффективной роли
                # Попытка получить реальный конфиг из Application
                try:
                    from .application import app_instance
                    if app_instance and hasattr(app_instance, 'config'):
                        config = app_instance.config
                    else:
                        # Создаем минимальный конфиг для работы permission_manager
                        class MinimalConfig:
                            def __init__(self):
                                self.bot_config = MinimalBotConfig()

                        class MinimalBotConfig:
                            def __init__(self):
                                self.super_admin_ids = []
                                self.admin_ids = []
                                self.moderator_ids = []

                        config = MinimalConfig()
                except ImportError:
                    # Создаем минимальный конфиг если Application недоступен
                    class MinimalConfig:
                        def __init__(self):
                            self.bot_config = MinimalBotConfig()

                    class MinimalBotConfig:
                        def __init__(self):
                            self.super_admin_ids = []
                            self.admin_ids = []
                            self.moderator_ids = []

                    config = MinimalConfig()

                return await permission_manager.get_effective_role(update, user.id, config)
            return UserRole.USER
        except Exception as e:
            self.logger.error(f"Error getting user role: {e}")
            return UserRole.USER

    def _check_permission(self, user_role: UserRole, required_role: UserRole) -> bool:
        """Проверка прав доступа"""
        # permission_manager.has_permission проверяет наличие required_role у user_role
        # Но нам нужно проверить, что user_role >= required_role
        # Для этого сравниваем приоритеты ролей
        role_priority = {
            UserRole.SUPER_ADMIN: 4,
            UserRole.ADMIN: 3,
            UserRole.MODERATOR: 2,
            UserRole.USER: 1
        }

        user_priority = role_priority.get(user_role, 0)
        required_priority = role_priority.get(required_role, 0)

        return user_priority >= required_priority

    def get_registered_handlers_count(self) -> Dict[str, int]:
        """Получение количества зарегистрированных обработчиков"""
        return {
            'text': len(self.text_handlers),
            'media': len(self.media_handlers),
            'voice': len(self.voice_handlers),
            'audio': len(self.audio_handlers),
            'document': len(self.document_handlers),
            'video': len(self.video_handlers),
            'photo': len(self.photo_handlers),
            'callback': len(self.callback_handlers),
            'inline': len(self.inline_handlers)
        }

# Глобальный экземпляр маршрутизатора
message_router = MessageTypeRouter()

def create_message_router(trigger_service: Optional[TriggerService] = None) -> MessageTypeRouter:
    """Создание экземпляра маршрутизатора сообщений"""
    return MessageTypeRouter(trigger_service)

    async def _execute_trigger_actions(self, matched_triggers: List[Dict], update: Update, context: ContextTypes):
        """
        Выполнение действий сработавших триггеров.

        Args:
            matched_triggers: Список сработавших триггеров
            update: Обновление от Telegram
            context: Контекст бота
        """
        if not self.trigger_service:
            return

        try:
            chat_id = update.message.chat_id
            message_text = update.message.text

            # Получаем действия для выполнения
            actions = await self.trigger_service.execute_trigger_actions(
                matched_triggers, chat_id, message_text, update.message.message_id
            )

            # Выполняем действия с учетом приоритета для реакций
            reaction_actions = [a for a in actions if a.get('type') == 'reaction']
            other_actions = [a for a in actions if a.get('type') != 'reaction']

            # Обрабатываем реакции по приоритету (только первую реакцию)
            if reaction_actions:
                # Сортируем по trigger_id для детерминированного выбора при равном приоритете
                reaction_actions.sort(key=lambda x: x.get('trigger_id', 0))
                # Выполняем только первую реакцию
                try:
                    await self._perform_trigger_action(reaction_actions[0], update, context)
                except Exception as e:
                    self.logger.error(f"Error performing reaction action: {e}")

            # Выполняем остальные действия
            for action in other_actions:
                try:
                    await self._perform_trigger_action(action, update, context)
                except Exception as e:
                    self.logger.error(f"Error performing trigger action {action.get('type')}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error executing trigger actions: {e}")

    async def _perform_trigger_action(self, action: Dict, update: Update, context: ContextTypes):
        """
        Выполнение конкретного действия триггера.

        Args:
            action: Данные действия
            update: Обновление от Telegram
            context: Контекст бота
        """
        action_type = action.get('type')
        content = action.get('content')

        if action_type == 'text':
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=content,
                reply_to_message_id=update.message.message_id
            )
        elif action_type == 'sticker':
            await context.bot.send_sticker(
                chat_id=update.message.chat_id,
                sticker=content,
                reply_to_message_id=update.message.message_id
            )
        elif action_type == 'gif':
            await context.bot.send_animation(
                chat_id=update.message.chat_id,
                animation=content,
                reply_to_message_id=update.message.message_id
            )
        elif action_type == 'reaction':
            # Реакция на сообщение
            if action.get('reaction_type') == 'emoji' and action.get('message_id'):
                try:
                    # Используем set_reaction для установки реакции
                    await context.bot.set_message_reaction(
                        chat_id=update.message.chat_id,
                        message_id=action['message_id'],
                        reaction=content  # emoji
                    )
                except Exception as e:
                    self.logger.error(f"Failed to set reaction: {e}")

        self.logger.debug(f"Executed trigger action: {action_type} for trigger '{action.get('trigger_name', 'unknown')}'")

    def set_trigger_service(self, trigger_service: TriggerService):
        """
        Установка сервиса триггеров.

        Args:
            trigger_service: Экземпляр TriggerService
        """
        self.trigger_service = trigger_service
        self.logger.info("Trigger service set for message router")
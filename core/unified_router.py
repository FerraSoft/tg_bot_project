"""
Объединенный маршрутизатор для всех типов обновлений.
Интегрирует CommandRouter, MessageTypeRouter и ContextMenuManager.

Архитектура:
- CommandRouter: обработка команд и callback'ов через middleware и проверки прав
- MessageTypeRouter: маршрутизация сообщений по типам контента
- ContextMenuManager: управление контекстными меню и проверка доступности

Алгоритм обработки callback'ов:
1. Проверка роли пользователя и доступности меню
2. Попытка обработки через CommandRouter (новая система)
3. Fallback к MessageTypeRouter при неудаче

Преимущества:
- Централизованная маршрутизация всех типов обновлений
- Гибкая система middleware для команд
- Поддержка ролевой модели доступа
- Легкая расширяемость новыми типами обработчиков
"""

import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from .command_router import CommandRouter
from .message_router import MessageTypeRouter
from .menu_manager import ContextMenuManager
from .permissions import UserRole


class UnifiedMessageRouter:
    """
    Объединенный маршрутизатор для всех типов обновлений.

    Обеспечивает:
    - Единый интерфейс для обработки всех типов сообщений
    - Интеграцию с существующими компонентами
    - Централизованное управление маршрутизацией
    - Логирование и мониторинг
    - Правильную обработку callback'ов через CommandRouter с fallback'ом
    """

    def __init__(self, command_router: CommandRouter,
                 message_router: MessageTypeRouter,
                 menu_manager: ContextMenuManager):
        """
        Инициализация объединенного маршрутизатора.

        Args:
            command_router: Маршрутизатор команд
            message_router: Маршрутизатор типов сообщений
            menu_manager: Менеджер контекстных меню
        """
        self.command_router = command_router
        self.message_router = message_router
        self.menu_manager = menu_manager
        self.logger = logging.getLogger(__name__)

    async def handle_update(self, update: Update, context: ContextTypes) -> bool:
        """
        Единая точка входа для обработки всех типов обновлений.

        Args:
            update: Обновление от Telegram
            context: Контекст бота

        Returns:
            True если обновление было успешно обработано
        """
        try:
            # Определение типа обновления и маршрутизация
            if update.message:
                return await self._handle_message_update(update, context)
            elif update.callback_query:
                return await self._handle_callback_update(update, context)
            elif update.inline_query:
                return await self._handle_inline_query(update, context)
            elif update.chosen_inline_result:
                return await self._handle_chosen_inline_result(update, context)
            elif update.chat_member:
                return await self._handle_chat_member_update(update, context)
            else:
                self.logger.debug("Unhandled update type")
                return False

        except Exception as e:
            self.logger.error(f"Error in unified router: {e}", exc_info=True)
            return False

    async def _handle_message_update(self, update: Update, context: ContextTypes) -> bool:
        """
        Обработка обновлений типа message.

        Args:
            update: Обновление с сообщением
            context: Контекст бота

        Returns:
            True если сообщение обработано
        """
        message = update.message

        # Проверка типа сообщения
        if message.text and message.text.startswith('/'):
            # Команды обрабатываются через CommandRouter
            self.logger.debug("Routing to command router")
            await self.command_router.handle_command(update, context)
            return True

        elif message.text:
            # Текстовые сообщения через MessageTypeRouter
            self.logger.debug("Routing text message")
            return await self.message_router.route_text_message(update, context)

        elif message.voice:
            # Голосовые сообщения
            self.logger.debug("Routing voice message")
            return await self.message_router.route_voice_message(update, context)

        elif message.photo or message.video or message.audio or message.document:
            # Медиа-сообщения
            self.logger.debug("Routing media message")
            return await self.message_router.route_media_message(update, context)

        else:
            self.logger.debug("Unhandled message type")
            return False

    async def _handle_callback_update(self, update: Update, context: ContextTypes) -> bool:
        """
        Обработка callback запросов с учетом контекста меню.

        Алгоритм обработки:
        1. Получение роли пользователя для проверки прав доступа
        2. Проверка доступности меню (для запросов menu_*)
        3. Попытка обработки через CommandRouter (новая система маршрутизации)
        4. Fallback к MessageTypeRouter при неудаче

        Args:
            update: Обновление с callback
            context: Контекст бота

        Returns:
            True если callback обработан
        """
        callback_data = update.callback_query.data
        self.logger.debug(f"Processing callback: {callback_data}")

        # Получение роли пользователя
        user_role = await self._get_user_role(update)

        # Проверка доступности меню (если это запрос меню)
        if callback_data.startswith('menu_'):
            if not self.menu_manager.is_menu_available(callback_data, user_role):
                await update.callback_query.answer("Недостаточно прав доступа")
                return True

        # Сначала пытаемся маршрутизировать через CommandRouter (новая система)
        try:
            result = await self.command_router.handle_callback(update, context)
            if result:
                return True
        except Exception as e:
            self.logger.error(f"Error in CommandRouter callback handler: {e}")

        # Fallback к MessageTypeRouter
        return await self.message_router.route_callback(update, context)

    async def _handle_inline_query(self, update: Update, context: ContextTypes) -> bool:
        """
        Обработка инлайновых запросов.

        Args:
            update: Инлайновый запрос
            context: Контекст бота

        Returns:
            True если запрос обработан
        """
        self.logger.debug("Processing inline query")
        return await self.message_router.route_inline_query(update, context)

    async def _handle_chosen_inline_result(self, update: Update, context: ContextTypes) -> bool:
        """
        Обработка выбора результата инлайнового запроса.

        Args:
            update: Выбранный результат
            context: Контекст бота

        Returns:
            True если результат обработан
        """
        self.logger.debug("Processing chosen inline result")
        # Здесь может быть дополнительная логика обработки выбора
        return True

    async def _handle_chat_member_update(self, update: Update, context: ContextTypes) -> bool:
        """
        Обработка обновлений участников чата.

        Args:
            update: Обновление участников чата
            context: Контекст бота

        Returns:
            True если обновление обработано
        """
        self.logger.debug("Processing chat member update")
        # Здесь может быть логика обработки вступления/выхода участников
        return True

    async def _get_user_role(self, update: Update) -> UserRole:
        """
        Получение роли пользователя для данного обновления.

        Args:
            update: Обновление от Telegram

        Returns:
            Роль пользователя
        """
        try:
            user = update.effective_user
            if user:
                # Использование существующей логики определения роли
                from .permissions import permission_manager
                # Попытка получить config из Application
                try:
                    from .application import app_instance
                    if app_instance and hasattr(app_instance, 'config'):
                        config = app_instance.config
                    else:
                        # Создаем минимальный конфиг
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

                return await permission_manager.get_effective_role(
                    update, user.id, config
                )
            return UserRole.USER
        except Exception as e:
            self.logger.error(f"Error getting user role: {e}")
            return UserRole.USER

    async def get_menu_for_user(self, menu_id: str, user_role: UserRole,
                               **context) -> Optional[object]:
        """
        Получение меню для пользователя через ContextMenuManager.

        Args:
            menu_id: Идентификатор меню
            user_role: Роль пользователя
            **context: Дополнительный контекст

        Returns:
            Объект меню или None
        """
        # Определение типа чата для контекстного построения меню
        chat_type = context.get('chat_type', 'private')
        context['chat_type'] = chat_type

        return await self.menu_manager.get_menu_for_user(menu_id, user_role, **context)

    def get_registered_handlers_count(self) -> dict:
        """
        Получение статистики зарегистрированных обработчиков.

        Returns:
            Словарь со статистикой
        """
        command_handlers = len(self.command_router.command_handlers)
        callback_handlers = len(self.command_router.callback_handlers)
        message_handlers = self.message_router.get_registered_handlers_count()

        return {
            'command_handlers': command_handlers,
            'callback_handlers': callback_handlers,
            'message_handlers': message_handlers,
            'total': command_handlers + callback_handlers + sum(message_handlers.values())
        }

    def clear_menu_cache(self):
        """Очистка кеша меню"""
        self.menu_manager.clear_cache()


def create_unified_router(command_router: CommandRouter,
                         message_router: MessageTypeRouter,
                         menu_manager: ContextMenuManager) -> UnifiedMessageRouter:
    """
    Создание объединенного маршрутизатора.

    Args:
        command_router: Маршрутизатор команд
        message_router: Маршрутизатор типов сообщений
        menu_manager: Менеджер меню

    Returns:
        UnifiedMessageRouter: Настроенный объединенный маршрутизатор
    """
    return UnifiedMessageRouter(command_router, message_router, menu_manager)
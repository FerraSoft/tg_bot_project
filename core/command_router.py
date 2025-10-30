"""
Единый маршрутизатор команд для централизованной обработки.
Отвечает за маршрутизацию команд к соответствующим обработчикам.
"""

import logging
from typing import Dict, List, Callable, Awaitable, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from .middleware import create_middleware_chain
from .permissions import permission_manager, UserRole


class CommandHandler:
    """
    Описание обработчика команды с метаданными.
    """

    def __init__(self, handler: Callable, required_role: UserRole = UserRole.USER,
                 description: str = "", category: str = "general"):
        self.handler = handler
        self.required_role = required_role
        self.description = description
        self.category = category


class CommandRouter:
    """
    Центральный маршрутизатор команд бота.

    Обеспечивает:
    - Регистрацию обработчиков команд
    - Автоматическую маршрутизацию
    - Проверку прав доступа
    - Обработку через middleware
    """

    def __init__(self, config, metrics=None):
        """
        Инициализация маршрутизатора.

        Args:
            config: Конфигурация приложения
            metrics: Сборщик метрик
        """
        self.config = config
        self.metrics = metrics
        self.logger = logging.getLogger(__name__)

        # Создаем цепочку middleware
        self.middleware_chain = create_middleware_chain(config, metrics)

        # Регистрируемые обработчики
        self.command_handlers: Dict[str, CommandHandler] = {}
        self.callback_handlers: Dict[str, CommandHandler] = {}
        self.message_handlers: Dict[str, CommandHandler] = {}

        # Категории команд
        self.categories = {
            'user': 'Пользовательские команды',
            'moderation': 'Модерация',
            'admin': 'Администрирование',
            'system': 'Системные команды',
            'games': 'Игры'
        }

    def register_command_handler(self, command: str, handler: Callable,
                               required_role: UserRole = UserRole.USER,
                               description: str = "", category: str = "user"):
        """
        Регистрация обработчика команды.

        Args:
            command: Название команды (без слеша)
            handler: Функция обработчик
            required_role: Минимальная требуемая роль
            description: Описание команды
            category: Категория команды
        """
        self.command_handlers[command] = CommandHandler(
            handler=handler,
            required_role=required_role,
            description=description,
            category=category
        )
        self.logger.debug(f"Registered command handler: /{command} -> {handler.__name__}")

    def register_callback_handler(self, callback_data: str, handler: Callable,
                                required_role: UserRole = UserRole.USER,
                                description: str = "", category: str = "user"):
        """
        Регистрация обработчика callback запросов.

        Args:
            callback_data: Callback data
            handler: Функция обработчик
            required_role: Минимальная требуемая роль
            description: Описание
            category: Категория
        """
        self.callback_handlers[callback_data] = CommandHandler(
            handler=handler,
            required_role=required_role,
            description=description,
            category=category
        )

    def register_message_handler(self, message_type: str, handler: Callable,
                               required_role: UserRole = UserRole.USER,
                               description: str = "", category: str = "user"):
        """
        Регистрация обработчика сообщений.

        Args:
            message_type: Тип сообщения (text, voice, audio, etc.)
            handler: Функция обработчик
            required_role: Минимальная требуемая роль
            description: Описание
            category: Категория
        """
        self.message_handlers[message_type] = CommandHandler(
            handler=handler,
            required_role=required_role,
            description=description,
            category=category
        )

    async def handle_command(self, update: Update, context: ContextTypes):
        """
        Обработка команды через middleware и маршрутизацию.

        Args:
            update: Обновление от Telegram
            context: Контекст бота
        """
        # Извлекаем команду из сообщения
        command = self._extract_command(update)
        if not command:
            return

        # Находим обработчик
        handler_info = self.command_handlers.get(command)
        if not handler_info:
            await self._send_unknown_command(update, command)
            return

        # Создаем обертку обработчика с проверкой роли
        async def wrapped_handler(update: Update, context: ContextTypes):
            await handler_info.handler(update, context)

        # Обрабатываем через middleware
        await self.middleware_chain.process_request(update, context, wrapped_handler)

    async def handle_callback(self, update: Update, context: ContextTypes):
        """
        Обработка callback запросов.

        Args:
            update: Обновление от Telegram
            context: Контекст бота
        """
        if not update.callback_query:
            return

        callback_data = update.callback_query.data
        if not callback_data:
            return

        self.logger.debug(f"Processing callback: {callback_data}")

        # Находим обработчик (точное совпадение или префикс)
        handler_info = None

        # Сначала ищем точное совпадение
        if callback_data in self.callback_handlers:
            handler_info = self.callback_handlers[callback_data]
            self.logger.debug(f"Found exact match for callback: {callback_data}")
        else:
            # Ищем по префиксу
            for prefix, handler in self.callback_handlers.items():
                if callback_data.startswith(prefix):
                    handler_info = handler
                    self.logger.debug(f"Found prefix match for callback: {callback_data} -> {prefix}")
                    break

        if not handler_info:
            self.logger.warning(f"No handler found for callback: {callback_data}")
            await update.callback_query.answer("Неизвестное действие")
            return

        self.logger.debug(f"Found handler for callback {callback_data}: {handler_info.handler.__name__}")

        # Создаем обертку обработчика
        async def wrapped_handler(update: Update, context: ContextTypes):
            await handler_info.handler(update, context)

        # Обрабатываем через middleware
        await self.middleware_chain.process_request(update, context, wrapped_handler)

    async def handle_message(self, update: Update, context: ContextTypes, message_type: str = "text"):
        """
        Обработка сообщений.

        Args:
            update: Обновление от Telegram
            context: Контекст бота
            message_type: Тип сообщения
        """
        handler_info = self.message_handlers.get(message_type)
        if not handler_info:
            return

        # Создаем обертку обработчика
        async def wrapped_handler(update: Update, context: ContextTypes):
            await handler_info.handler(update, context)

        # Обрабатываем через middleware
        await self.middleware_chain.process_request(update, context, wrapped_handler)

    def _extract_command(self, update: Update) -> Optional[str]:
        """
        Извлечение команды из обновления.

        Args:
            update: Обновление от Telegram

        Returns:
            Название команды или None
        """
        if not update.message or not update.message.text:
            return None

        text = update.message.text.strip()
        if not text.startswith('/'):
            return None

        # Извлекаем команду (убираем слеш и username бота)
        command = text.split()[0][1:].split('@')[0]
        return command

    async def _send_unknown_command(self, update: Update, command: str):
        """
        Отправка сообщения о неизвестной команде.

        Args:
            update: Обновление от Telegram
            command: Название неизвестной команды
        """
        try:
            message = f"❌ Неизвестная команда: /{command}\n\nИспользуйте /help для списка доступных команд."
            if update.message:
                await update.message.reply_text(message)
        except Exception as e:
            self.logger.error(f"Failed to send unknown command message: {e}")

    def get_registered_commands(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение списка зарегистрированных команд сгруппированных по категориям.

        Returns:
            Словарь категорий с командами
        """
        result = {}

        for category, category_name in self.categories.items():
            result[category] = {
                'name': category_name,
                'commands': {}
            }

        for command, handler_info in self.command_handlers.items():
            category = handler_info.category
            if category not in result:
                result[category] = {'name': category, 'commands': {}}

            result[category]['commands'][command] = {
                'description': handler_info.description,
                'required_role': handler_info.required_role.value
            }

        return result

    def get_available_commands_for_role(self, user_role: UserRole) -> List[str]:
        """
        Получение списка команд доступных для роли.

        Args:
            user_role: Роль пользователя

        Returns:
            Список доступных команд
        """
        available_commands = []

        for command, handler_info in self.command_handlers.items():
            if permission_manager.can_execute_command(user_role, command):
                available_commands.append(command)

        return sorted(available_commands)

    def get_command_info(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о команде.

        Args:
            command: Название команды

        Returns:
            Информация о команде или None
        """
        handler_info = self.command_handlers.get(command)
        if not handler_info:
            return None

        return {
            'command': command,
            'description': handler_info.description,
            'required_role': handler_info.required_role.value,
            'category': handler_info.category
        }


# Функция для создания настроенного маршрутизатора
def create_command_router(config, metrics=None):
    """
    Создание и настройка маршрутизатора команд.

    Args:
        config: Конфигурация приложения
        metrics: Сборщик метрик

    Returns:
        CommandRouter: Настроенный маршрутизатор
    """
    return CommandRouter(config, metrics)
"""
Обработчики команд для AI интеграций.
Реализует взаимодействие пользователей с AI сервисами.
"""

import logging
from typing import Dict, Any, List
from aiogram import types
from aiogram.dispatcher import FSMContext

from services.ai_service import ai_integration
from core.permissions import permission_manager, UserRole
from utils.validators import InputValidator


class AIHandlers:
    """
    Класс для обработки AI команд.
    Управляет взаимодействием с различными AI сервисами.
    """

    def __init__(self, bot, user_service, message_service=None):
        """
        Инициализация обработчиков AI.

        Args:
            bot: Экземпляр бота
            user_service: Сервис управления пользователями
            message_service: Сервис сообщений (опционально)
        """
        self.bot = bot
        self.user_service = user_service
        self.message_service = message_service
        self.logger = logging.getLogger(__name__)

        # Состояния для FSM
        self.ai_states = {}

    async def handle_gigachat_command(self, message: types.Message):
        """
        Обработка команды /gigachat [запрос]

        Args:
            message: Сообщение от пользователя
        """
        user_id = message.from_user.id
        query = message.get_args()

        if not query:
            await message.reply(
                "🤖 <b>GigaChat</b>\n\n"
                "Используйте: /gigachat <i>ваш запрос</i>\n\n"
                "Примеры:\n"
                "• /gigachat Расскажи о погоде в Москве\n"
                "• /gigachat Помоги написать поздравление\n"
                "• /gigachat Объясни как работает ИИ",
                parse_mode='HTML'
            )
            return

        # Проверка прав доступа
        if not await self._check_ai_access(user_id):
            await message.reply("❌ У вас нет доступа к AI функциям.")
            return

        # Показываем индикатор ввода
        await self.bot.send_chat_action(message.chat.id, "typing")

        try:
            response = await ai_integration.generate_response('gigachat', query, user_id)
            await message.reply(f"🤖 <b>GigaChat:</b>\n\n{response}", parse_mode='HTML')

        except Exception as e:
            self.logger.error(f"Ошибка в GigaChat обработчике: {e}")
            await message.reply("❌ Произошла ошибка при обработке запроса. Попробуйте позже.")

    async def handle_yandexgpt_command(self, message: types.Message):
        """
        Обработка команды /yandexgpt [запрос]

        Args:
            message: Сообщение от пользователя
        """
        user_id = message.from_user.id
        query = message.get_args()

        if not query:
            await message.reply(
                "🧠 <b>YandexGPT</b>\n\n"
                "Используйте: /yandexgpt <i>ваш запрос</i>\n\n"
                "Особенности:\n"
                "• Персонализированные рекомендации\n"
                "• Анализ поведения пользователя\n"
                "• Интеллектуальные ответы\n\n"
                "Примеры:\n"
                "• /yandexgpt Какие фильмы мне посмотреть?\n"
                "• /yandexgpt Помоги с выбором подарка\n"
                "• /yandexgpt Анализ моих интересов",
                parse_mode='HTML'
            )
            return

        # Проверка прав доступа
        if not await self._check_ai_access(user_id):
            await message.reply("❌ У вас нет доступа к AI функциям.")
            return

        # Показываем индикатор ввода
        await self.bot.send_chat_action(message.chat.id, "typing")

        try:
            response = await ai_integration.generate_response('yandexgpt', query, user_id)
            await message.reply(f"🧠 <b>YandexGPT:</b>\n\n{response}", parse_mode='HTML')

        except Exception as e:
            self.logger.error(f"Ошибка в YandexGPT обработчике: {e}")
            await message.reply("❌ Произошла ошибка при обработке запроса. Попробуйте позже.")

    async def handle_max_sync_command(self, message: types.Message):
        """
        Обработка команды /max_sync

        Args:
            message: Сообщение от пользователя
        """
        user_id = message.from_user.id

        # Проверка прав доступа
        if not await self._check_ai_access(user_id):
            await message.reply("❌ У вас нет доступа к AI функциям.")
            return

        await message.reply(
            "💬 <b>MAX Интеграция</b>\n\n"
            "Функция синхронизации с MAX мессенджером находится в разработке.\n\n"
            "Пока вы можете использовать:\n"
            "• /gigachat - для интеллектуальных ответов\n"
            "• /yandexgpt - для персональных рекомендаций\n"
            "• /ai_help - для справки по AI функциям",
            parse_mode='HTML'
        )

    async def handle_ai_help_command(self, message: types.Message):
        """
        Обработка команды /ai_help

        Args:
            message: Сообщение от пользователя
        """
        user_id = message.from_user.id

        # Получаем доступные сервисы
        available_services = await ai_integration.get_available_services()

        help_text = (
            "🤖 <b>AI Помощники в \"Бот в помощь\"</b>\n\n"
            "Уникальная фишка: <b>Мульти-помощник с российскими AI</b>\n\n"
            "<b>Доступные команды:</b>\n\n"
        )

        if 'gigachat' in available_services:
            help_text += "🤖 /gigachat <запрос> - Интеллектуальный помощник GigaChat\n"
        else:
            help_text += "🤖 /gigachat - Сервис временно недоступен\n"

        if 'yandexgpt' in available_services:
            help_text += "🧠 /yandexgpt <запрос> - Персональный AI YandexGPT\n"
        else:
            help_text += "🧠 /yandexgpt - Сервис временно недоступен\n"

        help_text += "💬 /max_sync - Синхронизация с MAX (в разработке)\n"
        help_text += "❓ /ai_help - Эта справка\n\n"

        help_text += "<b>Особенности:</b>\n"
        help_text += "• Полностью на русском языке\n"
        help_text += "• Интеграция с российскими AI платформами\n"
        help_text += "• Персонализация ответов\n"
        help_text += "• Кеширование для быстрого ответа\n\n"

        help_text += "<b>Примеры использования:</b>\n"
        help_text += "• /gigachat Как приготовить борщ?\n"
        help_text += "• /yandexgpt Какие книги почитать?\n"
        help_text += "• /gigachat Объясни теорию относительности\n"

        await message.reply(help_text, parse_mode='HTML')

    async def handle_ai_message(self, message: types.Message):
        """
        Обработка сообщений для AI (если пользователь в режиме AI чата)

        Args:
            message: Сообщение от пользователя
        """
        user_id = message.from_user.id

        # Проверяем, находится ли пользователь в режиме AI чата
        if user_id not in self.ai_states:
            return  # Не обрабатываем как AI сообщение

        ai_state = self.ai_states[user_id]
        service_name = ai_state.get('service', 'gigachat')

        # Проверка прав доступа
        if not await self._check_ai_access(user_id):
            await message.reply("❌ У вас нет доступа к AI функциям.")
            return

        # Показываем индикатор ввода
        await self.bot.send_chat_action(message.chat.id, "typing")

        try:
            query = message.text.strip()
            response = await ai_integration.generate_response(service_name, query, user_id)

            service_emoji = {'gigachat': '🤖', 'yandexgpt': '🧠', 'max': '💬'}.get(service_name, '🤖')
            await message.reply(f"{service_emoji} <b>{service_name.title()}:</b>\n\n{response}", parse_mode='HTML')

        except Exception as e:
            self.logger.error(f"Ошибка в AI сообщении: {e}")
            await message.reply("❌ Произошла ошибка при обработке сообщения.")

    async def handle_switch_ai_command(self, message: types.Message):
        """
        Обработка команды переключения AI сервиса

        Args:
            message: Сообщение от пользователя
        """
        user_id = message.from_user.id
        args = message.get_args()

        if not args:
            available = await ai_integration.get_available_services()
            services_text = "\n".join([f"• {s}" for s in available])

            await message.reply(
                "🔄 <b>Переключение AI сервиса</b>\n\n"
                f"Используйте: /switch_ai <i>сервис</i>\n\n"
                f"<b>Доступные сервисы:</b>\n{services_text}\n\n"
                f"<b>Примеры:</b>\n"
                f"• /switch_ai gigachat\n"
                f"• /switch_ai yandexgpt",
                parse_mode='HTML'
            )
            return

        service_name = args.lower().strip()

        # Проверка прав доступа
        if not await self._check_ai_access(user_id):
            await message.reply("❌ У вас нет доступа к AI функциям.")
            return

        # Попытка переключения
        success = await ai_integration.switch_service(user_id, service_name)

        if success:
            # Сохраняем состояние пользователя
            self.ai_states[user_id] = {'service': service_name, 'timestamp': message.date}

            emoji = {'gigachat': '🤖', 'yandexgpt': '🧠', 'max': '💬'}.get(service_name, '🤖')
            await message.reply(
                f"{emoji} <b>AI сервис переключен</b>\n\n"
                f"Теперь используется: <i>{service_name.title()}</i>\n\n"
                f"Все последующие сообщения будут обрабатываться через этот сервис.",
                parse_mode='HTML'
            )
        else:
            await message.reply(f"❌ Сервис '{service_name}' не найден или недоступен.")

    async def _check_ai_access(self, user_id: int) -> bool:
        """
        Проверка доступа пользователя к AI функциям.

        Args:
            user_id: ID пользователя

        Returns:
            True если есть доступ
        """
        try:
            # Получаем роль пользователя
            user_role = await self.user_service.get_user_role_enum_async(user_id)

            # AI функции доступны всем пользователям (USER и выше)
            # В будущем можно добавить специальное разрешение USE_AI_SERVICES
            return user_role in [UserRole.USER, UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]

        except Exception as e:
            self.logger.error(f"Ошибка проверки доступа к AI: {e}")
            return False

    def get_command_handlers(self) -> Dict[str, callable]:
        """
        Получение словаря команд и их обработчиков.

        Returns:
            Словарь команд
        """
        return {
            'gigachat': self.handle_gigachat_command,
            'yandexgpt': self.handle_yandexgpt_command,
            'max_sync': self.handle_max_sync_command,
            'ai_help': self.handle_ai_help_command,
            'switch_ai': self.handle_switch_ai_command
        }

    def get_message_handlers(self) -> List[callable]:
        """
        Получение обработчиков сообщений.

        Returns:
            Список обработчиков сообщений
        """
        return [self.handle_ai_message]
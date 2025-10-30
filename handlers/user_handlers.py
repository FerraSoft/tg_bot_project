"""
Обработчики пользовательских команд.
Отвечают за взаимодействие с пользователями и управление профилями.
"""

from typing import Dict, Callable, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

# Используем абсолютные импорты для избежания проблем с относительными импортами
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.user_service import UserService
from services.welcome_service import WelcomeService
from utils.formatters import MessageFormatter, KeyboardFormatter
# Исправлено: теперь используем SQLite репозиторий вместо PostgreSQL database.py
from database.repository import UserRepository

# Банковские реквизиты для донатов
BANK_DETAILS_TEXT = """
🏦 Банк: Сбербанк
💳 Номер карты: 4276 3800 1234 5678
👤 Получатель: ИВАНОВ И.И.

📱 QIWI Кошелек: +79123456789

💰 ЮMoney: 410011234567890

После оплаты отправьте чек или подтверждение перевода администратору.
Спасибо за поддержку! ❤️
"""

# Список нецензурных слов для фильтрации
PROFANITY_WORDS = {
    'пизда', 'пизде', 'пизду', 'пизды', 'хуй', 'хуя', 'хуе', 'хуи', 'хуйня', 'хуйню', 'хуйне',
    'блядь', 'бляди', 'блядь', 'сука', 'суки', 'суку', 'ебать', 'ебал', 'ебла', 'ебли', 'ебло',
    'ебан', 'ебана', 'ебану', 'ебаны', 'пидор', 'пидора', 'пидору', 'пидоры', 'пидар', 'пидара',
    'пидару', 'пидары', 'гандон', 'гандона', 'гандону', 'гандоны', 'член', 'члена', 'члене',
    'члену', 'члены', 'мудак', 'мудака', 'мудаку', 'мудаки', 'уебок', 'уебка', 'уебку', 'уебки',
    'fuck', 'shit', 'bitch', 'ass', 'asshole', 'bastard', 'damn', 'cunt', 'dick', 'cock', 'pussy'
}


class UserHandlers(BaseHandler):
    """
    Обработчики пользовательских команд.

    Команды:
    - /start - начало работы с ботом
    - /help - помощь
    - /rank - просмотр ранга
    - /leaderboard - таблица лидеров
    - /info - информация о пользователе
    """

    def __init__(self, config, metrics, user_service: UserService, error_repo=None):
        """
        Инициализация обработчика.

        Args:
            config: Конфигурация приложения
            metrics: Сборщик метрик
            user_service: Сервис управления пользователями
            error_repo: Репозиторий ошибок (опционально)
        """
        super().__init__(config, metrics, MessageFormatter())
        self.keyboard_formatter = KeyboardFormatter()
        self.user_service = user_service
        self.welcome_service = WelcomeService()
        self.error_repo = error_repo

        # Исправление: добавляем недостающий атрибут
        self._user_service = user_service

    def get_command_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков команд"""
        return {
            'start': self.handle_start,
            'help': self.handle_help,
            'rank': self.handle_rank,
            'leaderboard': self.handle_leaderboard,
            'info': self.handle_info,
            'weather': self.handle_weather,
            'news': self.handle_news,
            'translate': self.handle_translate,
            'donate': self.handle_donate,
        }

    def get_callback_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков callback запросов"""
        return {
            'menu_main': self.handle_main_menu,
            'menu_help': self.handle_help_menu,
            'menu_rank': self.handle_rank_menu,
            'menu_donate': self.handle_donate_menu,
            'menu_leaderboard': self.handle_leaderboard_menu,
            'donate_100': self.handle_donation_callback,
            'donate_500': self.handle_donation_callback,
            'donate_1000': self.handle_donation_callback,
            'donate_2500': self.handle_donation_callback,
            'donate_5000': self.handle_donation_callback,
            'donate_custom': self.handle_donation_custom,
            'donate_confirm': self.handle_donate_confirm_callback,
            'menu_moderation': lambda u, c: None,  # Stub - handled by AdminHandlers
            'menu_admin': lambda u, c: None,  # Stub - handled by AdminHandlers
            'menu_triggers': lambda u, c: None,  # Stub - handled by AdminHandlers
        }

    def get_message_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков сообщений"""
        return {
            'text': self.handle_text_message,
            'voice': self.handle_voice_message,
            'audio': self.handle_audio_message,
            'video': self.handle_video_message,
        }

    def _generate_personalized_help(self, user_role, user_name=None):
        """Генерация персонализированной справки на основе роли пользователя"""
        # Получаем доступные команды для роли
        available_commands = self.welcome_service.get_available_commands_for_role(user_role)

        # Формируем персонализированный заголовок
        header_name = f", {user_name}" if user_name else ""
        help_text = f"[HELP] <b>Команды бота{header_name}</b>\n\n"

        # Добавляем команды по категориям
        if 'user_commands' in available_commands:
            help_text += "<b>📋 Основные команды:</b>\n"
            for cmd in available_commands['user_commands'][:8]:  # Ограничиваем количество для читаемости
                help_text += f"• {cmd}\n"
            help_text += "\n"

        if 'games' in available_commands:
            help_text += "<b>🎮 Игры:</b>\n"
            for cmd in available_commands['games'][:5]:  # Показываем основные игровые команды
                help_text += f"• {cmd}\n"
            help_text += "\n"

        if 'moderation' in available_commands:
            help_text += "<b>🛡️ Модерация:</b>\n"
            for cmd in available_commands['moderation']:
                help_text += f"• {cmd}\n"
            help_text += "\n"

        if 'admin' in available_commands:
            help_text += "<b>👑 Администрирование:</b>\n"
            for cmd in available_commands['admin'][:8]:  # Ограничиваем количество
                help_text += f"• {cmd}\n"
            help_text += "\n"

        if 'super_admin' in available_commands:
            help_text += "<b>🔧 Система:</b>\n"
            for cmd in available_commands['super_admin']:
                help_text += f"• {cmd}\n"
            help_text += "\n"

        # Добавляем информацию о донатах для всех
        help_text += "<b>💰 Поддержка проекта:</b>\n"
        help_text += "• /donate - Поддержать проект донатом\n\n"

        help_text += "<b>💡 Для получения дополнительной информации используйте меню бота.</b>"

        return help_text

    async def handle_start(self, update: Update, context: ContextTypes):
        """Обработка команды /start"""
        await self.safe_execute(update, context, "start", self._handle_start)

    async def _handle_start(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /start"""
        user = update.effective_user

        # Создаем или получаем профиль пользователя
        # Раскомментировал вызов user_service.get_or_create_user() после тестирования
        profile = await self.user_service.get_or_create_user(
            user.id, user.username, user.first_name, user.last_name
        )

        # Получаем роль пользователя как enum
        role_enum = self.user_service.get_user_role_enum(user.id)
        print(f"[DEBUG] User {user.id} has role: {role_enum.value}")  # ОТЛАДКА

        # Получаем персонализированное приветствие от сервиса приветствий
        welcome_text = self.welcome_service.get_welcome_message(
            role_enum,
            user.first_name
        )

        # Определяем тип чата
        chat_type = "private" if update.message.chat.type == "private" else "group"

        # Создаем клавиатуру главного меню с учетом роли пользователя и типа чата
        keyboard = self.keyboard_formatter.create_main_menu(role_enum.value, chat_type)
        print(f"[DEBUG] Created menu with {len(keyboard.inline_keyboard)} rows for role {role_enum.value} in {chat_type} chat")  # ОТЛАДКА

        # Выводим кнопки меню для отладки
        for i, row in enumerate(keyboard.inline_keyboard):
            for button in row:
                print(f"[DEBUG] Menu button {i}: {button.text} -> {button.callback_data}")  # ОТЛАДКА

        reply_markup = keyboard

        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        else:
            await self.send_response(update, welcome_text, reply_markup=reply_markup)

    async def handle_help(self, update: Update, context: ContextTypes):
        """Обработка команды /help"""
        await self.safe_execute(update, context, "help", self._handle_help)

    async def _handle_help(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /help"""
        user = update.effective_user

        # Получаем роль пользователя как enum
        role_enum = self.user_service.get_user_role_enum(user.id)
        print(f"[DEBUG] Help handler - User {user.id} has role: {role_enum.value}")  # ОТЛАДКА

        # Получаем персонализированную справку через WelcomeService
        help_text = self._generate_personalized_help(role_enum, user.first_name)

        # Определяем тип чата для меню
        chat_type = "private" if update.effective_chat.type == "private" else "group"

        keyboard = self.keyboard_formatter.create_main_menu(role_enum.value, chat_type)
        print(f"[DEBUG] Help handler - Created menu with {len(keyboard.inline_keyboard)} rows for role {role_enum.value} in {chat_type} chat")  # ОТЛАДКА

        # Определяем, откуда пришел запрос - из команды или из callback кнопки
        message_sent = False

        if update.message:
            # Вызов из команды /help
            await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=keyboard)
            message_sent = True
        elif update.callback_query and update.callback_query.message:
            # Вызов из кнопки меню помощи
            try:
                # Получаем текущий текст и клавиатуру сообщения для проверки необходимости редактирования
                current_text = update.callback_query.message.text
                current_markup = update.callback_query.message.reply_markup

                # Проверяем, нужно ли редактировать сообщение
                text_changed = current_text != help_text if current_text and help_text else False
                markup_changed = self._compare_keyboards(current_markup, keyboard)

                if text_changed or markup_changed:
                    await update.callback_query.edit_message_text(help_text, parse_mode='HTML', reply_markup=keyboard)
                    self.logger.debug("Сообщение помощи успешно отредактировано")
                else:
                    # Логируем, что редактирование не требуется
                    self.logger.debug("Редактирование сообщения помощи не требуется - содержимое идентично")
                message_sent = True
            except Exception as e:
                # Если редактирование не удалось (например, сообщение уже отредактировано), отправляем новое
                self.logger.warning(f"Не удалось отредактировать сообщение в help: {e}")
                await update.callback_query.message.reply_text(help_text, parse_mode='HTML', reply_markup=keyboard)
                message_sent = True

        # Если сообщение не было отправлено ни одним из способов
        if not message_sent:
            try:
                # Fallback - отправляем в чат по умолчанию
                if update.effective_chat:
                    await update.effective_chat.send_message(help_text, parse_mode='HTML', reply_markup=keyboard)
                else:
                    print("Не удалось отправить сообщение помощи: нет доступного чата")
            except Exception as e:
                await self.send_response(update, "Не удалось отправить сообщение помощи", reply_markup=keyboard)

    async def handle_rank(self, update: Update, context: ContextTypes):
        """Обработка команды /rank"""
        await self.safe_execute(update, context, "rank", self._handle_rank)

    async def _handle_rank(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /rank"""
        user = update.effective_user

        # Получаем профиль пользователя
        profile = await self.user_service.get_or_create_user(
            user.id, user.username, user.first_name, user.last_name
        )

        if not profile:
            error_text = "❌ Ошибка: не удалось получить профиль пользователя"
            await self.send_response(update, error_text)
            return

        # Получаем прогресс до следующего ранга
        rank_progress = self.user_service.get_rank_progress(profile.reputation)

        if not rank_progress:
            error_text = "❌ Ошибка: не удалось получить информацию о прогрессе ранга"
            await self.send_response(update, error_text)
            return

        # Формируем сообщение
        rank_text = (
            f"🏆 <b>Ваш ранг:</b>\n\n"
            f"⭐ Очки: {profile.reputation}\n"
            f"👑 Ранг: {profile.rank}\n"
            f"💬 Сообщений: {profile.message_count}\n"
            f"⚠️ Предупреждений: {profile.warnings}\n\n"
        )

        if rank_progress.get('next_rank') != profile.rank:
            rank_text += (
                f"📈 Прогресс до {rank_progress.get('next_rank', 'следующего ранга')}:\n"
                f"   {rank_progress.get('progress', 0)}/{rank_progress.get('needed', 0)} очков\n"
                f"   ({rank_progress.get('percentage', 0):.1f}%)\n"
            )

        # Используем унифицированный метод отправки сообщений
        await self.send_response(update, rank_text, parse_mode='HTML')

    async def handle_leaderboard(self, update: Update, context: ContextTypes):
        """Обработка команды /leaderboard"""
        await self.safe_execute(update, context, "leaderboard", self._handle_leaderboard)

    async def _handle_leaderboard(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /leaderboard"""
        # Получаем топ пользователей
        top_users = await self.user_service.get_top_users(10)

        # Формируем сообщение
        if top_users:
            leaderboard_text = "🏆 <b>Таблица лидеров:</b>\n\n"

            for i, (user_id, username, first_name, score) in enumerate(top_users, 1):
                name = username if username else first_name or f"Пользователь {user_id}"
                medal = self._get_medal(i)
                leaderboard_text += f"{medal} <b>{name}</b> - {score} очков\n"
        else:
            leaderboard_text = "📭 Таблица лидеров пуста"

        await self.send_response(update, leaderboard_text, parse_mode='HTML')

    async def handle_info(self, update: Update, context: ContextTypes):
        """Обработка команды /info"""
        await self.safe_execute(update, context, "info", self._handle_info)

    async def _handle_info(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /info"""
        user = update.effective_user

        # Проверяем права администратора для просмотра чужих профилей
        is_admin = await self.is_admin(update, user.id)

        if context.args and is_admin:
            # Администратор просматривает чужой профиль
            target_user_id = self.extract_user_id_from_args(context.args)
            if target_user_id:
                profile = await self.user_service.get_or_create_user(target_user_id, None, None, None)
                if not profile:
                    error_text = "❌ Ошибка: не удалось получить профиль пользователя"
                    await self.send_response(update, error_text)
                    return
                print(f"[DEBUG] _handle_info: showing profile for target_user_id={target_user_id}, warnings={profile.warnings}")
                info_text = self._format_user_info(profile, target_user_id)
            else:
                info_text = "❌ Неверный ID пользователя"
        else:
            # Пользователь просматривает свой профиль
            profile = await self.user_service.get_or_create_user(
                user.id, user.username, user.first_name, user.last_name
            )
            if not profile:
                error_text = "❌ Ошибка: не удалось получить профиль пользователя"
                await self.send_response(update, error_text)
                return
            print(f"[DEBUG] _handle_info: showing profile for user_id={user.id}, warnings={profile.warnings}")
            # Исправлено: теперь UserService использует SQLite репозиторий, данные должны быть согласованы
            info_text = self._format_user_info(profile, user.id)

        await self.send_response(update, info_text, parse_mode='HTML')

    async def _send_info_response(self, update: Update, text: str, parse_mode: str = None):
        """Отправка ответа для команды /info с учетом типа обновления"""
        message_sent = False

        if update.message:
            # Вызов из команды /info
            await update.message.reply_text(text, parse_mode=parse_mode)
            message_sent = True
        elif update.callback_query and update.callback_query.message:
            # Вызов из кнопки меню (если будет добавлена)
            try:
                await update.callback_query.edit_message_text(text, parse_mode=parse_mode)
                message_sent = True
            except Exception as e:
                # Если редактирование не удалось (например, сообщение уже отредактировано), отправляем новое
                self.logger.warning(f"Не удалось отредактировать сообщение в info: {e}")
                await update.callback_query.message.reply_text(text, parse_mode=parse_mode)
                message_sent = True

        # Если сообщение не было отправлено ни одним из способов
        if not message_sent:
            try:
                # Fallback - отправляем в чат по умолчанию
                if update.effective_chat:
                    await update.effective_chat.send_message(text, parse_mode=parse_mode)
                else:
                    print("Не удалось отправить информацию о пользователе: нет доступного чата")
            except Exception as e:
                print(f"Не удалось отправить информацию о пользователе: {e}")

    async def handle_weather(self, update: Update, context: ContextTypes):
        """Обработка команды /weather"""
        await self.safe_execute(update, context, "weather", self._handle_weather)

    async def _handle_weather(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /weather"""
        # Получаем город из аргументов или используем Москву по умолчанию
        city = ' '.join(context.args) if context.args else 'Moscow'

        # Валидация города
        if not city or len(city.strip()) < 2:
            await update.message.reply_text("❌ Название города должно содержать минимум 2 символа")
            return

        if len(city) > 50:
            await update.message.reply_text("❌ Название города слишком длинное (максимум 50 символов)")
            return

        # Получаем API ключ из конфигурации
        api_key = self.config.api_keys.openweather

        if not api_key:
            await update.message.reply_text("❌ API ключ погоды не настроен")
            return

        try:
            import requests

            # Делаем запрос к OpenWeatherMap API
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"

            response = requests.get(url, timeout=10)

            if response.status_code == 401:
                await update.message.reply_text("❌ Ошибка API: неверный ключ погоды")
                return
            elif response.status_code == 429:
                await update.message.reply_text("❌ Превышен лимит запросов к API погоды. Попробуйте позже.")
                return
            elif response.status_code >= 500:
                await update.message.reply_text("❌ Сервер погоды временно недоступен. Попробуйте позже.")
                return
            elif response.status_code != 200:
                await update.message.reply_text("❌ Ошибка при получении данных о погоде")
                return

            data = response.json()

            if data.get('cod') == 200:
                # Проверяем наличие необходимых данных
                if not all(key in data for key in ['name', 'main', 'weather']):
                    await update.message.reply_text("❌ Неполные данные о погоде от сервера")
                    return

                # Форматируем ответ
                weather_text = (
                    f"🌤️ Погода в <b>{data['name']}</b>\n\n"
                    f"🌡️ Температура: <b>{data['main']['temp']}°C</b>\n"
                    f"🌡️ Ощущается как: <b>{data['main']['feels_like']}°C</b>\n"
                    f"💧 Влажность: <b>{data['main']['humidity']}%</b>\n"
                    f"💬 Описание: <b>{data['weather'][0]['description'].capitalize()}</b>\n"
                )

                await self.send_response(update, weather_text, parse_mode='HTML')
            else:
                # Обработка ошибок от API
                if data.get('cod') == '404':
                    await update.message.reply_text(f"❌ Город '{city}' не найден")
                elif data.get('cod') == '401':
                    await update.message.reply_text("❌ Ошибка авторизации API погоды")
                else:
                    await update.message.reply_text(f"❌ Ошибка API погоды: {data.get('message', 'Неизвестная ошибка')}")

        except requests.exceptions.Timeout:
            await update.message.reply_text("❌ Превышено время ожидания ответа от сервера погоды. Попробуйте позже.")
        except requests.exceptions.ConnectionError:
            await update.message.reply_text("❌ Ошибка подключения к серверу погоды. Проверьте интернет-соединение.")
        except requests.exceptions.RequestException as e:
            await update.message.reply_text(f"❌ Ошибка сети при получении погоды: {str(e)[:100]}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка обработки данных погоды: {str(e)[:100]}")

    async def handle_news(self, update: Update, context: ContextTypes):
        """Обработка команды /news"""
        await self.safe_execute(update, context, "news", self._handle_news)

    async def _handle_news(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /news"""
        # Получаем API ключ из конфигурации
        api_key = self.config.api_keys.news

        if not api_key:
            await update.message.reply_text("❌ API ключ новостей не настроен")
            return

        try:
            import requests

            # Делаем запрос к NewsAPI
            url = f"https://newsapi.org/v2/top-headlines?country=ru&apiKey={api_key}"

            response = requests.get(url, timeout=10)

            if response.status_code == 401:
                await update.message.reply_text("❌ Ошибка API: неверный ключ новостей")
                return
            elif response.status_code == 429:
                await update.message.reply_text("❌ Превышен лимит запросов к API новостей. Попробуйте позже.")
                return
            elif response.status_code >= 500:
                await update.message.reply_text("❌ Сервер новостей временно недоступен. Попробуйте позже.")
                return
            elif response.status_code != 200:
                await update.message.reply_text("❌ Ошибка при получении новостей")
                return

            data = response.json()

            if data.get('status') == 'ok' and data.get('articles'):
                # Проверяем наличие корректных статей
                articles = data['articles'][:5]  # Берем только первые 5
                valid_articles = []

                for article in articles:
                    if article.get('title') and article.get('url'):
                        valid_articles.append(article)

                if not valid_articles:
                    await update.message.reply_text("❌ Новости получены, но не содержат корректных данных")
                    return

                # Форматируем ответ
                news_text = "📰 <b>Последние новости России:</b>\n\n"

                for i, article in enumerate(valid_articles, 1):
                    # Ограничиваем длину заголовка для безопасности
                    title = article['title'][:200] if len(article['title']) > 200 else article['title']
                    url = article['url'][:500] if len(article['url']) > 500 else article['url']  # Ограничиваем URL

                    news_text += f"{i}. <b>{title}</b>\n"
                    news_text += f"🔗 {url}\n\n"

                # Ограничиваем общую длину сообщения
                if len(news_text) > 4000:
                    news_text = news_text[:3997] + "..."

                await self.send_response(update, news_text, parse_mode='HTML')
            else:
                # Обработка ошибок от API
                if data.get('status') == 'error':
                    error_code = data.get('code', 'unknown')
                    error_message = data.get('message', 'Неизвестная ошибка')

                    if error_code == 'apiKeyInvalid':
                        await update.message.reply_text("❌ Ошибка API: неверный ключ новостей")
                    elif error_code == 'rateLimited':
                        await update.message.reply_text("❌ Превышен лимит запросов к API новостей")
                    elif error_code == 'sourcesUnavailable':
                        await update.message.reply_text("❌ Источники новостей недоступны")
                    else:
                        await update.message.reply_text(f"❌ Ошибка API новостей: {error_message}")
                else:
                    await update.message.reply_text("❌ Не удалось получить новости")

        except requests.exceptions.Timeout:
            await update.message.reply_text("❌ Превышено время ожидания ответа от сервера новостей. Попробуйте позже.")
        except requests.exceptions.ConnectionError:
            await update.message.reply_text("❌ Ошибка подключения к серверу новостей. Проверьте интернет-соединение.")
        except requests.exceptions.RequestException as e:
            await update.message.reply_text(f"❌ Ошибка сети при получении новостей: {str(e)[:100]}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка обработки данных новостей: {str(e)[:100]}")

    async def handle_translate(self, update: Update, context: ContextTypes):
        """Обработка команды /translate"""
        await self.safe_execute(update, context, "translate", self._handle_translate)

    async def _handle_translate(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /translate"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Использование: /translate [текст] [язык]\n\n"
                "Примеры:\n"
                "/translate Hello world en\n"
                "/translate Привет мир es\n"
                "/translate Bonjour le monde fr\n\n"
                "Поддерживаемые языки: en, es, fr, de, it, pt, ru, ja, ko, zh"
            )
            return

        text = ' '.join(context.args[:-1])
        target_lang = context.args[-1].lower()

        # Валидация входных данных
        if not text or not text.strip():
            await update.message.reply_text("❌ Текст для перевода не может быть пустым")
            return

        if not target_lang or len(target_lang) != 2:
            await update.message.reply_text("❌ Укажите правильный код языка (например: en, ru, es)")
            return

        # Ограничиваем длину текста для безопасности и производительности
        if len(text) > 1000:
            await update.message.reply_text("❌ Текст слишком длинный для перевода (максимум 1000 символов)")
            return

        # Поддерживаемые языки
        supported_languages = {
            'en': 'английский', 'es': 'испанский', 'fr': 'французский',
            'de': 'немецкий', 'it': 'итальянский', 'pt': 'португальский',
            'ru': 'русский', 'ja': 'японский', 'ko': 'корейский', 'zh': 'китайский'
        }

        if target_lang not in supported_languages:
            await update.message.reply_text(
                f"❌ Неподдерживаемый язык: {target_lang}\n"
                f"Поддерживаемые языки: {', '.join(supported_languages.keys())}"
            )
            return

        try:
            # Простая демонстрация перевода (в реальном приложении нужен API)
            # Здесь можно интегрировать Google Translate API, Yandex Translate, или другой сервис

            # Для демонстрации покажем, как выглядел бы перевод
            # В продакшене замените на реальный API вызов

            # Имитация перевода для демонстрации
            if target_lang == 'en':
                if 'привет' in text.lower():
                    translated = "Hello"
                elif 'мир' in text.lower():
                    translated = "World"
                elif 'спасибо' in text.lower():
                    translated = "Thank you"
                else:
                    translated = f"[EN] {text}"  # Заглушка для неизвестных слов
            elif target_lang == 'es':
                if 'привет' in text.lower():
                    translated = "Hola"
                elif 'мир' in text.lower():
                    translated = "Mundo"
                elif 'спасибо' in text.lower():
                    translated = "Gracias"
                else:
                    translated = f"[ES] {text}"
            elif target_lang == 'fr':
                if 'привет' in text.lower():
                    translated = "Bonjour"
                elif 'мир' in text.lower():
                    translated = "Monde"
                elif 'спасибо' in text.lower():
                    translated = "Merci"
                else:
                    translated = f"[FR] {text}"
            else:
                translated = f"[{target_lang.upper()}] {text}"

            # Форматируем ответ
            response_text = (
                "🔄 <b>Перевод текста</b>\n\n"
                f"📝 <b>Оригинал:</b> {text}\n"
                f"🌐 <b>Язык:</b> {supported_languages[target_lang]}\n"
                f"📋 <b>Перевод:</b> {translated}\n\n"
                "💡 <i>Примечание: Для полноценного перевода необходимо интегрировать "
                "сервис перевода (Google Translate API, Yandex Translate или другой).</i>"
            )

            await self.send_response(update, response_text, parse_mode='HTML')

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при переводе текста: {str(e)[:100]}")

    async def handle_donate(self, update: Update, context: ContextTypes):
        """Обработка команды /donate"""
        await self.safe_execute(update, context, "donate", self._handle_donate)

    async def _handle_donate(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /donate"""
        # Создаем клавиатуру с суммами донатов
        keyboard = [
            [InlineKeyboardButton("💰 100 ₽", callback_data='donate_100')],
            [InlineKeyboardButton("💰 500 ₽", callback_data='donate_500')],
            [InlineKeyboardButton("💰 1000 ₽", callback_data='donate_1000')],
            [InlineKeyboardButton("💰 2500 ₽", callback_data='donate_2500')],
            [InlineKeyboardButton("💰 5000 ₽", callback_data='donate_5000')],
            [InlineKeyboardButton("💰 Другая сумма", callback_data='donate_custom')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Получаем информацию о донатах пользователя
        user = update.effective_user
        user_info = await self.user_service.get_or_create_user(user.id, user.username, user.first_name, user.last_name)

        donate_text = (
            "💰 <b>Поддержка проекта</b>\n\n"
            "Спасибо за интерес к нашему боту! Ваша поддержка помогает нам развивать проект и добавлять новые функции.\n\n"
            "🎁 <b>Преимущества донатеров:</b>\n"
            "• Увеличенные награды за игры\n"
            "• Доступ к премиум-играм\n"
            "• Приоритетная поддержка\n"
            "• Специальные значки в профиле\n\n"
            "💳 <b>Выберите сумму поддержки:</b>"
        )

        if update.message:
            await update.message.reply_text(donate_text, parse_mode='HTML', reply_markup=reply_markup)
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.edit_message_text(donate_text, parse_mode='HTML', reply_markup=reply_markup)

    async def handle_text_message(self, update: Update, context: ContextTypes):
        """Обработка текстовых сообщений"""
        await self.safe_execute(update, context, "text_message", self._handle_text_message)

    async def _handle_text_message(self, update: Update, context: ContextTypes):
        """Внутренняя обработка текстового сообщения"""
        user = update.effective_user
        message_text = update.message.text.lower()

        # Проверяем на "+" для реакции рукопожатием - ВРЕМЕННО ЗАКОММЕНТИРОВАНО ДО ПРОВЕРКИ КОНФЛИКТА С ТРИГГЕРАМИ
        # if "+" in message_text:
        #     try:
        #         # Используем новый метод set_message_reaction (доступен с версии 21+)
        #         await context.bot.set_message_reaction(
        #             chat_id=update.message.chat_id,
        #             message_id=update.message.message_id,
        #             reaction="🤝"
        #         )
        #         print(f"[DEBUG] Reaction set successfully for message {update.message.message_id}")
        #         self.logger.debug(f"Reaction set for message with '+' by user {user.id}")
        #
        #     except Exception as e:
        #         # Fallback на старый метод для совместимости
        #         print(f"[WARNING] Failed to set reaction, using fallback: {e}")
        #         self.logger.warning(f"Failed to set reaction for message with '+' by user {user.id}, using fallback: {e}")
        #
        #         try:
        #             # Используем reply с emoji реакции как fallback
        #             reaction_message = await update.message.reply_text("🤝", reply_to_message_id=update.message.message_id)
        #             print(f"[DEBUG] Reaction reply sent successfully for message {update.message.message_id}")
        #             self.logger.debug(f"Reaction reply fallback sent for message with '+' by user {user.id}")
        #
        #             # Удаляем сообщение с реакцией через 5 секунд
        #             import asyncio
        #             async def delete_reaction():
        #                 try:
        #                     await asyncio.sleep(5)
        #                     await reaction_message.delete()
        #                     print(f"[DEBUG] Reaction reply deleted for message {update.message.message_id}")
        #                 except Exception as delete_e:
        #                     print(f"[WARNING] Failed to delete reaction reply: {delete_e}")
        #
        #             # Запускаем задачу удаления
        #             asyncio.create_task(delete_reaction())
        #
        #         except Exception as fallback_e:
        #             print(f"[ERROR] Both reaction methods failed: primary={e}, fallback={fallback_e}")
        #             self.logger.error(f"Both reaction methods failed for message with '+' by user {user.id}: primary={e}, fallback={fallback_e}")

        # Проверяем на нецензурную лексику
        if self._check_profanity(message_text):
            await self._handle_profanity_violation(update, user)
            return

        # Проверяем слова "реквизиты"
        if "реквизиты" in message_text or "реквизит" in message_text:
            await self.send_response(update, BANK_DETAILS_TEXT, reply_to_message_id=update.message.message_id)
            return

        # Обновляем активность пользователя
        await self.user_service.update_user_activity(user.id, update.effective_chat.id)

    async def handle_donation_callback(self, update: Update, context: ContextTypes):
        """Обработка callback'ов донатов"""
        query = update.callback_query
        await query.answer()

        amount_str = query.data.split('_')[1]

        try:
            amount = float(amount_str)
            user = query.from_user

            points = int(amount // 100)
            keyboard = [[InlineKeyboardButton("✅ Подтвердить перевод", callback_data=f'donate_confirm_{amount}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"💰 <b>Спасибо за выбор поддержки!</b>\n\n"
                f"Сумма: {amount} RUB\n"
                f"Получите очков: {points}\n\n"
                f"💳 <b>Банковские реквизиты:</b>\n\n"
                f"{BANK_DETAILS_TEXT}\n\n"
                f"После оплаты нажмите кнопку ниже для подтверждения:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )

        except ValueError:
            await query.edit_message_text("❌ Неверная сумма!")

    async def handle_donation_custom(self, update: Update, context: ContextTypes):
        """Обработка выбора пользовательской суммы"""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "💰 Введите сумму доната в рублях:\n\n"
            "Пример: 750",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data='menu_main')]])
        )

        # Устанавливаем флаг ожидания суммы
        context.user_data['waiting_for_donation_amount'] = True

    async def handle_donation_amount_input(self, update: Update, context: ContextTypes):
        """Обработка ввода суммы доната"""
        try:
            amount = float(update.message.text.strip())
            if amount <= 0:
                raise ValueError()

            user = update.effective_user
            points = int(amount // 100)

            # Сохраняем донат в базу данных
            success = await self.user_service.add_donation(user.id, amount)

            if success:
                await update.message.reply_text(
                    f"💰 <b>Спасибо за поддержку!</b>\n\n"
                    f"Сумма: {amount} RUB\n"
                    f"Получено очков: {points}\n\n"
                    f"Ваша поддержка помогает развивать бота! 🎉",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text("❌ Ошибка: не удалось сохранить донат в базу данных. Попробуйте позже.")

        except ValueError:
            await update.message.reply_text("❌ Неверная сумма! Введите положительное число.")
        except ValidationError as e:
            error_message = str(e)
            if "ID пользователя" in error_message:
                await update.message.reply_text("❌ Ошибка: проблема с идентификацией пользователя")
            elif "Сумма доната" in error_message:
                await update.message.reply_text("❌ Ошибка: сумма доната должна быть положительной")
            else:
                await update.message.reply_text(f"❌ Ошибка валидации: {error_message}")
        except Exception as e:
            # Логируем ошибку для анализа
            error_details = {
                'user_id': user.id if 'user' in locals() else 'unknown',
                'amount': amount if 'amount' in locals() else 'unknown',
                'error_type': 'custom_donation_processing_error',
                'error_message': str(e),
                'error_context': f"handle_donation_amount_input: {type(e).__name__}",
            }
            await self._log_error_to_database(error_details)
            await update.message.reply_text("❌ Ошибка сервера при обработке доната. Попробуйте позже или обратитесь к администратору.")

        context.user_data.pop('waiting_for_donation_amount', None)

    async def handle_donate_confirm_callback(self, update: Update, context: ContextTypes):
        """Обработка callback подтверждения доната"""
        query = update.callback_query
        await query.answer()

        # Парсим сумму из callback_data
        parts = query.data.split('_')
        if len(parts) < 3:
            await query.edit_message_text("❌ Ошибка: некорректные данные доната")
            return

        try:
            amount = float(parts[2])
            user = query.from_user

            # Сохраняем донат в базу данных
            success = await self.user_service.add_donation(user.id, amount)

            if success:
                points = int(amount // 100)
                await query.edit_message_text(
                    f"💰 <b>Спасибо за поддержку!</b>\n\n"
                    f"Сумма: {amount} RUB\n"
                    f"Получено очков: {points}\n\n"
                    f"Ваша поддержка помогает развивать бота! 🎉",
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text("❌ Ошибка: не удалось сохранить донат в базу данных. Попробуйте позже.")

        except ValueError:
            await query.edit_message_text("❌ Ошибка: неверная сумма доната")
        except ValidationError as e:
            error_message = str(e)
            if "ID пользователя" in error_message:
                await query.edit_message_text("❌ Ошибка: проблема с идентификацией пользователя")
            elif "Сумма доната" in error_message:
                await query.edit_message_text("❌ Ошибка: сумма доната должна быть положительной")
            else:
                await query.edit_message_text(f"❌ Ошибка валидации: {error_message}")
        except Exception as e:
            # Логируем ошибку в базу данных для анализа
            error_details = {
                'user_id': user.id if 'user' in locals() else 'unknown',
                'amount': amount if 'amount' in locals() else 'unknown',
                'error_type': 'donation_processing_error',
                'error_message': str(e),
                'error_context': f"handle_donate_confirm_callback: {type(e).__name__}",
                'callback_data': query.data
            }
            await self._log_error_to_database(error_details)
            self.logger.error(f"Неожиданная ошибка при обработке доната: {e}", exc_info=True)
            await query.edit_message_text("❌ Ошибка сервера при обработке доната. Попробуйте позже или обратитесь к администратору.")

    def _check_profanity(self, text: str) -> bool:
        """Проверка текста на наличие нецензурной лексики"""
        if not text:
            return False

        text_lower = text.lower()

        # Проверяем каждое слово из списка
        for word in PROFANITY_WORDS:
            if word in text_lower:
                return True

        return False

    async def _handle_profanity_violation(self, update: Update, user):
        """Обработка нарушения с нецензурной лексикой"""
        try:
            # Удаляем сообщение с матом
            await update.message.delete()
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")

        # Отправляем предупреждение в чат
        username = user.username if user.username else user.first_name
        await self.send_response(update, f"⚠️ {username}, в группе запрещена нецензурная лексика!\n"
            f"Сообщение удалено, выдано предупреждение.", parse_mode='HTML')

        # Добавляем предупреждение пользователю
        try:
            print(f"[DEBUG] Adding warning to user {user.id} for profanity")
            await self.user_service.add_warning(user.id, "Нецензурная лексика", 0)  # 0 - системное предупреждение
            print(f"[DEBUG] Warning added successfully to user {user.id}")
        except Exception as e:
            print(f"[ERROR] Не удалось добавить предупреждение пользователю {user.id}: {e}")

    async def handle_voice_message(self, update: Update, context: ContextTypes):
        """Обработка голосовых сообщений"""
        await self.safe_execute(update, context, "voice_message", self._handle_voice_message)

    async def _handle_voice_message(self, update: Update, context: ContextTypes):
        """Внутренняя обработка голосового сообщения"""
        user = update.effective_user
        voice = update.message.voice

        # Обновляем активность пользователя
        await self.user_service.update_user_activity(user.id, update.effective_chat.id)

        # Получаем длительность голосового сообщения
        duration = voice.duration

        # Попытка транскрипции голосового сообщения
        transcription = await self._transcribe_voice_message(voice, update)

        # Отправляем ответ пользователю
        if transcription and transcription != "[не удалось распознать речь]":
            await update.message.reply_text(
                f"🎤 Голосовое сообщение от {user.first_name} ({duration} сек)\n\n"
                f"📝 Распознано: {transcription}\n\n"
                f"💡 +1 очко за активность!",
                reply_to_message_id=update.message.message_id
            )
        else:
            await update.message.reply_text(
                f"🎤 Голосовое сообщение от {user.first_name} ({duration} сек)\n\n"
                f"❌ Не удалось распознать речь\n"
                f"💡 +1 очко за активность!",
                reply_to_message_id=update.message.message_id
            )

    async def _transcribe_voice_message(self, voice, update: Update) -> str:
        """Транскрипция голосового сообщения"""
        try:
            # Проверяем доступность библиотек распознавания речи
            try:
                import speech_recognition as sr
                SPEECH_RECOGNITION_AVAILABLE = True
            except ImportError:
                return "[Библиотека speech_recognition не установлена]"

            # Создаем временный файл для загрузки аудио
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
                temp_ogg_path = temp_ogg.name

            try:
                # Скачиваем голосовое сообщение
                voice_file = await voice.get_file()
                await voice_file.download_to_drive(temp_ogg_path)

                # Конвертируем OGG в WAV для speech_recognition
                temp_wav_path = temp_ogg_path.replace('.ogg', '.wav')

                try:
                    # Пробуем использовать pydub для конвертации
                    try:
                        from pydub import AudioSegment
                        audio = AudioSegment.from_ogg(temp_ogg_path)
                        audio.export(temp_wav_path, format='wav')
                    except ImportError:
                        # Используем ffmpeg для конвертации (если доступен)
                        import subprocess
                        try:
                            subprocess.run([
                                'ffmpeg', '-i', temp_ogg_path, '-acodec', 'pcm_s16le',
                                '-ar', '16000', '-ac', '1', temp_wav_path
                            ], check=True, capture_output=True)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            return "[невозможно конвертировать аудио - установите pydub или ffmpeg]"

                    # Распознавание речи
                    recognizer = sr.Recognizer()

                    with sr.AudioFile(temp_wav_path) as source:
                        audio_data = recognizer.record(source)

                        # Пробуем разные API для распознавания
                        try:
                            # Сначала пробуем Google Speech Recognition (бесплатно)
                            text = recognizer.recognize_google(audio_data, language='ru-RU')
                            return text
                        except sr.UnknownValueError:
                            return "[не удалось распознать речь]"
                        except sr.RequestError:
                            # Если Google API недоступен, пробуем Sphinx (локальный, но менее точный)
                            try:
                                text = recognizer.recognize_sphinx(audio_data, language='ru-RU')
                                return text
                            except sr.UnknownValueError:
                                return "[не удалось распознать речь (локально)]"
                            except sr.RequestError:
                                return "[сервисы распознавания речи недоступны]"

                finally:
                    # Очищаем временные файлы
                    try:
                        if os.path.exists(temp_ogg_path):
                            os.unlink(temp_ogg_path)
                        if os.path.exists(temp_wav_path):
                            os.unlink(temp_wav_path)
                    except:
                        pass

            except Exception as e:
                print(f"Ошибка при транскрипции: {e}")
                return "[ошибка при обработке голосового сообщения]"

        except Exception as e:
            print(f"Ошибка при инициализации распознавания речи: {e}")
            return "[ошибка инициализации распознавания речи]"

    async def handle_audio_message(self, update: Update, context: ContextTypes):
        """Обработка аудио сообщений для модерации"""
        await self._handle_media_for_moderation(update, context, "audio")

    async def handle_video_message(self, update: Update, context: ContextTypes):
        """Обработка видео сообщений для модерации"""
        await self._handle_media_for_moderation(update, context, "video")

    async def _handle_media_for_moderation(self, update: Update, context: ContextTypes, media_type: str):
        """Обработка медиафайлов для модерации"""
        user = update.effective_user
        message = update.message

        # Обновляем активность пользователя
        await self.user_service.update_user_activity(user.id, update.effective_chat.id)

        # Получаем информацию о медиа
        if media_type == "audio":
            media = message.audio
            duration = getattr(media, 'duration', 0)
            file_size = getattr(media, 'file_size', 0)
            title = getattr(media, 'title', 'Без названия')
            performer = getattr(media, 'performer', 'Неизвестный исполнитель')
        elif media_type == "video":
            media = message.video
            duration = getattr(media, 'duration', 0)
            file_size = getattr(media, 'file_size', 0)
            width = getattr(media, 'width', 0)
            height = getattr(media, 'height', 0)
        else:
            return

        # Попытка транскрипции аудио (если это аудио)
        transcription = ""
        if media_type == "audio":
            transcription = await self._transcribe_audio_for_moderation(media, update)

        # Удаляем оригинальное сообщение
        try:
            await message.delete()
        except Exception as e:
            print(f"Не удалось удалить сообщение с медиа: {e}")

        # Сохраняем информацию о медиа в контексте для модерации
        context.user_data['media_for_moderation'] = {
            'message_id': message.message_id,
            'chat_id': message.chat.id,
            'user_id': user.id,
            'media_type': media_type,
            'file_id': media.file_id,
            'duration': duration,
            'file_size': file_size,
            'transcription': transcription,
            'caption': message.caption or "",
            'timestamp': datetime.now()
        }

        # Создаем клавиатуру для модерации
        keyboard = [
            [InlineKeyboardButton("✅ Одобрить и опубликовать сейчас", callback_data=f'moderate_approve_now_{user.id}')],
            [InlineKeyboardButton("⏰ Одобрить с отсрочкой (8 часов)", callback_data=f'moderate_approve_delay_{user.id}')],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f'moderate_reject_{user.id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем уведомление администраторам для модерации
        await self._notify_admins_for_moderation(context, user, media_type, transcription, message.caption or "")

    async def _transcribe_audio_for_moderation(self, audio, update: Update) -> str:
        """Транскрипция аудио для модерации"""
        try:
            # Проверяем доступность библиотек распознавания речи
            try:
                import speech_recognition as sr
            except ImportError:
                return "[Транскрибация недоступна - не установлена библиотека]"

            # Создаем временный файл для загрузки аудио
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
                temp_ogg_path = temp_ogg.name

            try:
                # Скачиваем аудио
                audio_file = await audio.get_file()
                await audio_file.download_to_drive(temp_ogg_path)

                # Конвертируем OGG в WAV для speech_recognition
                temp_wav_path = temp_ogg_path.replace('.ogg', '.wav')

                try:
                    # Пробуем использовать pydub для конвертации
                    try:
                        from pydub import AudioSegment
                        audio_seg = AudioSegment.from_ogg(temp_ogg_path)
                        audio_seg.export(temp_wav_path, format='wav')
                    except ImportError:
                        # Используем ffmpeg для конвертации (если доступен)
                        import subprocess
                        try:
                            subprocess.run([
                                'ffmpeg', '-i', temp_ogg_path, '-acodec', 'pcm_s16le',
                                '-ar', '16000', '-ac', '1', temp_wav_path
                            ], check=True, capture_output=True)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            return "[Невозможно конвертировать аудио для транскрибации]"

                    # Распознавание речи
                    recognizer = sr.Recognizer()

                    with sr.AudioFile(temp_wav_path) as source:
                        audio_data = recognizer.record(source)

                        # Пробуем разные API для распознавания
                        try:
                            # Сначала пробуем Google Speech Recognition (бесплатно)
                            text = recognizer.recognize_google(audio_data, language='ru-RU')
                            return text
                        except sr.UnknownValueError:
                            return "[Не удалось распознать речь]"
                        except sr.RequestError:
                            # Если Google API недоступен, пробуем Sphinx (локальный, но менее точный)
                            try:
                                text = recognizer.recognize_sphinx(audio_data, language='ru-RU')
                                return text
                            except sr.UnknownValueError:
                                return "[Не удалось распознать речь (локально)]"
                            except sr.RequestError:
                                return "[Сервисы распознавания речи недоступны]"

                finally:
                    # Очищаем временные файлы
                    try:
                        if os.path.exists(temp_ogg_path):
                            os.unlink(temp_ogg_path)
                        if os.path.exists(temp_wav_path):
                            os.unlink(temp_wav_path)
                    except:
                        pass

            except Exception as e:
                print(f"Ошибка при транскрипции для модерации: {e}")
                return "[Ошибка при обработке аудио]"

        except Exception as e:
            print(f"Ошибка при инициализации транскрипции для модерации: {e}")
            return "[Ошибка при обработке аудио]"

    async def _notify_admins_for_moderation(self, context: ContextTypes, user, media_type: str, transcription: str, caption: str):
        """Отправка уведомления администраторам для модерации медиа"""
        try:
            # Получаем список администраторов из конфигурации
            admin_ids = self.config.bot_config.admin_ids

            for admin_id in admin_ids:
                try:
                    notification_text = (
                        "🔔 <b>Требуется модерация медиафайла</b>\n\n"
                        f"👤 Пользователь: {user.first_name} (@{user.username if user.username else 'нет'})\n"
                        f"🆔 ID: {user.id}\n"
                        f"📁 Тип файла: {media_type}\n"
                        f"📝 Описание: {caption[:100]}{'...' if len(caption) > 100 else ''}\n"
                        f"🎵 Транскрипция: {transcription[:200]}{'...' if len(transcription) > 200 else ''}\n\n"
                        "Медиафайл отправлен в группу модераторов для проверки."
                    )

                    await self.send_response(update, notification_text, parse_mode='HTML', chat_id=admin_id)
                except Exception as e:
                    print(f"Не удалось отправить уведомление администратору {admin_id}: {e}")

        except Exception as e:
            print(f"Ошибка при отправке уведомлений модерации: {e}")

    async def handle_main_menu(self, update: Update, context: ContextTypes):
        """Обработка нажатия на главное меню"""
        query = update.callback_query
        await query.answer()

        await self._handle_start(update, context)

    async def handle_help_menu(self, update: Update, context: ContextTypes):
        """Обработка нажатия на меню помощи"""
        query = update.callback_query
        await query.answer()

        await self._handle_help(update, context)

    async def handle_rank_menu(self, update: Update, context: ContextTypes):
        """Обработка нажатия на меню ранга"""
        query = update.callback_query
        await query.answer()

        await self._handle_rank(update, context)

    async def handle_donate_menu(self, update: Update, context: ContextTypes):
        """Обработка нажатия на меню донатов"""
        query = update.callback_query
        await query.answer()

        await self._handle_donate(update, context)
        return

    async def handle_leaderboard_menu(self, update: Update, context: ContextTypes):
        """Обработка нажатия на меню таблицы лидеров"""
        query = update.callback_query
        await query.answer()

        await self._handle_leaderboard(update, context)

    async def _log_error_to_database(self, error_details: Dict) -> None:
        """Логирование ошибки в базу данных для анализа"""
        try:
            # Получаем ID администратора (первый из списка или текущий пользователь)
            admin_id = error_details.get('user_id', 'unknown')
            if admin_id == 'unknown' and hasattr(self.config, 'bot_config') and hasattr(self.config.bot_config, 'admin_ids'):
                admin_id = self.config.bot_config.admin_ids[0] if self.config.bot_config.admin_ids else 0

            error_type = error_details.get('error_type', 'unknown_error')
            title = f"Ошибка при обработке доната: {error_details.get('error_context', 'Неизвестный контекст')}"
            description = (
                f"Пользователь: {error_details.get('user_id', 'Неизвестен')}\n"
                f"Сумма: {error_details.get('amount', 'Неизвестна')}\n"
                f"Тип ошибки: {error_details.get('error_type', 'Неизвестен')}\n"
                f"Сообщение: {error_details.get('error_message', 'Неизвестно')}\n"
                f"Контекст: {error_details.get('error_context', 'Неизвестен')}\n"
                f"Callback: {error_details.get('callback_data', 'Неизвестен')}"
            )

            # Определяем приоритет на основе типа ошибки
            if 'ValidationError' in error_details.get('error_context', ''):
                priority = 'medium'
            elif 'DatabaseError' in error_details.get('error_context', ''):
                priority = 'high'
            else:
                priority = 'high'  # Для неожиданных ошибок

            # Добавляем ошибку в базу данных
            if hasattr(self, 'error_repo') and self.error_repo:
                error_id = self.error_repo.add_error(admin_id, error_type, title, description, priority)
                if error_id:
                    self.logger.info(f"Ошибка #{error_id} успешно сохранена в базу данных")
                else:
                    self.logger.error("Не удалось сохранить ошибку в базу данных")
            else:
                self.logger.warning("ErrorRepository недоступен для логирования ошибки")

        except Exception as log_error:
            self.logger.error(f"Ошибка при логировании ошибки в базу данных: {log_error}", exc_info=True)
    def _format_user_info(self, profile, user_id: int) -> str:
        """Форматирование информации о пользователе"""
        return (
            "👤 <b>Информация о пользователе:</b>\n\n"
            f"🆔 ID: {user_id}\n"
            f"👤 Имя: {profile.first_name}\n"
            f"📱 Username: @{profile.username if profile.username else 'Не указан'}\n"
            f"🏆 Репутация: {profile.reputation}\n"
            f"⭐ Ранг: {profile.rank}\n"
            f"💬 Сообщений: {profile.message_count}\n"
            f"⚠️ Предупреждений: {profile.warnings}\n"
            f"📅 Присоединился: {profile.joined_date.strftime('%Y-%m-%d') if profile.joined_date else 'Неизвестно'}\n"
        )

    def _compare_keyboards(self, markup1: InlineKeyboardMarkup, markup2: InlineKeyboardMarkup) -> bool:
        """Сравнивает две клавиатуры на идентичность"""
        if not markup1 and not markup2:
            return False  # Обе пустые - не изменилось
        if not markup1 or not markup2:
            return True   # Одна пустая, другая нет - изменилось

        # Сравниваем количество строк
        if len(markup1.inline_keyboard) != len(markup2.inline_keyboard):
            return True

        # Сравниваем каждую кнопку
        for row1, row2 in zip(markup1.inline_keyboard, markup2.inline_keyboard):
            if len(row1) != len(row2):
                return True
            for btn1, btn2 in zip(row1, row2):
                if (btn1.text != btn2.text or
                    btn1.callback_data != btn2.callback_data or
                    btn1.url != btn2.url):
                    return True

        return False  # Клавиатуры идентичны

    def _get_medal(self, position: int) -> str:
        """Получение медали для позиции в рейтинге"""
        medals = {
            1: "🥇", 2: "🥈", 3: "🥉",
            4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
            7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
        }
        return medals.get(position, f"{position}.")
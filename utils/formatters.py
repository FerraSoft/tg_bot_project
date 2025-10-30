"""
Форматтеры для сообщений и клавиатур телеграм-бота.
Обеспечивают единообразное форматирование вывода.
"""

from typing import Dict, List, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class MessageFormatter:
    """Форматтер текстовых сообщений"""

    @staticmethod
    def format_user_info(user_data: Dict[str, Any]) -> str:
        """Форматирование информации о пользователе"""
        if not user_data:
            return "👤 <b>Информация о пользователе:</b>\n❌ Данные не найдены"

        name = MessageFormatter.escape_html(str(user_data.get('name', 'Неизвестно')))
        username = MessageFormatter.escape_html(str(user_data.get('username', 'Не указан')))

        return (
            "👤 <b>Информация о пользователе:</b>\n"
            f"🆔 ID: {user_data.get('id', 'Неизвестен')}\n"
            f"👤 Имя: {name}\n"
            f"📱 Username: @{username}\n"
            f"🏆 Репутация: {user_data.get('reputation', 0)}\n"
            f"⭐ Ранг: {MessageFormatter.escape_html(str(user_data.get('rank', 'Новичок')))}\n"
            f"💬 Сообщений: {user_data.get('message_count', 0)}\n"
            f"📅 Дата регистрации: {user_data.get('joined_date', 'Неизвестна')}"
        )

    @staticmethod
    def format_rank_info(score: int, warnings: int, role: str) -> str:
        """Форматирование информации о ранге"""
        return (
            "🏆 <b>Ваш ранг:</b>\n"
            f"⭐ Очки: {score}\n"
            f"⚠️ Предупреждений: {warnings}\n"
            f"👑 Роль: {MessageFormatter.escape_html(role)}"
        )

    @staticmethod
    def format_leaderboard(users: List[tuple]) -> str:
        """Форматирование таблицы лидеров"""
        if not users:
            return "📭 Таблица лидеров пуста"

        result = ["🏆 <b>Таблица лидеров:</b>\n"]

        for i, (user_id, username, display_name, points) in enumerate(users[:10], 1):
            medal = MessageFormatter._get_medal(i)
            name = MessageFormatter.escape_html(display_name or username or f"User{user_id}")
            result.append(f"{medal} <b>{name}</b> - {points} очков")

        return "\n".join(result)

    @staticmethod
    def _get_medal(position: int) -> str:
        """Получение медали для позиции в таблице лидеров"""
        if position == 1:
            return "🥇"
        elif position == 2:
            return "🥈"
        elif position == 3:
            return "🥉"
        elif position == 10:
            return "🔟"
        else:
            return f"{position}."

    @staticmethod
    def format_weather_info(weather_data: Dict[str, Any]) -> str:
        """Форматирование информации о погоде"""
        if not weather_data:
            return "🌤️ <b>Погода</b>\n❌ Данные не найдены"

        city = MessageFormatter.escape_html(str(weather_data.get('city', 'Неизвестном городе')))
        return (
            f"🌤️ <b>Погода в {city}</b>\n"
            f"🌡️ Температура: {weather_data.get('temp', 0)}°C\n"
            f"🌡️ Ощущается как: {weather_data.get('feels_like', 0)}°C\n"
            f"💧 Влажность: {weather_data.get('humidity', 0)}%\n"
            f"💬 Описание: {MessageFormatter.escape_html(str(weather_data.get('description', 'Нет данных')))}"
        )

    @staticmethod
    def format_news(articles: List[Dict[str, Any]]) -> str:
        """Форматирование списка новостей"""
        if not articles:
            return "📰 Новости не найдены"

        result = ["📰 <b>Последние новости:</b>\n"]

        for i, article in enumerate(articles[:10], 1):
            title = MessageFormatter.escape_html(article.get('title', 'Без заголовка'))
            url = article.get('url', '')
            result.append(f"{i}. <b>{title}</b>")
            if url:
                result.append(f"🔗 {url}")

        return "\n".join(result)

    @staticmethod
    def format_error_report(error_data: Dict[str, Any]) -> str:
        """Форматирование отчета об ошибке"""
        if not error_data:
            return "🐛 <b>Отчет об ошибке</b>\n❌ Данные не найдены"

        error_id = error_data.get('id', 'Неизвестен')
        return (
            f"🐛 <b>Отчет об ошибке #{error_id}</b>\n"
            f"📋 Тип: {MessageFormatter.escape_html(str(error_data.get('type', 'Неизвестен')))}\n"
            f"📝 Заголовок: {MessageFormatter.escape_html(str(error_data.get('title', 'Без заголовка')))}\n"
            f"⭐ Приоритет: {MessageFormatter.escape_html(str(error_data.get('priority', 'Не указан')))}\n"
            f"👤 Создатель: {MessageFormatter.escape_html(str(error_data.get('admin_name', 'Неизвестен')))}\n"
            f"📅 Дата создания: {error_data.get('created_at', 'Неизвестна')}\n"
            f"📄 Описание:\n{MessageFormatter.escape_html(str(error_data.get('description', 'Без описания')))}"
        )

    @staticmethod
    def format_donation_info(amount: float, points: int) -> str:
        """Форматирование информации о донате"""
        return (
            "💰 <b>Спасибо за поддержку!</b>\n"
            f"💵 Сумма: {amount} RUB\n"
            f"⭐ Получено очков: {points}\n"
            "🎉 Ваша поддержка помогает развивать бота!"
        )

    @staticmethod
    def format_achievement(achievement_name: str, description: str) -> str:
        """Форматирование достижения"""
        return (
            "🏆 <b>Новое достижение!</b>\n"
            f"🎖 {MessageFormatter.escape_html(achievement_name)}\n"
            f"📝 {MessageFormatter.escape_html(description)}"
        )

    @staticmethod
    def format_moderation_info(media_type: str, user_name: str, transcription: str = None) -> str:
        """Форматирование информации для модерации"""
        media_types = {
            'audio': 'АУДИО',
            'video': 'ВИДЕО',
            'photo': 'ИЗОБРАЖЕНИЕ',
            'document': 'ДОКУМЕНТ'
        }

        result = (
            "🔍 <b>Медиафайл на модерации</b>\n"
            f"👤 Пользователь: {MessageFormatter.escape_html(user_name)}\n"
            f"📁 Тип файла: {media_types.get(media_type.lower(), media_type.upper())}"
        )

        if transcription:
            result += f"\n🎵 Транскрипция: {MessageFormatter.escape_html(transcription)}"

        return result

    @staticmethod
    def escape_html(text: str) -> str:
        """Экранирование HTML символов"""
        if not text:
            return ""
        return (text.replace("&", "&")
                .replace("<", "<")
                .replace(">", ">")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))

    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Усечение текста до указанной длины"""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix


class KeyboardFormatter:
    """Форматтер клавиатур"""

    @staticmethod
    def create_main_menu(user_role: str = "user", chat_type: str = "private") -> InlineKeyboardMarkup:
        """Создание главного меню с учетом роли пользователя и типа чата"""
        # Базовые кнопки для всех пользователей
        keyboard = [
            [InlineKeyboardButton("📋 Помощь", callback_data='menu_help')],
            [InlineKeyboardButton("🎮 Мини игры", callback_data='menu_games')],
            [InlineKeyboardButton("💰 Донат", callback_data='menu_donate')],
            [InlineKeyboardButton("🏆 Таблица лидеров", callback_data='menu_leaderboard')]
        ]

        # Дополнительные кнопки для модераторов и администраторов
        if user_role in ["moderator", "admin", "super_admin"]:
            keyboard.insert(0, [InlineKeyboardButton("🛡️ Модерация", callback_data='menu_moderation')])

        # Дополнительные кнопки для администраторов только в личном чате
        if user_role in ["admin", "super_admin"] and chat_type == "private":
            keyboard.insert(1, [InlineKeyboardButton("👑 Администрирование", callback_data='menu_admin')])
            keyboard.insert(2, [InlineKeyboardButton("⚙️ Триггеры", callback_data='menu_triggers')])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_games_menu(chat_type: str = "private") -> InlineKeyboardMarkup:
        """Создание меню игр"""
        if chat_type != "private":
            # В групповых чатах показываем сообщение о том, что игры доступны только в личном чате
            keyboard = [
                [InlineKeyboardButton("💬 Играть в личном чате с ботом", url='https://t.me/bot_username')],
                [InlineKeyboardButton("⬅️ Назад", callback_data='menu_main')]
            ]
        else:
            # В личном чате показываем полное меню игр
            keyboard = [
                [InlineKeyboardButton("🎯 Игра 1", callback_data='game_1')],
                [InlineKeyboardButton("🎲 Игра 2", callback_data='game_2')],
                [InlineKeyboardButton("🎰 Игра 3", callback_data='game_3')],
                [InlineKeyboardButton("🎪 Игра 4", callback_data='game_4')],
                [InlineKeyboardButton("🎨 Игра 5", callback_data='game_5')],
                [InlineKeyboardButton("🎭 Игра 6", callback_data='game_6')],
                [InlineKeyboardButton("🎪 Игра 7", callback_data='game_7')],
                [InlineKeyboardButton("⬅️ Назад", callback_data='menu_main')]
            ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_donation_menu() -> InlineKeyboardMarkup:
        """Создание меню донатов"""
        keyboard = [
            [InlineKeyboardButton("💰 100 ₽", callback_data='donate_100')],
            [InlineKeyboardButton("💰 250 ₽", callback_data='donate_250')],
            [InlineKeyboardButton("💰 500 ₽", callback_data='donate_500')],
            [InlineKeyboardButton("💰 1000 ₽", callback_data='donate_1000')],
            [InlineKeyboardButton("💰 2500 ₽", callback_data='donate_2500')],
            [InlineKeyboardButton("💰 Другая сумма", callback_data='donate_custom')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_main')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_admin_menu(user_role: str = "admin") -> InlineKeyboardMarkup:
        """Создание меню администратора с учетом роли"""
        keyboard = []

        # Базовые кнопки для администраторов
        if user_role in ["admin", "super_admin"]:
            keyboard.extend([
                [InlineKeyboardButton("👥 Управление пользователями", callback_data='admin_users')],
                [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
                [InlineKeyboardButton("🔧 Настройки", callback_data='admin_settings')],
                [InlineKeyboardButton("🐛 Отчеты об ошибках", callback_data='admin_errors')]
            ])

        # Дополнительные кнопки только для супер-администраторов
        if user_role == "super_admin":
            keyboard.extend([
                [InlineKeyboardButton("⚙️ Системные настройки", callback_data='admin_system')],
                [InlineKeyboardButton("📋 Логи системы", callback_data='admin_logs')],
                [InlineKeyboardButton("🔄 Перезапуск бота", callback_data='admin_restart')]
            ])

        # Кнопка "Назад" для всех
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='menu_main')])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_moderation_menu(user_role: str = "moderator") -> InlineKeyboardMarkup:
        """Создание меню модерации с учетом роли"""
        keyboard = [
            [InlineKeyboardButton("⚠️ Предупреждения", callback_data='mod_warnings')],
            [InlineKeyboardButton("🔇 Заглушки", callback_data='mod_mutes')],
            [InlineKeyboardButton("📊 Статистика модерации", callback_data='mod_stats')]
        ]

        # Дополнительные кнопки для администраторов (могут банить)
        if user_role in ["admin", "super_admin"]:
            keyboard.insert(0, [InlineKeyboardButton("🚫 Баны пользователей", callback_data='mod_bans')])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='menu_main')])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_moderation_menu(media_type: str, user_id: int) -> InlineKeyboardMarkup:
        """Создание меню модерации"""
        keyboard = [
            [InlineKeyboardButton("✅ Одобрить", callback_data=f'moderate_approve_{user_id}')],
            [InlineKeyboardButton("⏰ Одобрить с задержкой", callback_data=f'moderate_delay_{user_id}')],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f'moderate_reject_{user_id}')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_confirmation_menu(yes_callback: str, no_callback: str, yes_text: str = "Да", no_text: str = "Нет") -> InlineKeyboardMarkup:
        """Создание меню подтверждения"""
        keyboard = [
            [InlineKeyboardButton(yes_text, callback_data=yes_callback)],
            [InlineKeyboardButton(no_text, callback_data=no_callback)]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_pagination_menu(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
        """Создание меню пагинации"""
        if total_pages == 1:
            # Для одной страницы показываем только информационную кнопку
            keyboard = [[InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data=f'{prefix}_info')]]
        else:
            # Для нескольких страниц показываем навигацию
            navigation_row = []
            if current_page > 1:
                navigation_row.append(InlineKeyboardButton("⬅️", callback_data=f'{prefix}_prev'))
            if current_page < total_pages:
                navigation_row.append(InlineKeyboardButton("➡️", callback_data=f'{prefix}_next'))

            info_row = [[InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data=f'{prefix}_info')]]

            if navigation_row:
                keyboard = [navigation_row] + info_row
            else:
                keyboard = info_row

        return InlineKeyboardMarkup(keyboard)
"""
Сервис управления приветственными сообщениями.
Отвечает за генерацию приветствий в зависимости от роли пользователя.
"""

from typing import Dict, Optional
from core.permissions import UserRole
from core.exceptions import ValidationError


class WelcomeService:
    """
    Сервис для генерации приветственных сообщений на основе роли пользователя.

    Отвечает за:
    - Генерацию приветствий для разных ролей
    - Форматирование сообщений с персональными данными
    - Валидацию входных данных
    """

    def __init__(self):
        """Инициализация сервиса приветствий"""
        self.welcome_messages = self._initialize_welcome_messages()

    def _initialize_welcome_messages(self) -> Dict[str, str]:
        """
        Инициализация словаря приветственных сообщений для разных ролей.
        На основе требований из welcome_messages_proposals.md
        """
        return {
            UserRole.USER.value: """👋 Добро пожаловать в наш бот!

Здесь вы можете:
• 📊 Проверить свой ранг: /rank
• 🏆 Посмотреть таблицу лидеров: /leaderboard
• 🎯 Играть в игры: /play_game
• 🌦️ Узнать погоду: /weather
• 📰 Прочитать новости: /news
• 💸 Поддержать проект: /donate

Для справки используйте /help""",

            UserRole.MODERATOR.value: """🛡️ Добро пожаловать, модератор!

Ваши права:
• ⚠️ Предупреждения: /warn
• 🔇 Заглушка: /mute /unmute
• 📊 Статистика модерации

Все базовые команды также доступны: /rank, /play_game, /weather и др.""",

            UserRole.ADMIN.value: """👑 Добро пожаловать, администратор!

У вас полный доступ к управлению ботом:
• 👥 Модерация: /warn, /mute, /ban, /kick
• 📊 Статистика: /admin_stats, /export_stats
• 📝 Планирование: /schedule_post, /list_posts
• 🛠️ Система: /admin_errors, /report_error

Все пользовательские команды также доступны.
Используйте /help для полного списка.""",

            UserRole.SUPER_ADMIN.value: """🔧 Супер-администратор активирован!

Ваши возможности:
• ⚠️ Модерация пользователей: /warn /mute /ban
• 📈 Просмотр статистики: /admin_stats
• 📅 Управление публикациями: /schedule_post
• 🔍 Работа с ошибками: /admin_errors
• 📤 Экспорт данных: /export_stats

Обычные команды: /rank /leaderboard /play_game и др."""
        }

    def get_welcome_message(self, user_role: UserRole, user_name: Optional[str] = None) -> str:
        """
        Получение приветственного сообщения для указанной роли.

        Args:
            user_role: Роль пользователя
            user_name: Имя пользователя (опционально)

        Returns:
            Отформатированное приветственное сообщение

        Raises:
            ValidationError: Если роль не поддерживается
        """
        if not isinstance(user_role, UserRole):
            raise ValidationError(f"Неверная роль пользователя: {user_role}")

        # Получаем базовое сообщение для роли
        base_message = self.welcome_messages.get(user_role.value)

        if not base_message:
            # Fallback на сообщение для обычного пользователя
            base_message = self.welcome_messages[UserRole.USER.value]

        # Форматируем с именем пользователя, если указано
        if user_name:
            # Добавляем персональное приветствие в начало
            personal_greeting = f"👋 Привет, {user_name}!\n\n"
            return personal_greeting + base_message
        else:
            # Безымянное приветствие
            return "👋 Привет!\n\n" + base_message

    def get_available_commands_for_role(self, user_role: UserRole) -> Dict[str, list]:
        """
        Получение доступных команд для указанной роли.

        Args:
            user_role: Роль пользователя

        Returns:
            Словарь с доступными командами по категориям
        """
        if not isinstance(user_role, UserRole):
            raise ValidationError(f"Неверная роль пользователя: {user_role}")

        # Базовые команды для всех пользователей
        base_commands = {
            'user_commands': [
                '/start - Приветствие и начало работы',
                '/help - Справка по командам',
                '/rank - Просмотр личного ранга и прогресса',
                '/leaderboard - Таблица лидеров по очкам',
                '/info - Информация о боте',
                '/weather - Погода',
                '/news - Новости',
                '/translate - Перевод текста',
                '/donate - Поддержать проект'
            ],
            'games': [
                '/play_game - Выбор игры',
                '/rock_paper_scissors - Камень-ножницы-бумага',
                '/tic_tac_toe - Крестики-нолики',
                '/quiz - Викторина',
                '/battleship - Морской бой',
                '/game_2048 - Игра 2048',
                '/tetris - Тетрис',
                '/snake - Змейка'
            ]
        }

        # Добавляем команды в зависимости от роли
        if user_role in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            base_commands['moderation'] = [
                '/warn - Выдать предупреждение',
                '/mute - Заглушить пользователя',
                '/unmute - Снять заглушку'
            ]

        if user_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            base_commands['admin'] = [
                '/ban - Заблокировать пользователя',
                '/unban - Разблокировать пользователя',
                '/kick - Выгнать из чата',
                '/admin_stats - Статистика админа',
                '/schedule_post - Запланировать публикацию',
                '/list_posts - Список запланированных постов',
                '/delete_post - Удалить пост',
                '/publish_now - Опубликовать немедленно',
                '/report_error - Сообщить об ошибке',
                '/admin_errors - Управление ошибками',
                '/export_stats - Экспорт статистики'
            ]

        if user_role == UserRole.SUPER_ADMIN:
            base_commands['super_admin'] = [
                '/admin_system - Системные настройки',
                '/admin_logs - Системные логи',
                '/admin_restart - Управление перезапуском'
            ]

        return base_commands

    def validate_user_name(self, name: str) -> bool:
        """
        Валидация имени пользователя.

        Args:
            name: Имя для проверки

        Returns:
            True если имя корректное
        """
        if not name or not isinstance(name, str):
            return False

        # Проверяем длину
        if len(name.strip()) < 1 or len(name) > 100:
            return False

        # Проверяем на запрещенные символы (простая проверка)
        forbidden_chars = ['<', '>', '&', '\n', '\r']
        if any(char in name for char in forbidden_chars):
            return False

        return True
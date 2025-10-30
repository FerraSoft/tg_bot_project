"""
Централизованный менеджер контекстных меню с учетом прав доступа.
Отвечает за создание и управление меню в зависимости от роли пользователя.
"""

import logging
from typing import Dict, List, Callable, Any, Optional
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from .permissions import UserRole, permission_manager
from utils.formatters import KeyboardFormatter


class MenuConfig:
    """Конфигурация меню"""
    def __init__(self, menu_id: str, builder: Callable, required_role: UserRole,
                 level: str, description: str = ""):
        self.menu_id = menu_id
        self.builder = builder
        self.required_role = required_role
        self.level = level
        self.description = description


class ContextMenuManager:
    """
    Централизованный менеджер контекстных меню.

    Обеспечивает:
    - Регистрацию меню с учетом прав доступа
    - Динамическое построение меню для пользователей
    - Разделение меню по уровням доступа
    - Переиспользование компонентов меню
    """

    def __init__(self, permission_manager_instance, formatter: KeyboardFormatter):
        """
        Инициализация менеджера меню.

        Args:
            permission_manager_instance: Экземпляр менеджера разрешений
            formatter: Форматтер клавиатур
        """
        self.permission_manager = permission_manager_instance
        self.formatter = formatter
        self.logger = logging.getLogger(__name__)

        # Регистрация меню по ID
        self.menus: Dict[str, MenuConfig] = {}

        # Группировка меню по уровням доступа
        self.menu_levels: Dict[str, List[str]] = {
            'user': [],
            'moderator': [],
            'admin': [],
            'super_admin': []
        }

        # Кеш построенных меню для оптимизации
        self.menu_cache: Dict[str, InlineKeyboardMarkup] = {}

        # Инициализация стандартных меню
        self._initialize_default_menus()

    def _initialize_default_menus(self):
        """Инициализация стандартных меню системы"""
        # Меню уровня USER
        self.register_menu(
            'menu_main', self._build_main_menu, UserRole.USER, 'user',
            'Главное меню бота'
        )
        self.register_menu(
            'menu_help', self._build_help_menu, UserRole.USER, 'user',
            'Меню помощи'
        )
        self.register_menu(
            'menu_games', self._build_games_menu, UserRole.USER, 'user',
            'Меню игр'
        )
        self.register_menu(
            'menu_donate', self._build_donate_menu, UserRole.USER, 'user',
            'Меню донатов'
        )
        self.register_menu(
            'menu_leaderboard', self._build_leaderboard_menu, UserRole.USER, 'user',
            'Таблица лидеров'
        )

        # Меню уровня MODERATOR
        self.register_menu(
            'menu_moderation', self._build_moderation_menu, UserRole.MODERATOR, 'moderator',
            'Меню модерации'
        )
        self.register_menu(
            'mod_warnings', self._build_warnings_menu, UserRole.MODERATOR, 'moderator',
            'Управление предупреждениями'
        )
        self.register_menu(
            'mod_mutes', self._build_mutes_menu, UserRole.MODERATOR, 'moderator',
            'Управление заглушками'
        )
        self.register_menu(
            'mod_stats', self._build_mod_stats_menu, UserRole.MODERATOR, 'moderator',
            'Статистика модерации'
        )

        # Меню уровня ADMIN
        self.register_menu(
            'menu_admin', self._build_admin_menu, UserRole.ADMIN, 'admin',
            'Меню администрирования'
        )
        self.register_menu(
            'menu_triggers', self._build_triggers_menu, UserRole.ADMIN, 'admin',
            'Управление триггерами'
        )
        self.register_menu(
            'admin_users', self._build_admin_users_menu, UserRole.ADMIN, 'admin',
            'Управление пользователями'
        )
        self.register_menu(
            'admin_stats', self._build_admin_stats_menu, UserRole.ADMIN, 'admin',
            'Статистика администрирования'
        )
        self.register_menu(
            'admin_settings', self._build_admin_settings_menu, UserRole.ADMIN, 'admin',
            'Настройки системы'
        )
        self.register_menu(
            'admin_errors', self._build_admin_errors_menu, UserRole.ADMIN, 'admin',
            'Отчеты об ошибках'
        )

        # Меню уровня SUPER_ADMIN
        self.register_menu(
            'admin_system', self._build_system_menu, UserRole.SUPER_ADMIN, 'super_admin',
            'Системные настройки'
        )
        self.register_menu(
            'admin_logs', self._build_logs_menu, UserRole.SUPER_ADMIN, 'super_admin',
            'Системные логи'
        )
        self.register_menu(
            'admin_restart', self._build_restart_menu, UserRole.SUPER_ADMIN, 'super_admin',
            'Управление перезапуском'
        )

    def register_menu(self, menu_id: str, menu_builder: Callable, required_role: UserRole,
                     level: str, description: str = ""):
        """
        Регистрация нового меню.

        Args:
            menu_id: Уникальный идентификатор меню
            menu_builder: Функция-строитель меню
            required_role: Минимальная требуемая роль
            level: Уровень доступа меню
            description: Описание меню
        """
        menu_config = MenuConfig(menu_id, menu_builder, required_role, level, description)
        self.menus[menu_id] = menu_config

        if level not in self.menu_levels:
            self.menu_levels[level] = []
        self.menu_levels[level].append(menu_id)

        self.logger.debug(f"Registered menu: {menu_id} (level: {level}, role: {required_role.value})")

    async def get_menu_for_user(self, menu_id: str, user_role: UserRole,
                               **context) -> Optional[InlineKeyboardMarkup]:
        """
        Получение меню для пользователя с учетом его роли.

        Args:
            menu_id: Идентификатор меню
            user_role: Роль пользователя
            **context: Дополнительный контекст для построения меню

        Returns:
            InlineKeyboardMarkup или None если доступ запрещен
        """
        # Проверка доступности меню
        if not self.is_menu_available(menu_id, user_role):
            self.logger.warning(f"Menu {menu_id} not available for role {user_role.value}")
            return None

        # Получение конфигурации меню
        menu_config = self.menus.get(menu_id)
        if not menu_config:
            self.logger.error(f"Menu configuration not found: {menu_id}")
            return None

        try:
            # Построение меню
            menu = await menu_config.builder(user_role, **context)

            # Кеширование результата
            cache_key = f"{menu_id}_{user_role.value}_{hash(str(context))}"
            self.menu_cache[cache_key] = menu

            return menu

        except Exception as e:
            self.logger.error(f"Error building menu {menu_id}: {e}")
            return None

    def is_menu_available(self, menu_id: str, user_role: UserRole) -> bool:
        """
        Проверка доступности меню для роли пользователя.

        Args:
            menu_id: Идентификатор меню
            user_role: Роль пользователя

        Returns:
            True если меню доступно
        """
        menu_config = self.menus.get(menu_id)
        if not menu_config:
            return False

        # Проверка иерархии ролей (USER < MODERATOR < ADMIN < SUPER_ADMIN)
        role_hierarchy = {
            UserRole.USER: 1,
            UserRole.MODERATOR: 2,
            UserRole.ADMIN: 3,
            UserRole.SUPER_ADMIN: 4
        }

        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(menu_config.required_role, 999)

        return user_level >= required_level

    def get_available_menus_for_role(self, user_role: UserRole) -> List[str]:
        """
        Получение списка доступных меню для роли.

        Args:
            user_role: Роль пользователя

        Returns:
            Список идентификаторов доступных меню
        """
        available_menus = []

        for menu_id, menu_config in self.menus.items():
            if self.is_menu_available(menu_id, user_role):
                available_menus.append(menu_id)

        return sorted(available_menus)

    def get_menus_by_level(self, level: str) -> List[str]:
        """
        Получение меню определенного уровня.

        Args:
            level: Уровень доступа

        Returns:
            Список идентификаторов меню уровня
        """
        return self.menu_levels.get(level, [])

    def clear_cache(self):
        """Очистка кеша меню"""
        self.menu_cache.clear()
        self.logger.debug("Menu cache cleared")

    # Методы построения стандартных меню

    async def _build_main_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение главного меню"""
        chat_type = context.get('chat_type', 'private')
        return self.formatter.create_main_menu(user_role.value, chat_type)

    async def _build_help_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню помощи"""
        # Базовые кнопки для всех
        keyboard = [
            [InlineKeyboardButton("📋 Помощь", callback_data='menu_help')],
            [InlineKeyboardButton("🎮 Игры", callback_data='menu_games')],
            [InlineKeyboardButton("💰 Донат", callback_data='menu_donate')],
            [InlineKeyboardButton("🏆 Лидеры", callback_data='menu_leaderboard')]
        ]

        # Добавление кнопок в зависимости от роли
        if user_role in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            keyboard.insert(1, [InlineKeyboardButton("🛡️ Модерация", callback_data='menu_moderation')])

        if user_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            keyboard.insert(2, [InlineKeyboardButton("👑 Админ", callback_data='menu_admin')])

        keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data='close_menu')])

        return InlineKeyboardMarkup(keyboard)

    async def _build_games_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню игр"""
        chat_type = context.get('chat_type', 'private')
        return self.formatter.create_games_menu(chat_type)

    async def _build_donate_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню донатов"""
        return self.formatter.create_donation_menu()

    async def _build_leaderboard_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню таблицы лидеров"""
        # Здесь будет логика получения и отображения лидеров
        keyboard = [
            [InlineKeyboardButton("📊 Общая таблица", callback_data='leaderboard_general')],
            [InlineKeyboardButton("🎮 По играм", callback_data='leaderboard_games')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_main')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_moderation_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню модерации"""
        return self.formatter.create_moderation_menu(user_role.value)

    async def _build_warnings_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню предупреждений"""
        keyboard = [
            [InlineKeyboardButton("⚠️ Активные предупреждения", callback_data='warnings_active')],
            [InlineKeyboardButton("📋 История", callback_data='warnings_history')],
            [InlineKeyboardButton("🔍 Поиск пользователя", callback_data='warnings_search')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_moderation')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_mutes_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню заглушек"""
        keyboard = [
            [InlineKeyboardButton("🔇 Активные заглушки", callback_data='mutes_active')],
            [InlineKeyboardButton("📋 История", callback_data='mutes_history')],
            [InlineKeyboardButton("🔍 Поиск пользователя", callback_data='mutes_search')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_moderation')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_mod_stats_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню статистики модерации"""
        keyboard = [
            [InlineKeyboardButton("📊 Общая статистика", callback_data='mod_stats_general')],
            [InlineKeyboardButton("👥 По пользователям", callback_data='mod_stats_users')],
            [InlineKeyboardButton("📅 По периодам", callback_data='mod_stats_periods')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_moderation')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_admin_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню администрирования"""
        return self.formatter.create_admin_menu(user_role.value)

    async def _build_admin_users_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню управления пользователями"""
        keyboard = [
            [InlineKeyboardButton("👥 Список пользователей", callback_data='admin_users_list')],
            [InlineKeyboardButton("🔍 Поиск пользователя", callback_data='admin_users_search')],
            [InlineKeyboardButton("📊 Статистика пользователей", callback_data='admin_users_stats')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_admin_stats_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню статистики администрирования"""
        keyboard = [
            [InlineKeyboardButton("📊 Общая статистика", callback_data='admin_stats_general')],
            [InlineKeyboardButton("🎮 Статистика игр", callback_data='admin_stats_games')],
            [InlineKeyboardButton("💰 Статистика донатов", callback_data='admin_stats_donates')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_admin_settings_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню настроек"""
        keyboard = [
            [InlineKeyboardButton("🤖 Настройки бота", callback_data='admin_settings_bot')],
            [InlineKeyboardButton("🛡️ Безопасность", callback_data='admin_settings_security')],
            [InlineKeyboardButton("🔧 Технические настройки", callback_data='admin_settings_tech')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_admin_errors_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню отчетов об ошибках"""
        keyboard = [
            [InlineKeyboardButton("🐛 Последние ошибки", callback_data='admin_errors_recent')],
            [InlineKeyboardButton("📊 Статистика ошибок", callback_data='admin_errors_stats')],
            [InlineKeyboardButton("🔍 Поиск ошибок", callback_data='admin_errors_search')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_system_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню системных настроек"""
        keyboard = [
            [InlineKeyboardButton("⚙️ Конфигурация системы", callback_data='admin_system_config')],
            [InlineKeyboardButton("💾 Резервное копирование", callback_data='admin_system_backup')],
            [InlineKeyboardButton("🔄 Обновления", callback_data='admin_system_updates')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_logs_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню системных логов"""
        keyboard = [
            [InlineKeyboardButton("📋 Логи приложения", callback_data='admin_logs_app')],
            [InlineKeyboardButton("🔗 Логи базы данных", callback_data='admin_logs_db')],
            [InlineKeyboardButton("🌐 Логи API", callback_data='admin_logs_api')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_restart_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню управления перезапуском"""
        keyboard = [
            [InlineKeyboardButton("🔄 Мягкий перезапуск", callback_data='admin_restart_soft')],
            [InlineKeyboardButton("💥 Полный перезапуск", callback_data='admin_restart_hard')],
            [InlineKeyboardButton("⚠️ Экстренная остановка", callback_data='admin_restart_emergency')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _build_triggers_menu(self, user_role: UserRole, **context) -> InlineKeyboardMarkup:
        """Построение меню управления триггерами"""
        keyboard = [
            [InlineKeyboardButton("📋 Список триггеров", callback_data='triggers_list')],
            [InlineKeyboardButton("➕ Создать триггер", callback_data='triggers_create')],
            [InlineKeyboardButton("📝 Шаблоны триггеров", callback_data='triggers_templates')],
            [InlineKeyboardButton("📊 Статистика триггеров", callback_data='triggers_stats')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')]
        ]
        return InlineKeyboardMarkup(keyboard)


# Глобальный экземпляр менеджера меню
menu_manager = None

def create_menu_manager(permission_manager_instance, formatter: KeyboardFormatter):
    """
    Создание глобального экземпляра менеджера меню.

    Args:
        permission_manager_instance: Экземпляр менеджера разрешений
        formatter: Форматтер клавиатур

    Returns:
        ContextMenuManager: Настроенный менеджер меню
    """
    global menu_manager
    menu_manager = ContextMenuManager(permission_manager_instance, formatter)
    return menu_manager
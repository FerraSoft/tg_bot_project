"""
Система ролей и разрешений бота.
Определяет уровни доступа и правила для различных операций.
"""

from enum import Enum
from typing import Dict, List, Set
from dataclasses import dataclass


class UserRole(Enum):
    """Перечисление ролей пользователей"""
    USER = "user"           # Обычный пользователь
    MODERATOR = "moderator" # Модератор
    ADMIN = "admin"         # Администратор
    SUPER_ADMIN = "super_admin"  # Супер-администратор


class Permission(Enum):
    """Перечисление разрешений"""
    # Базовые команды (доступны всем)
    USE_BASIC_COMMANDS = "use_basic_commands"
    USE_GAMES = "use_games"
    USE_INFO = "use_info"
    USE_DONATE = "use_donate"

    # Модераторские разрешения
    WARN_USERS = "warn_users"
    MUTE_USERS = "mute_users"
    VIEW_MODERATION_STATS = "view_moderation_stats"

    # Администраторские разрешения
    BAN_USERS = "ban_users"
    KICK_USERS = "kick_users"
    MANAGE_SCHEDULED_POSTS = "manage_scheduled_posts"
    EXPORT_DATA = "export_data"
    VIEW_ADMIN_STATS = "view_admin_stats"

    # Супер-администраторские разрешения
    MANAGE_SYSTEM = "manage_system"
    MANAGE_ADMINS = "manage_admins"
    VIEW_SYSTEM_LOGS = "view_system_logs"
    MANAGE_ERRORS = "manage_errors"


@dataclass
class RolePermissions:
    """Разрешения для конкретной роли"""
    role: UserRole
    permissions: Set[Permission]
    description: str


# Определение разрешений для каждой роли
ROLE_PERMISSIONS = {
    UserRole.USER: RolePermissions(
        role=UserRole.USER,
        permissions={
            Permission.USE_BASIC_COMMANDS,
            Permission.USE_GAMES,
            Permission.USE_INFO,
            Permission.USE_DONATE,
        },
        description="Обычный пользователь с базовым доступом"
    ),

    UserRole.MODERATOR: RolePermissions(
        role=UserRole.MODERATOR,
        permissions={
            Permission.USE_BASIC_COMMANDS,
            Permission.USE_GAMES,
            Permission.USE_INFO,
            Permission.USE_DONATE,
            Permission.WARN_USERS,
            Permission.MUTE_USERS,
            Permission.VIEW_MODERATION_STATS,
        },
        description="Модератор с правами на предупреждения и заглушку"
    ),

    UserRole.ADMIN: RolePermissions(
        role=UserRole.ADMIN,
        permissions={
            Permission.USE_BASIC_COMMANDS,
            Permission.USE_GAMES,
            Permission.USE_INFO,
            Permission.USE_DONATE,
            Permission.WARN_USERS,
            Permission.MUTE_USERS,
            Permission.VIEW_MODERATION_STATS,
            Permission.BAN_USERS,
            Permission.KICK_USERS,
            Permission.MANAGE_SCHEDULED_POSTS,
            Permission.EXPORT_DATA,
            Permission.VIEW_ADMIN_STATS,
        },
        description="Администратор с полными правами модерации и управления"
    ),

    UserRole.SUPER_ADMIN: RolePermissions(
        role=UserRole.SUPER_ADMIN,
        permissions=set(Permission),  # Все разрешения
        description="Супер-администратор с полным доступом к системе"
    ),
}


class PermissionManager:
    """
    Менеджер разрешений для проверки прав доступа.
    """

    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS

    def get_role_permissions(self, role: UserRole) -> Set[Permission]:
        """
        Получение множества разрешений для роли.

        Args:
            role: Роль пользователя

        Returns:
            Множество разрешений
        """
        if role in self.role_permissions:
            return self.role_permissions[role].permissions
        return set()

    def has_permission(self, user_role: UserRole, permission: Permission) -> bool:
        """
        Проверка наличия разрешения у роли.

        Args:
            user_role: Роль пользователя
            permission: Проверяемое разрешение

        Returns:
            True если разрешение есть
        """
        role_permissions = self.get_role_permissions(user_role)
        return permission in role_permissions

    def get_user_role_from_config(self, user_id: int, config) -> UserRole:
        """
        Определение роли пользователя на основе конфигурации.

        Args:
            user_id: ID пользователя
            config: Конфигурация приложения

        Returns:
            Роль пользователя
        """
        print(f"[DEBUG] get_user_role_from_config: user_id={user_id}")

        # Проверяем супер-администраторов
        if hasattr(config, 'bot_config') and hasattr(config.bot_config, 'super_admin_ids'):
            super_admin_ids = config.bot_config.super_admin_ids
            print(f"[DEBUG] get_user_role_from_config: super_admin_ids={super_admin_ids}")
            if user_id in super_admin_ids:
                print(f"[DEBUG] get_user_role_from_config: user {user_id} is SUPER_ADMIN")
                return UserRole.SUPER_ADMIN

        # Проверяем администраторов
        if hasattr(config, 'bot_config') and hasattr(config.bot_config, 'admin_ids'):
            admin_ids = config.bot_config.admin_ids
            print(f"[DEBUG] get_user_role_from_config: admin_ids={admin_ids}")
            if user_id in admin_ids:
                print(f"[DEBUG] get_user_role_from_config: user {user_id} is ADMIN")
                return UserRole.ADMIN

        # Проверяем модераторов
        if hasattr(config, 'bot_config') and hasattr(config.bot_config, 'moderator_ids'):
            if user_id in config.bot_config.moderator_ids:
                return UserRole.MODERATOR

        # По умолчанию - обычный пользователь
        print(f"[DEBUG] get_user_role_from_config: user {user_id} is USER (default)")
        return UserRole.USER

    async def get_user_role_from_chat(self, update, user_id: int) -> UserRole:
        """
        Определение роли пользователя на основе прав в чате.

        Args:
            update: Обновление от Telegram
            user_id: ID пользователя

        Returns:
            Роль пользователя
        """
        try:
            chat = update.effective_chat
            if chat:
                member = await chat.get_member(user_id)
                if member.status == 'creator':
                    return UserRole.SUPER_ADMIN
                elif member.status == 'administrator':
                    return UserRole.ADMIN
        except Exception:
            pass

        return UserRole.USER

    async def get_effective_role(self, update, user_id: int, config) -> UserRole:
        """
        Получение эффективной роли пользователя (максимальная из всех источников).

        Args:
            update: Обновление от Telegram
            user_id: ID пользователя
            config: Конфигурация приложения

        Returns:
            Эффективная роль пользователя
        """
        import logging
        logger = logging.getLogger(__name__)

        # Проверяем роли в порядке приоритета
        role_priority = {
            UserRole.SUPER_ADMIN: 4,
            UserRole.ADMIN: 3,
            UserRole.MODERATOR: 2,
            UserRole.USER: 1
        }

        # Получаем роль из конфигурации
        config_role = UserRole.USER
        if config is not None:
            config_role = self.get_user_role_from_config(user_id, config)
        logger.debug(f"[DEBUG] get_effective_role: config_role for user {user_id} = {config_role} (config provided: {config is not None})")

        # Получаем роль из базы данных (если есть доступ к репозиторию)
        db_role = await self._get_user_role_from_database(user_id)
        logger.debug(f"[DEBUG] get_effective_role: db_role for user {user_id} = {db_role}")

        # Получаем роль из чата
        chat_role = UserRole.USER
        if update is not None:
            chat_role = await self.get_user_role_from_chat(update, user_id)
        logger.debug(f"[DEBUG] get_effective_role: chat_role for user {user_id} = {chat_role} (update provided: {update is not None})")

        # Возвращаем роль с максимальным приоритетом
        roles = [config_role, db_role, chat_role]
        max_priority_role = max(roles, key=lambda r: role_priority[r])
        logger.info(f"[ROLE_DEBUG] User {user_id}: config={config_role}, db={db_role}, chat={chat_role} -> FINAL={max_priority_role}")

        return max_priority_role

    async def _get_user_role_from_database(self, user_id: int) -> UserRole:
        """
        Получение роли пользователя из базы данных.

        Args:
            user_id: ID пользователя

        Returns:
            Роль пользователя из базы данных
        """
        import logging
        import os
        logger = logging.getLogger(__name__)

        try:
            # Импортируем репозиторий для получения данных пользователя
            from database.repository import UserRepository

            logger.debug(f"[DEBUG] _get_user_role_from_database: Checking role for user {user_id}")

            # Получаем путь к базе данных из переменной окружения или по умолчанию
            db_path = os.getenv('DATABASE_URL', 'telegram_bot/telegram_bot.db')
            logger.debug(f"[DEBUG] _get_user_role_from_database: db_path = {db_path}")
            user_repo = UserRepository(db_path)
            user_data = await user_repo.get_by_id_async(user_id)

            logger.debug(f"[DEBUG] _get_user_role_from_database: user_data = {user_data}")

            if user_data and 'role_id' in user_data:
                role_id = user_data['role_id']
                logger.debug(f"[DEBUG] _get_user_role_from_database: role_id = {role_id}")

                # Преобразование role_id в UserRole
                role_mapping = {
                    1: UserRole.USER,
                    2: UserRole.MODERATOR,
                    3: UserRole.ADMIN,
                    4: UserRole.SUPER_ADMIN
                }
                role = role_mapping.get(role_id, UserRole.USER)
                logger.debug(f"[DEBUG] _get_user_role_from_database: mapped to role = {role}")
                return role
            else:
                logger.debug(f"[DEBUG] _get_user_role_from_database: no role_id in user_data")

        except Exception as e:
            # Если не удалось получить роль из базы данных, возвращаем USER
            logger.warning(f"[DEBUG] _get_user_role_from_database: exception {e} (returning USER role)")

        return UserRole.USER

    def get_required_permissions_for_command(self, command: str) -> Set[Permission]:
        """
        Получение необходимых разрешений для команды.

        Args:
            command: Название команды (без слеша)

        Returns:
            Множество необходимых разрешений
        """
        # Базовые команды доступны всем
        basic_commands = {
            'start', 'help', 'info', 'rank', 'leaderboard',
            'weather', 'news', 'translate', 'donate'
        }

        if command in basic_commands:
            return {Permission.USE_BASIC_COMMANDS}

        # Игровые команды
        game_commands = {'play_game', 'game_rps_start', 'game_2048_start'}
        if command in game_commands or command.startswith('game_'):
            return {Permission.USE_GAMES}

        # Модераторские команды
        moderator_commands = {'warn', 'mute', 'unmute'}
        if command in moderator_commands:
            return {Permission.WARN_USERS, Permission.MUTE_USERS}

        # Администраторские команды
        admin_commands = {
            'ban', 'unban', 'kick', 'admin_stats', 'export_stats',
            'schedule_post', 'list_posts', 'delete_post', 'publish_now',
            'menu_moderation', 'menu_admin', 'menu_triggers', 'admin_users'
        }
        if command in admin_commands:
            return {Permission.BAN_USERS, Permission.VIEW_ADMIN_STATS}

        # Команды системы ошибок (доступны администраторам)
        error_commands = {
            'report_error', 'admin_errors', 'analyze_error_ai',
            'process_all_errors_ai', 'add_error_to_todo', 'add_all_analyzed_to_todo'
        }
        if command in error_commands:
            return {Permission.MANAGE_ERRORS}

        # Меню команды (доступны всем)
        menu_commands = {
            'menu_main', 'menu_help', 'menu_rank', 'menu_donate', 'menu_leaderboard'
        }
        if command in menu_commands:
            return {Permission.USE_BASIC_COMMANDS}

        # По умолчанию требуем базовые разрешения
        return {Permission.USE_BASIC_COMMANDS}

    def can_execute_command(self, user_role: UserRole, command: str) -> bool:
        """
        Проверка возможности выполнения команды пользователем.

        Args:
            user_role: Роль пользователя
            command: Название команды

        Returns:
            True если команда может быть выполнена
        """
        required_permissions = self.get_required_permissions_for_command(command)
        user_permissions = self.get_role_permissions(user_role)

        return required_permissions.issubset(user_permissions)


# Глобальный экземпляр менеджера разрешений
permission_manager = PermissionManager()
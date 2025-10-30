"""
Сервис управления ролями пользователей.
Отвечает за назначение, проверку и получение ролей пользователей.
"""

import json
from typing import Dict, Optional, List
from database.models import Role
from database.repository import BaseRepository


class RoleService:
    """
    Сервис для управления ролями пользователей.

    Предоставляет методы для:
    - Получения ролей пользователей
    - Назначения ролей
    - Проверки прав доступа
    - Валидации ролей
    """

    # Стандартные роли с их ID
    DEFAULT_ROLES = {
        'user': 1,
        'moderator': 2,
        'admin': 3
    }

    def __init__(self, db_path: str):
        """
        Инициализация сервиса ролей.

        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_repo = BaseRepository(db_path)

    def get_user_role_name(self, user_id: int) -> str:
        """
        Получить имя роли пользователя.

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            str: Имя роли ('user', 'moderator', 'admin')
        """
        try:
            # Получаем role_id пользователя
            query = """
                SELECT r.name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.telegram_id = ?
            """
            result = self.db_repo._fetch_one(query, (user_id,))

            if result:
                return result[0]

            # Если пользователь не найден или роль не указана, возвращаем 'user'
            return 'user'

        except Exception as e:
            print(f"Error getting user role: {e}")
            return 'user'  # fallback

    def get_user_role_id(self, user_id: int) -> int:
        """
        Получить ID роли пользователя.

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            int: ID роли
        """
        try:
            query = "SELECT role_id FROM users WHERE telegram_id = ?"
            result = self.db_repo._fetch_one(query, (user_id,))

            return result[0] if result else 1  # default user role

        except Exception as e:
            print(f"Error getting user role ID: {e}")
            return 1

    def assign_role(self, user_id: int, role_name: str) -> bool:
        """
        Назначить роль пользователю.

        Args:
            user_id: ID пользователя в Telegram
            role_name: Имя роли ('user', 'moderator', 'admin')

        Returns:
            bool: True если роль назначена успешно
        """
        try:
            # Проверяем валидность роли
            if not self._validate_role_name(role_name):
                return False

            # Получаем ID роли
            role_id = self._get_role_id_by_name(role_name)
            if not role_id:
                return False

            # Обновляем роль пользователя
            query = "UPDATE users SET role_id = ? WHERE telegram_id = ?"
            self.db_repo._execute_query(query, (role_id, user_id))

            return True

        except Exception as e:
            print(f"Error assigning role: {e}")
            return False

    def is_admin(self, user_id: int) -> bool:
        """
        Проверить, является ли пользователь администратором.

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            bool: True если пользователь администратор
        """
        role_name = self.get_user_role_name(user_id)
        return role_name == 'admin'

    def is_moderator(self, user_id: int) -> bool:
        """
        Проверить, является ли пользователь модератором или администратором.

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            bool: True если пользователь модератор или администратор
        """
        role_name = self.get_user_role_name(user_id)
        return role_name in ['moderator', 'admin']

    def get_role_permissions(self, role_name: str) -> Dict:
        """
        Получить разрешения для роли.

        Args:
            role_name: Имя роли

        Returns:
            Dict: Словарь с разрешениями
        """
        try:
            query = "SELECT permissions FROM roles WHERE name = ?"
            result = self.db_repo._fetch_one(query, (role_name,))

            if result and result[0]:
                return json.loads(result[0])

            # Возвращаем разрешения по умолчанию
            return self._get_default_permissions(role_name)

        except Exception as e:
            print(f"Error getting role permissions: {e}")
            return {}

    def get_all_roles(self) -> List[Role]:
        """
        Получить все активные роли.

        Returns:
            List[Role]: Список ролей
        """
        try:
            query = "SELECT id, name, display_name, description, permissions, is_active FROM roles WHERE is_active = 1"
            rows = self.db_repo._fetch_all(query)

            roles = []
            for row in rows:
                role = Role(
                    id=row[0],
                    name=row[1],
                    display_name=row[2],
                    description=row[3],
                    permissions=row[4],
                    is_active=bool(row[5])
                )
                roles.append(role)

            return roles

        except Exception as e:
            print(f"Error getting all roles: {e}")
            return []

    def _validate_role_name(self, role_name: str) -> bool:
        """
        Проверить валидность имени роли.

        Args:
            role_name: Имя роли

        Returns:
            bool: True если роль валидна
        """
        return role_name in self.DEFAULT_ROLES.keys()

    def _get_role_id_by_name(self, role_name: str) -> Optional[int]:
        """
        Получить ID роли по имени.

        Args:
            role_name: Имя роли

        Returns:
            Optional[int]: ID роли или None
        """
        try:
            query = "SELECT id FROM roles WHERE name = ? AND is_active = 1"
            result = self.db_repo._fetch_one(query, (role_name,))

            return result[0] if result else None

        except Exception as e:
            print(f"Error getting role ID by name: {e}")
            return None

    def _get_default_permissions(self, role_name: str) -> Dict:
        """
        Получить разрешения по умолчанию для роли.

        Args:
            role_name: Имя роли

        Returns:
            Dict: Словарь с разрешениями
        """
        defaults = {
            'user': {
                "can_use_basic_commands": True,
                "can_play_games": True
            },
            'moderator': {
                "can_use_basic_commands": True,
                "can_play_games": True,
                "can_moderate": True,
                "can_warn_users": True
            },
            'admin': {
                "can_use_basic_commands": True,
                "can_play_games": True,
                "can_moderate": True,
                "can_warn_users": True,
                "can_manage_users": True,
                "can_schedule_posts": True,
                "can_export_data": True
            }
        }

        return defaults.get(role_name, {})

    def initialize_roles(self) -> bool:
        """
        Инициализировать стандартные роли в базе данных.

        Returns:
            bool: True если инициализация успешна
        """
        try:
            roles_data = [
                (1, 'user', 'Пользователь', 'Обычный пользователь чата', json.dumps({
                    "can_use_basic_commands": True,
                    "can_play_games": True
                })),
                (2, 'moderator', 'Модератор', 'Модератор чата с правами управления', json.dumps({
                    "can_use_basic_commands": True,
                    "can_play_games": True,
                    "can_moderate": True,
                    "can_warn_users": True
                })),
                (3, 'admin', 'Администратор', 'Администратор бота с полными правами', json.dumps({
                    "can_use_basic_commands": True,
                    "can_play_games": True,
                    "can_moderate": True,
                    "can_warn_users": True,
                    "can_manage_users": True,
                    "can_schedule_posts": True,
                    "can_export_data": True
                }))
            ]

            for role_data in roles_data:
                query = """
                    INSERT OR IGNORE INTO roles (id, name, display_name, description, permissions)
                    VALUES (?, ?, ?, ?, ?)
                """
                self.db_repo._execute_query(query, role_data)

            return True

        except Exception as e:
            print(f"Error initializing roles: {e}")
            return False

    def initialize_admin_users(self, admin_ids: List[int]) -> bool:
        """
        Инициализировать пользователей-администраторов из конфигурации.

        Args:
            admin_ids: Список ID администраторов из конфигурации

        Returns:
            bool: True если инициализация успешна
        """
        try:
            for admin_id in admin_ids:
                try:
                    # Проверяем, существует ли пользователь
                    existing_user = self.db_repo._fetch_one(
                        "SELECT id FROM users WHERE telegram_id = ?", (admin_id,)
                    )

                    if existing_user:
                        # Обновляем роль существующего пользователя на admin
                        query = "UPDATE users SET role_id = ? WHERE telegram_id = ?"
                        self.db_repo._execute_query(query, (3, admin_id))  # 3 = admin role
                        print(f"Updated existing user {admin_id} to admin role")
                    else:
                        # Создаем нового пользователя с ролью admin
                        # Для этого нам нужны дополнительные данные, которые мы не имеем
                        # Поэтому просто пропускаем - пользователь будет создан при первом взаимодействии
                        print(f"Admin user {admin_id} not found in database, will be created on first interaction")
                        continue

                except Exception as e:
                    print(f"Error processing admin user {admin_id}: {e}")
                    continue

            return True

        except Exception as e:
            print(f"Error initializing admin users: {e}")
            return False
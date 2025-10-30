"""
Сервис управления пользователями.
Отвечает за бизнес-логику работы с пользователями.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from core.exceptions import ValidationError
from core.permissions import UserRole, permission_manager
from utils.validators import InputValidator, Validator


@dataclass
class UserProfile:
    """Профиль пользователя"""
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    reputation: int = 0
    rank: str = "Новичок"
    message_count: int = 0
    joined_date: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    warnings: int = 0
    achievements: Optional[List[str]] = None

    def __post_init__(self):
        if self.achievements is None:
            self.achievements = []
        if self.joined_date is None:
            self.joined_date = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()


class UserService:
    """
    Сервис для управления пользователями и их данными.

    Отвечает за:
    - Создание и обновление профилей пользователей
    - Расчет рейтингов и рангов
    - Управление достижениями
    - Статистику активности
    """

    def __init__(self, user_repository, score_repository, role_service=None):
        """
        Инициализация сервиса.

        Args:
            user_repository: Репозиторий пользователей
            score_repository: Репозиторий очков и рейтингов
            role_service: Сервис управления ролями
        """
        self.user_repo = user_repository
        self.score_repo = score_repository
        self.role_service = role_service
        self.logger = logging.getLogger(__name__)

        # Настройки рангов и очков
        self.rank_thresholds = {
            "Новичок": 0,
            "Ученик": 100,
            "Активист": 500,
            "Знаток": 1000,
            "Эксперт": 2500,
            "Мастер": 5000,
            "Гуру": 10000,
            "Легенда": 25000,
            "Капитан": 50000,
            "Генерал": 100000,
            "Император": 250000
        }

        self.rank_names = list(self.rank_thresholds.keys())

    async def get_or_create_user(self, user_id: int, username: str = None,
                                first_name: str = None, last_name: str = None) -> UserProfile:
        """
        Получение пользователя или создание нового профиля.

        Args:
            user_id: ID пользователя
            username: Имя пользователя
            first_name: Имя
            last_name: Фамилия

        Returns:
            Профиль пользователя
        """
        try:
            # Валидация входных данных
            if not isinstance(user_id, int) or user_id <= 0 or user_id > 2147483647:
                raise ValidationError("Неверный ID пользователя")

            # Получаем данные пользователя из репозитория
            user_data = await self.user_repo.get_by_id_async(user_id)
            if user_data and isinstance(user_data, dict):
                user_data = user_data
            else:
                user_data = None
            self.logger.debug(f"Результат get_by_id для {user_id}: {user_data is not None}")

            if user_data:
                self.logger.debug(f"Найден существующий пользователь {user_id}: id={user_data.get('id')}, telegram_id={user_data.get('telegram_id')}, first_name={user_data.get('first_name')}")

                # Проверяем, что все необходимые поля присутствуют и не None
                if not user_data.get('id'):
                    self.logger.error(f"Пользователь {user_id} найден, но поле id отсутствует или None")
                    return None

                # Пользователь существует, обновляем данные
                self.logger.debug(f"Обновление данных существующего пользователя {user_id}")
                updated_data = await self._update_user_data(user_data, username, first_name, last_name)
                self.logger.debug(f"Результат обновления данных для {user_id}: {updated_data is not None}")
                if updated_data:
                    profile = self._map_to_profile(updated_data)
                    self.logger.debug(f"Создан профиль из обновленных данных для {user_id}: {profile is not None}")
                    return profile
                else:
                    self.logger.error(f"Ошибка обновления данных пользователя {user_id}")
                    return None
            else:
                # Создаем нового пользователя
                self.logger.debug(f"Создание нового пользователя {user_id}")
                new_user_data = await self._create_new_user(user_id, username, first_name, last_name)
                self.logger.debug(f"Результат создания нового пользователя {user_id}: {new_user_data is not None}")
                if new_user_data:
                    profile = self._map_to_profile(new_user_data)
                    self.logger.debug(f"Создан профиль из новых данных для {user_id}: {profile is not None}")
                    return profile
                else:
                    self.logger.error(f"Ошибка создания нового пользователя {user_id}")
                    return None

        except Exception as e:
            # Handle potential sqlite3.IntegrityError or other database errors
            if "FOREIGN KEY constraint failed" in str(e) or "IntegrityError" in str(type(e).__name__):
                self.logger.warning(f"Нарушение внешнего ключа для пользователя {user_id}, пропускаем создание ролей")
                # Попытка создания без ролей или с ролью по умолчанию
                try:
                    # Используем роль 1 (user) по умолчанию
                    user_data['role_id'] = 1
                    new_user_data = await self._create_new_user(user_id, username, first_name, last_name)
                    if new_user_data:
                        profile = self._map_to_profile(new_user_data)
                        return profile
                except Exception as retry_error:
                    self.logger.error(f"Повторная попытка создания пользователя {user_id} не удалась: {retry_error}")
                    return None
            else:
                self.logger.error(f"Ошибка базы данных при работе с пользователем {user_id}: {e}")
                return None
        except Exception as e:
            if "FOREIGN KEY constraint failed" in str(e):
                self.logger.warning(f"Нарушение внешнего ключа для пользователя {user_id}, пропускаем создание ролей")
                # Попытка создания без ролей или с ролью по умолчанию
                try:
                    # Используем роль 1 (user) по умолчанию
                    user_data['role_id'] = 1
                    new_user_data = await self._create_new_user(user_id, username, first_name, last_name)
                    if new_user_data:
                        profile = self._map_to_profile(new_user_data)
                        return profile
                except Exception as retry_error:
                    self.logger.error(f"Повторная попытка создания пользователя {user_id} не удалась: {retry_error}")
                    return None
            else:
                self.logger.error(f"Ошибка базы данных при работе с пользователем {user_id}: {e}")
                return None
        except Exception as e:
            self.logger.error(f"Ошибка в get_or_create_user для пользователя {user_id}: {e}", exc_info=True)
            return None

    async def update_user_activity(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """
        Обновление активности пользователя.

        Args:
            user_id: ID пользователя
            chat_id: ID чата

        Returns:
            Результат обновления (включая повышение ранга)
        """
        try:
            # Обновляем статистику активности
            await self.user_repo.update_activity(user_id, chat_id)

            # Обновляем очки
            print(f"[DEBUG] UserService.update_user_activity: calling score_repo.update_score({user_id}, 1)")
            await self.score_repo.update_score(user_id, 1)

            # Проверяем повышение ранга
            rank_update = await self._check_rank_promotion(user_id)

            return {
                'activity_updated': True,
                'rank_promoted': rank_update is not None,
                'rank_update': rank_update
            }
        except Exception as e:
            self.logger.error(f"Ошибка в update_user_activity для пользователя {user_id}: {e}", exc_info=True)
            # Возвращаем результат с ошибкой, но не прерываем выполнение
            return {
                'activity_updated': False,
                'rank_promoted': False,
                'rank_update': None,
                'error': str(e)
            }

    async def add_warning(self, user_id: int, reason: str, admin_id: int) -> bool:
        """
        Добавление предупреждения пользователю.

        Args:
            user_id: ID пользователя
            reason: Причина предупреждения
            admin_id: ID администратора

        Returns:
            True если предупреждение добавлено
        """
        if not InputValidator.validate_text_content(reason, max_length=500):
            raise ValidationError("Неверная причина предупреждения")

        print(f"[DEBUG] UserService.add_warning called: user_id={user_id}, reason='{reason}', admin_id={admin_id}")
        result = await self.user_repo.add_warning(user_id, reason, admin_id)
        print(f"[DEBUG] UserService.add_warning result: {result}")

        # Проверяем обновление счетчика предупреждений
        if result:
            warnings_count = await self.user_repo.get_warnings_count(user_id)
            print(f"[DEBUG] Warnings count after adding warning: {warnings_count}")

        return result

    async def get_user_achievements(self, user_id: int) -> List[Tuple[str, datetime]]:
        """
        Получение достижений пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список достижений с датами разблокировки
        """
        return await self.user_repo.get_user_achievements(user_id)

    async def check_and_unlock_achievements(self, user_id: int) -> List[str]:
        """
        Проверка и разблокировка новых достижений.

        Args:
            user_id: ID пользователя

        Returns:
            Список новых достижений
        """
        self.logger.debug(f"Starting achievement check for user {user_id}")
        user_profile = await self.get_or_create_user(user_id)
        user_stats = await self._get_user_statistics(user_id)
        self.logger.debug(f"User stats for {user_id}: {user_stats}")

        new_achievements = []
        all_achievements = await self.user_repo.get_all_achievements()
        self.logger.debug(f"Total achievements to check: {len(all_achievements)}")

        for achievement in all_achievements:
            achievement_id, name, description, condition_type, condition_value, badge = achievement
            self.logger.debug(f"Checking achievement: {name}, type: {condition_type}, value: {condition_value}")

            if await self._check_achievement_condition(user_profile, user_stats, condition_type, condition_value):
                self.logger.debug(f"Achievement condition met for: {name}")
                if not await self.user_repo.has_achievement(user_id, achievement_id):
                    self.logger.debug(f"Unlocking achievement: {name}")
                    await self.user_repo.unlock_achievement(user_id, achievement_id)
                    new_achievements.append(name)
                else:
                    self.logger.debug(f"Achievement already unlocked: {name}")
            else:
                self.logger.debug(f"Achievement condition NOT met for: {name}")

        self.logger.debug(f"New achievements unlocked: {new_achievements}")
        return new_achievements

    async def get_top_users(self, limit: int = 10) -> List[Tuple[int, str, str, int]]:
        """
        Получение топ пользователей по очкам.

        Args:
            limit: Количество пользователей

        Returns:
            Список пользователей (id, username, first_name, score)
        """
        return await self.user_repo.get_top_users_async(limit)

    async def search_users(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Поиск пользователей по имени или username.

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            Список найденных пользователей
        """
        if not InputValidator.validate_text_content(query, max_length=50):
            raise ValidationError("Неверный поисковый запрос")

        return await self.user_repo.search_users(query, limit)

    def calculate_rank(self, score: int) -> str:
        """
        Расчет ранга пользователя по количеству очков.

        Args:
            score: Количество очков

        Returns:
            Название ранга
        """
        for rank, threshold in reversed(self.rank_thresholds.items()):
            if score >= threshold:
                return rank

        return "Новичок"

    def get_user_role(self, user_id: int) -> str:
        """
        Получение роли пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Название роли
        """
        if self.role_service:
            return self.role_service.get_user_role_name(user_id)
        return UserRole.USER.value  # fallback

    def is_admin(self, user_id: int) -> bool:
        """
        Проверка, является ли пользователь администратором.

        Args:
            user_id: ID пользователя

        Returns:
            True если администратор
        """
        if self.role_service:
            return self.role_service.is_admin(user_id)
        # Используем permission_manager как fallback
        user_role = self.get_user_role(user_id)
        try:
            role_enum = UserRole(user_role)
            return role_enum in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
        except ValueError:
            return False

    def is_moderator(self, user_id: int) -> bool:
        """
        Проверка, является ли пользователь модератором или администратором.

        Args:
            user_id: ID пользователя

        Returns:
            True если модератор или администратор
        """
        if self.role_service:
            return self.role_service.is_moderator(user_id)
        # Используем permission_manager как fallback
        user_role = self.get_user_role(user_id)
        try:
            role_enum = UserRole(user_role)
            return role_enum in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        except ValueError:
            return False

    async def get_user_role_enum_async(self, user_id: int) -> UserRole:
        """
        Получение роли пользователя как enum UserRole (асинхронная версия).

        Args:
            user_id: ID пользователя

        Returns:
            Роль пользователя как enum
        """
        try:
            # Используем permission_manager для получения роли
            from core.permissions import permission_manager
            # Получаем config из Application если возможно, иначе создаем минимальный
            try:
                from core.application import app_instance
                if app_instance and hasattr(app_instance, 'config'):
                    config = app_instance.config
                else:
                    config = self._get_minimal_config_for_permissions()
            except ImportError:
                config = self._get_minimal_config_for_permissions()

            role = await permission_manager.get_effective_role(None, user_id, config)
            print(f"[DEBUG] get_user_role_enum_async: permission_manager returned role: {role.value if hasattr(role, 'value') else role}")  # ОТЛАДКА
            return role
        except Exception as e:
            # Fallback к старому методу
            print(f"[DEBUG] get_user_role_enum_async: permission_manager failed ({e}), using fallback")  # ОТЛАДКА
            role_str = self.get_user_role(user_id)
            try:
                role_enum = UserRole(role_str)
                print(f"[DEBUG] get_user_role_enum_async: fallback returned role: {role_enum.value}")  # ОТЛАДКА
                return role_enum
            except ValueError:
                print(f"[DEBUG] get_user_role_enum_async: fallback failed, returning USER")  # ОТЛАДКА
                return UserRole.USER  # fallback

    def get_user_role_enum(self, user_id: int) -> UserRole:
        """
        Получение роли пользователя как enum UserRole (синхронная версия).

        Args:
            user_id: ID пользователя

        Returns:
            Роль пользователя как enum
        """
        # Создаем event loop для вызова асинхронного метода
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если loop уже запущен, создаем новую задачу
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_user_role_enum_async(user_id))
                    return future.result()
            else:
                return loop.run_until_complete(self.get_user_role_enum_async(user_id))
        except Exception as e:
            print(f"[ERROR] get_user_role_enum: failed to get async role ({e}), using fallback")  # ОТЛАДКА
            role_str = self.get_user_role(user_id)
            try:
                return UserRole(role_str)
            except ValueError:
                return UserRole.USER  # fallback

    def _get_minimal_config_for_permissions(self):
        """Создание минимального конфига для permission_manager"""
        class MinimalConfig:
            def __init__(self):
                self.bot_config = MinimalBotConfig()

        class MinimalBotConfig:
            def __init__(self):
                self.super_admin_ids = []
                self.admin_ids = []
                self.moderator_ids = []

        config = MinimalConfig()
        return config

    def get_rank_progress(self, current_score: int) -> Dict[str, Any]:
        """
        Получение прогресса до следующего ранга.

        Args:
            current_score: Текущие очки пользователя

        Returns:
            Информация о прогрессе
        """
        current_rank = self.calculate_rank(current_score)

        # Находим следующий ранг
        current_index = self.rank_names.index(current_rank)
        next_index = min(current_index + 1, len(self.rank_names) - 1)

        current_threshold = self.rank_thresholds[current_rank]
        next_threshold = self.rank_thresholds[self.rank_names[next_index]]

        progress = current_score - current_threshold
        needed = next_threshold - current_threshold

        return {
            'current_rank': current_rank,
            'next_rank': self.rank_names[next_index] if current_index < len(self.rank_names) - 1 else current_rank,
            'current_score': current_score,
            'progress': progress,
            'needed': needed,
            'percentage': (progress / needed * 100) if needed > 0 else 100
        }

    async def _update_user_data(self, user_data: Dict, username: str, first_name: str, last_name: str) -> Dict:
        """Обновление данных существующего пользователя"""
        try:
            update_data = {}

            if username and user_data.get('username') != username:
                update_data['username'] = username

            if first_name and user_data.get('first_name') != first_name:
                update_data['first_name'] = first_name

            if last_name and user_data.get('last_name') != last_name:
                update_data['last_name'] = last_name

            if update_data:
                self.logger.debug(f"Обновление данных пользователя {user_data['id']}: {update_data}")
                await self.user_repo.update_user(user_data['id'], update_data)
                self.logger.debug(f"Данные пользователя {user_data['id']} успешно обновлены")
            else:
                self.logger.debug(f"Для пользователя {user_data['id']} нет данных для обновления")

            # Возвращаем актуальные данные пользователя - используем telegram_id вместо id
            telegram_id = user_data.get('telegram_id')
            if telegram_id:
                current_data = await self.user_repo.get_by_id_async(telegram_id)
                if current_data:
                    return current_data
                else:
                    self.logger.error(f"Не удалось получить обновленные данные пользователя telegram_id={telegram_id}")
                    return None
            else:
                self.logger.error(f"telegram_id отсутствует в данных пользователя: {user_data}")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении пользователя {user_data.get('id', 'unknown')}: {e}", exc_info=True)
            return None

    async def _create_new_user(self, user_id: int, username: str, first_name: str, last_name: str) -> Dict:
        """Создание нового пользователя"""
        try:
            user_data = {
                'telegram_id': user_id,
                'username': username,
                'first_name': first_name or '',
                'last_name': last_name,
                'joined_date': datetime.now(),
                'last_activity': datetime.now()
            }

            result = await self.user_repo._execute_query_async(
                "INSERT INTO users (telegram_id, username, first_name, last_name, joined_date, last_activity) VALUES (?, ?, ?, ?, ?, ?)",
                (user_data['telegram_id'], user_data.get('username'), user_data.get('first_name'), user_data.get('last_name'), user_data.get('joined_date'), user_data.get('last_activity'))
            )
            result = True

            # Проверяем результат создания пользователя
            if result:
                # Получаем созданного пользователя для возврата полных данных
                return await self.user_repo.get_by_id(user_id)
            else:
                print(f"Ошибка: репозиторий вернул None при создании пользователя {user_id}")
                return None

        except Exception as e:
            print(f"Ошибка при создании пользователя {user_id}: {e}")
            return None

    async def _check_rank_promotion(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Проверка повышения ранга пользователя"""
        user_data = await self.user_repo.get_by_id_async(user_id)
        if not user_data:
            return None

        current_rank = user_data.get('rank', 'Новичок')
        new_rank = self.calculate_rank(user_data.get('reputation', 0))

        if new_rank != current_rank:
            # Обновляем ранг в базе данных
            await self.user_repo.update_rank(user_id, new_rank)

            return {
                'old_rank': current_rank,
                'new_rank': new_rank,
                'user_name': user_data.get('first_name', 'Пользователь'),
                'promoted': True
            }

        return None

    async def _get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        message_count = await self.score_repo.get_message_count(user_id)
        total_score = await self.score_repo.get_total_score(user_id)
        days_active = await self.user_repo.get_days_active(user_id)
        warnings_count = await self.user_repo.get_warnings_count(user_id)

        return {
            'message_count': message_count,
            'total_score': total_score,
            'days_active': days_active,
            'warnings_count': warnings_count
        }

    async def _check_achievement_condition(self, profile: UserProfile, stats: Dict[str, Any],
                                         condition_type: str, condition_value: Any) -> bool:
        """Проверка условия достижения"""
        if condition_type == 'score' and stats.get('total_score', 0) >= condition_value:
            return True
        elif condition_type == 'messages' and stats.get('message_count', 0) >= condition_value:
            return True
        elif condition_type == 'days_active' and stats.get('days_active', 0) >= condition_value:
            return True
        elif condition_type == 'warnings' and stats.get('warnings_count', 0) <= condition_value:
            return True
        elif condition_type == 'donations':
            # Для достижений за донаты проверяем общую сумму донатов
            total_donations = await self.get_total_donations(profile.user_id)
            self.logger.debug(f"Checking donation achievement: total_donations={total_donations}, condition_value={condition_value}")
            result = total_donations >= float(condition_value)
            self.logger.debug(f"Donation achievement condition result: {result}")
            return result

        return False

    def _map_to_profile(self, user_data: Dict) -> UserProfile:
        """Преобразование данных из БД в профиль пользователя"""
        if not user_data:
            raise ValueError("Данные пользователя не могут быть None")

        # Дополнительная проверка на наличие обязательных полей
        if 'id' not in user_data or user_data['id'] is None:
            raise ValueError(f"Обязательное поле 'id' отсутствует в данных пользователя: {user_data}")

        # Преобразование строковых дат в datetime объекты
        joined_date = user_data.get('joined_date')
        last_activity = user_data.get('last_activity')

        if isinstance(joined_date, str):
            try:
                joined_date = datetime.fromisoformat(joined_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                joined_date = None

        if isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                last_activity = None

        return UserProfile(
            user_id=user_data['id'],
            username=user_data.get('username'),
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name'),
            reputation=user_data.get('reputation', 0),
            rank=user_data.get('rank', 'Новичок'),
            message_count=user_data.get('message_count', 0),
            joined_date=joined_date,
            last_activity=last_activity,
            warnings=user_data.get('warnings', 0)
        )

    async def add_donation(self, user_id: int, amount: float) -> bool:
        """
        Добавление доната пользователя.

        Args:
            user_id: ID пользователя
            amount: Сумма доната

        Returns:
            True если донат добавлен успешно
        """
        self.logger.info(f"Начало добавления доната: user_id={user_id}, amount={amount}")

        try:
            # Валидация данных
            self.logger.debug(f"Валидация входных данных для пользователя {user_id}")
            if not Validator.validate_user_id(user_id):
                self.logger.error(f"Неверный ID пользователя: {user_id}")
                raise ValidationError("Неверный ID пользователя")

            if amount <= 0:
                self.logger.error(f"Неверная сумма доната: {amount} (должна быть положительной)")
                raise ValidationError("Сумма доната должна быть положительной")

            self.logger.debug(f"Валидация прошла успешно для пользователя {user_id}")

            # Создаем пользователя, если не существует
            self.logger.debug(f"Получение или создание профиля пользователя {user_id}")
            try:
                user_profile = await self.get_or_create_user(user_id)
                self.logger.debug(f"Результат get_or_create_user для {user_id}: {user_profile is not None}")
                if user_profile:
                    self.logger.debug(f"Профиль пользователя {user_id}: user_id={user_profile.user_id}, first_name={user_profile.first_name}")
                else:
                    self.logger.error(f"get_or_create_user вернул None для пользователя {user_id}")
            except Exception as profile_error:
                self.logger.error(f"Исключение в get_or_create_user для пользователя {user_id}: {profile_error}", exc_info=True)
                return False

            if not user_profile:
                self.logger.error(f"Не удалось создать или получить профиль пользователя {user_id}")
                return False

            self.logger.debug(f"Профиль пользователя {user_id} получен: {user_profile.user_id if user_profile else None}")

            # Получаем текущий год для статистики
            current_year = datetime.now().year
            self.logger.debug(f"Текущий год для статистики: {current_year}")

            # Начинаем транзакцию
            self.logger.debug("Начало транзакции для добавления доната")
            self.logger.debug("Проверка подключения к репозиториям перед транзакцией")
            if self.user_repo is None:
                self.logger.error("user_repo is None - невозможно начать транзакцию")
                return False
            if self.score_repo is None:
                self.logger.error("score_repo is None - невозможно начать транзакцию")
                return False

            try:
                await self.user_repo.begin_transaction()
                await self.score_repo.begin_transaction()
            except Exception as e:
                self.logger.error(f"Не удалось начать транзакцию: {e}")
                return False

            try:
                # Добавляем донат в базу данных
                self.logger.debug(f"Добавление доната в базу данных: user_id={user_id}, amount={amount}, year={current_year}")
                self.logger.debug(f"Вызов user_repo.add_donation с параметрами: user_id={user_id}, amount={amount}, year={current_year}")
                success = await self.user_repo.add_donation(user_id, amount, current_year)
                self.logger.debug(f"Результат user_repo.add_donation: {success}")

                if success:
                    self.logger.info(f"Донат успешно добавлен в базу данных для пользователя {user_id}")

                    # Начисляем очки за донат (1 очко за каждые 100 рублей)
                    points = int(amount // 100)
                    self.logger.debug(f"Расчет очков за донат: amount={amount}, points={points}")
                    if points > 0:
                        self.logger.debug(f"Начисление {points} очков пользователю {user_id}")
                        print(f"[DEBUG] UserService.add_donation: calling score_repo.update_score({user_id}, {points})")
                        score_success = await self.score_repo.update_score(user_id, points)
                        self.logger.debug(f"Результат update_score: {score_success}")
                        if score_success:
                            self.logger.info(f"Начислено {points} очков пользователю {user_id}")
                        else:
                            self.logger.warning(f"Не удалось начислить очки пользователю {user_id}")

                    # Проверяем достижения
                    self.logger.debug(f"Проверка достижений для пользователя {user_id}")
                    await self.check_and_unlock_achievements(user_id)
                    self.logger.debug(f"Проверка достижений завершена для пользователя {user_id}")

                    # Подтверждаем транзакцию
                    await self.user_repo.commit_transaction()
                    await self.score_repo.commit_transaction()
                    self.logger.info(f"Донат успешно обработан для пользователя {user_id}")
                else:
                    self.logger.error(f"Не удалось добавить донат в базу данных для пользователя {user_id}")
                    # Откатываем транзакцию
                    await self.user_repo.rollback_transaction()
                    await self.score_repo.rollback_transaction()
                    return False

                return success

            except Exception as inner_e:
                # Откатываем транзакцию при ошибке
                self.logger.error(f"Ошибка во время транзакции, выполняем откат: {inner_e}")
                try:
                    await self.user_repo.rollback_transaction()
                    await self.score_repo.rollback_transaction()
                except Exception as rollback_e:
                    self.logger.error(f"Ошибка при откате транзакции: {rollback_e}")
                raise inner_e

        except ValidationError as e:
            self.logger.warning(f"Ошибка валидации при добавлении доната для пользователя {user_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при добавлении доната для пользователя {user_id}: {e}", exc_info=True)
            return False

    async def get_total_donations(self, user_id: int, year: int = None) -> float:
        """
        Получение общей суммы донатов пользователя.

        Args:
            user_id: ID пользователя
            year: Год для фильтрации (если None, то все года)

        Returns:
            Общая сумма донатов
        """
        result = await self.user_repo._fetch_one_async(
            "SELECT COALESCE(SUM(amount), 0) as total FROM donations WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)" + (" AND year = ?" if year else ""),
            (user_id, year) if year else (user_id,)
        )
        return result['total'] if result else 0.0
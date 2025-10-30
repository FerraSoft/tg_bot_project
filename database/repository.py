"""
Репозитории для работы с базой данных.
Реализуют паттерн Repository для инкапсуляции логики доступа к данным.
"""

import os
import sqlite3
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from abc import ABC, abstractmethod
from core.exceptions import DatabaseError
from .models import User, Score, Error, ScheduledPost, Achievement, UserAchievement, Warning, Donation, Trigger


class BaseRepository(ABC):
    """Базовый класс репозитория"""

    def __init__(self, database_url: str):
        """
        Инициализация репозитория.

        Args:
            database_url: URL базы данных
        """
        self.database_url = database_url
        self._connection = None

    def _get_connection(self) -> sqlite3.Connection:
        """Получение соединения с базой данных"""
        if self._connection is None:
            try:
                # Выводим информацию об отладке
                print(f"[DEBUG] Connecting to database: {self.database_url}")
                print(f"[DEBUG] Database file exists: {os.path.exists(self.database_url)}")
                if os.path.exists(self.database_url):
                    print(f"[DEBUG] Database file size: {os.path.getsize(self.database_url)} bytes")

                print(f"[DEBUG] Attempting to connect to database: {self.database_url}")
                print(f"[DEBUG] Check same thread: False (allowing multi-threaded access)")
                print(f"[DEBUG] Attempting to connect to database: {self.database_url}")
                print(f"[DEBUG] Check same thread: False (allowing multi-threaded access)")
                print(f"[DEBUG] Attempting to connect to database: {self.database_url}")
                print(f"[DEBUG] Check same thread: False (allowing multi-threaded access)")
                print(f"[DEBUG] Isolation level: None (autocommit mode)")
                self._connection = sqlite3.connect(self.database_url, check_same_thread=False, isolation_level=None)
                print(f"[DEBUG] Database connection established successfully")
                print(f"[DEBUG] Database connection established successfully")
                print(f"[DEBUG] Database connection established successfully")
                self._connection.row_factory = sqlite3.Row
                self._enable_foreign_keys()

                # Включаем WAL mode для лучшей производительности и меньшего количества блокировок
                print(f"[DEBUG] Enabling WAL mode...")
                cursor = self._connection.cursor()
                cursor.execute("PRAGMA journal_mode = WAL")
                wal_result = cursor.fetchone()
                print(f"[DEBUG] WAL mode result: {wal_result}")

                # Включаем synchronous=NORMAL для лучшей производительности
                cursor.execute("PRAGMA synchronous = NORMAL")
                sync_result = cursor.fetchone()
                print(f"[DEBUG] Synchronous mode result: {sync_result}")

                # Создаем таблицы если их нет
                self._create_tables_if_not_exists()

                # Выводим информацию о таблицах
                cursor = self._connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                table_names = [table['name'] for table in tables]
                print(f"[DEBUG] Available tables: {table_names}")

            except sqlite3.Error as e:
                error_msg = f"Ошибка подключения к базе данных {self.database_url}: {e}"
                print(f"[ERROR] {error_msg}")
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
                raise DatabaseError(error_msg)
        return self._connection

    async def _get_connection_async(self) -> sqlite3.Connection:
        """Асинхронное получение соединения с базой данных"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_connection)

    def _enable_foreign_keys(self):
        """Включение внешних ключей"""
        try:
            print(f"[DEBUG] Enabling foreign keys...")
            cursor = self._get_connection().cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            print(f"[DEBUG] Foreign keys enabled successfully")
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to enable foreign keys: {e}")
            raise DatabaseError(f"Ошибка включения внешних ключей: {e}")

    def _create_tables_if_not_exists(self):
        """Создание таблиц если они не существуют"""
        try:
            from .models import DatabaseSchema

            conn = self._get_connection()
            cursor = conn.cursor()

            # Сначала создаем таблицу ролей
            try:
                cursor.execute(DatabaseSchema.TABLES['roles'])
                print(f"[INFO] Created/verified roles table")

                # Добавляем стандартные роли
                cursor.execute("""
                    INSERT OR IGNORE INTO roles (id, name, display_name, description)
                    VALUES
                        (1, 'user', 'Пользователь', 'Обычный пользователь'),
                        (2, 'moderator', 'Модератор', 'Модератор чата'),
                        (3, 'admin', 'Администратор', 'Администратор бота'),
                        (4, 'super_admin', 'Супер-администратор', 'Полный доступ')
                """)
                print(f"[INFO] Standard roles initialized")
            except sqlite3.Error as roles_error:
                print(f"[ERROR] Error creating roles table: {roles_error}")

            # Получаем SQL для создания остальных таблиц
            create_tables_sql = DatabaseSchema.get_create_tables_sql()

            # Создаем остальные таблицы
            for table_name, sql in DatabaseSchema.TABLES.items():
                if table_name != 'roles':  # Роли уже создали выше
                    try:
                        cursor.execute(sql)
                        print(f"[INFO] Created/verified table: {table_name}")
                    except sqlite3.Error as table_error:
                        print(f"[ERROR] Error creating table {table_name}: {table_error}")
                        # Не прерываем выполнение для некритических таблиц
                        if table_name not in ['payments', 'transactions']:  # Эти таблицы могут быть опциональными
                            raise DatabaseError(f"Failed to create table {table_name}: {table_error}")

            print(f"[SUCCESS] Database tables initialized")

        except Exception as e:
            print(f"[ERROR] Error creating tables: {e}")
            # Не прерываем выполнение из-за ошибок создания таблиц

    def _execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Выполнение запроса"""
        try:
            print(f"[DEBUG] Executing query: {query[:100]}{'...' if len(query) > 100 else ''}")
            print(f"[DEBUG] Query params: {params}")
            conn = self._get_connection()
            cursor = conn.cursor()
            print(f"[DEBUG] Connection state: {conn}")
            cursor.execute(query, params)
            print(f"[DEBUG] Query executed, committing...")
            print(f"[DEBUG] Attempting to commit transaction...")
            conn.commit()
            print(f"[DEBUG] Query committed successfully")
            return cursor
        except sqlite3.Error as e:
            error_msg = f"Ошибка выполнения запроса: {e}"
            print(f"❌ DEBUG: {error_msg}")
            print(f"❌ DEBUG: Query: {query}")
            print(f"❌ DEBUG: Params: {params}")
            print(f"❌ DEBUG: Database URL: {self.database_url}")
            import logging
            logging.getLogger(__name__).error(error_msg, exc_info=True)
            raise DatabaseError(error_msg)

    async def _execute_query_async(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Асинхронное выполнение запроса"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_query, query, params)

    def _fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Получение одной записи"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            error_msg = f"Ошибка получения записи: {e}"
            print(f"❌ DEBUG: {error_msg}")
            print(f"❌ DEBUG: Query: {query}")
            print(f"❌ DEBUG: Params: {params}")
            print(f"❌ DEBUG: Database URL: {self.database_url}")
            import logging
            logging.getLogger(__name__).error(error_msg, exc_info=True)
            raise DatabaseError(error_msg)

    async def _fetch_one_async(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Асинхронное получение одной записи"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_one, query, params)

    def _fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Получение всех записей"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            error_msg = f"Ошибка получения записей: {e}"
            print(f"❌ DEBUG: {error_msg}")
            print(f"❌ DEBUG: Query: {query}")
            print(f"❌ DEBUG: Params: {params}")
            print(f"❌ DEBUG: Database URL: {self.database_url}")
            import logging
            logging.getLogger(__name__).error(error_msg, exc_info=True)
            raise DatabaseError(error_msg)

    async def _fetch_all_async(self, query: str, params: tuple = ()) -> List[Dict]:
        """Асинхронное получение всех записей"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_all, query, params)

    async def begin_transaction(self):
        """Начало транзакции"""
        print(f"[DEBUG] Beginning transaction...")
        conn = self._get_connection()
        conn.execute("BEGIN")
        print(f"[DEBUG] Transaction begun successfully")

    async def commit_transaction(self):
        """Подтверждение транзакции"""
        print(f"[DEBUG] Committing transaction...")
        conn = self._get_connection()
        conn.commit()
        print(f"[DEBUG] Transaction committed successfully")

    async def rollback_transaction(self):
        """Откат транзакции"""
        print(f"[DEBUG] Rolling back transaction...")
        conn = self._get_connection()
        conn.rollback()
        print(f"[DEBUG] Transaction rolled back successfully")

    def close(self):
        """Закрытие соединения"""
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
            except sqlite3.Error as e:
                print(f"Ошибка закрытия соединения: {e}")


class UserRepository(BaseRepository):
    """Репозиторий пользователей"""

    def get_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        try:
            # Сначала получаем данные только из таблицы users с JOIN на roles
            user_query = """
                SELECT u.*, r.name as role_name, r.display_name as role_display_name
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
                WHERE u.telegram_id = ?
            """
            user_result = self._fetch_one(user_query, (user_id,))

            if user_result:
                # Проверяем наличие записи в таблице scores
                score_query = "SELECT total_score, message_count, game_wins, donations_total FROM scores WHERE user_id = ?"
                score_result = self._fetch_one(score_query, (user_result['id'],))

                # Объединяем результаты
                combined_result = dict(user_result)
                if score_result:
                    combined_result.update(score_result)
                else:
                    # Если записи в scores нет, добавляем значения по умолчанию
                    combined_result.update({
                        'total_score': 0,
                        'message_count': 0,
                        'game_wins': 0,
                        'donations_total': 0.0
                    })

                return combined_result
            else:
                return None

        except Exception as e:
            print(f"[ERROR] Exception in get_by_id({user_id}): {e}")
            import traceback
            traceback.print_exc()
            return None

    async def get_by_id_async(self, user_id: int) -> Optional[Dict]:
        """Асинхронное получение пользователя по ID"""
        try:
            # Сначала получаем данные только из таблицы users с JOIN на roles
            user_query = """
                SELECT u.*, r.name as role_name, r.display_name as role_display_name
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
                WHERE u.telegram_id = ?
            """
            user_result = await self._fetch_one_async(user_query, (user_id,))

            if user_result:
                # Проверяем наличие записи в таблице scores
                score_query = "SELECT total_score, message_count, game_wins, donations_total FROM scores WHERE user_id = ?"
                score_result = await self._fetch_one_async(score_query, (user_result['id'],))

                # Объединяем результаты
                combined_result = dict(user_result)
                if score_result:
                    combined_result.update(score_result)
                else:
                    # Если записи в scores нет, добавляем значения по умолчанию
                    combined_result.update({
                        'total_score': 0,
                        'message_count': 0,
                        'game_wins': 0,
                        'donations_total': 0.0
                    })

                return combined_result
            else:
                return None

        except Exception as e:
            print(f"[ERROR] Exception in get_by_id_async({user_id}): {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_by_username(self, username: str) -> Optional[Dict]:
        """Получение пользователя по username"""
        query = """
            SELECT u.*, s.total_score, s.message_count, s.game_wins
            FROM users u
            LEFT JOIN scores s ON u.id = s.user_id
            WHERE u.username = ?
        """
        return self._fetch_one(query, (username,))

    def create_user(self, user_data: Dict) -> Dict:
        """Создание нового пользователя"""
        try:
            print(f"[DEBUG REPO] create_user called with data: {user_data}")
            query = """
                INSERT INTO users (telegram_id, username, first_name, last_name, joined_date, last_activity)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                user_data['telegram_id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('joined_date'),
                user_data.get('last_activity')
            )

            print(f"[DEBUG REPO] Executing user insert query with params: {params}")
            cursor = self._execute_query(query, params)

            # Создаем запись в таблице scores
            user_id = cursor.lastrowid
            print(f"[DEBUG REPO] User insert lastrowid: {user_id}")
            if user_id is None or user_id == 0:
                print(f"Ошибка: не удалось получить lastrowid после создания пользователя {user_data['telegram_id']}")
                return None

            try:
                self._create_user_score(user_id)
                print(f"[DEBUG REPO] Created score record for user_id: {user_id}")
            except Exception as e:
                print(f"Ошибка при создании записи очков для пользователя {user_id}: {e}")

            # Возвращаем созданного пользователя
            user = self.get_by_id(user_data['telegram_id'])
            if user is None:
                print(f"Ошибка: не удалось найти пользователя после создания {user_data['telegram_id']}")
            else:
                print(f"[DEBUG REPO] Successfully created user: {user}")
            return user

        except Exception as e:
            print(f"Ошибка при создании пользователя {user_data.get('telegram_id', 'unknown')}: {e}")
            import logging
            logging.getLogger(__name__).error(f"Ошибка при создании пользователя: {e}", exc_info=True)
            return None

    def _create_user_score(self, user_id: int):
        """Создание записи очков для пользователя"""
        try:
            query = "INSERT INTO scores (user_id) VALUES (?)"
            self._execute_query(query, (user_id,))
        except Exception as e:
            print(f"Ошибка при создании записи очков для пользователя {user_id}: {e}")
            import logging
            logging.getLogger(__name__).error(f"Ошибка при создании записи очков: {e}", exc_info=True)

    def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Обновление данных пользователя"""
        if not update_data:
            return True

        set_parts = [f"{key} = ?" for key in update_data.keys()]
        query = f"UPDATE users SET {', '.join(set_parts)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"

        params = list(update_data.values()) + [user_id]

        cursor = self._execute_query(query, tuple(params))
        return cursor.rowcount > 0

    async def update_activity(self, telegram_id: int, chat_id: int) -> Dict:
        """Обновление активности пользователя"""
        # Обновляем время последней активности
        query = "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE telegram_id = ?"
        await self._execute_query_async(query, (telegram_id,))

        # Обновляем статистику сообщений
        score_query = """
            UPDATE scores
            SET message_count = message_count + 1, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
        """
        await self._execute_query_async(score_query, (telegram_id,))

        # Возвращаем обновленные данные
        return await self.get_by_id_async(telegram_id)

    def get_top_users(self, limit: int = 10) -> List[Tuple[int, str, str, int]]:
        """Получение топ пользователей по очкам"""
        query = """
            SELECT u.telegram_id, u.username, u.first_name, COALESCE(s.total_score, 0) as score
            FROM users u
            LEFT JOIN scores s ON u.id = s.user_id
            WHERE u.is_active = 1
            ORDER BY score DESC
            LIMIT ?
        """
        rows = self._fetch_all(query, (limit,))

        return [(row['telegram_id'], row['username'], row['first_name'], row['score']) for row in rows]

    async def get_top_users_async(self, limit: int = 10) -> List[Tuple[int, str, str, int]]:
        """Асинхронное получение топ пользователей по очкам"""
        query = """
            SELECT u.telegram_id, u.username, u.first_name, COALESCE(s.total_score, 0) as score
            FROM users u
            LEFT JOIN scores s ON u.id = s.user_id
            WHERE u.is_active = 1
            ORDER BY score DESC
            LIMIT ?
        """
        rows = await self._fetch_all_async(query, (limit,))

        return [(row['telegram_id'], row['username'], row['first_name'], row['score']) for row in rows]

    def initialize_achievements(self) -> bool:
        """Инициализация стандартных достижений"""
        try:
            # Проверяем, есть ли уже достижения в таблице
            existing_count = self._fetch_one("SELECT COUNT(*) as count FROM achievements", ())
            if existing_count and existing_count['count'] > 0:
                return True  # Достижения уже инициализированы

            # Стандартные достижения
            achievements = [
                ("Первое сообщение", "Отправить первое сообщение в чате", "messages", "1", "💬"),
                ("Болтун", "Отправить 100 сообщений", "messages", "100", "🗣️"),
                ("Коммуникатор", "Отправить 1000 сообщений", "messages", "1000", "📢"),
                ("Первая игра", "Сыграть первую игру", "games", "1", "🎮"),
                ("Игрок", "Выиграть 10 игр", "games", "10", "🏆"),
                ("Чемпион", "Выиграть 100 игр", "games", "100", "👑"),
                ("Первый донат", "Сделать первый донат", "donations", "1", "💰"),
                ("Меценат", "Пожертвовать 1000 рублей", "donations", "1000", "🏦"),
                ("Благотворитель", "Пожертвовать 10000 рублей", "donations", "10000", "💎"),
                ("Новичок", "Набрать 100 очков", "score", "100", "🌟"),
                ("Активист", "Набрать 1000 очков", "score", "1000", "⭐"),
                ("Эксперт", "Набрать 10000 очков", "score", "10000", "🏅"),
                ("Легенда", "Набрать 100000 очков", "score", "100000", "👑"),
                ("Долгожитель", "Быть активным 7 дней", "days_active", "7", "📅"),
                ("Ветеран", "Быть активным 30 дней", "days_active", "30", "🎖️"),
            ]

            # Добавляем достижения в базу данных
            for name, description, condition_type, condition_value, badge in achievements:
                query = """
                    INSERT INTO achievements (name, description, condition_type, condition_value, badge)
                    VALUES (?, ?, ?, ?, ?)
                """
                self._execute_query(query, (name, description, condition_type, condition_value, badge))

            return True

        except Exception as e:
            print(f"Ошибка инициализации достижений: {e}")
            return False

    def search_users(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск пользователей"""
        search_query = """
            SELECT u.*, s.total_score, s.message_count
            FROM users u
            LEFT JOIN scores s ON u.id = s.user_id
            WHERE u.is_active = 1
            AND (u.first_name LIKE ? OR u.username LIKE ? OR u.last_name LIKE ?)
            LIMIT ?
        """

        search_pattern = f"%{query}%"
        params = (search_pattern, search_pattern, search_pattern, limit)

        return self._fetch_all(search_query, params)

    def add_warning(self, user_id: int, reason: str, admin_id: int) -> bool:
        """Добавление предупреждения"""
        print(f"[DEBUG] Repository.add_warning called: user_id={user_id}, reason='{reason}', admin_id={admin_id}")

        # Находим внутренний ID пользователя
        user_query = "SELECT id FROM users WHERE telegram_id = ?"
        user_row = self._fetch_one(user_query, (user_id,))
        if not user_row:
            print(f"[ERROR] Repository.add_warning: пользователь с telegram_id {user_id} не найден в базе данных")
            return False
        internal_user_id = user_row['id']

        # Находим внутренний ID админа
        admin_query = "SELECT id FROM users WHERE telegram_id = ?"
        admin_row = self._fetch_one(admin_query, (admin_id,))
        if not admin_row:
            print(f"[ERROR] Repository.add_warning: админ с telegram_id {admin_id} не найден в базе данных")
            return False
        internal_admin_id = admin_row['id']

        print(f"[DEBUG] Repository.add_warning: internal_user_id={internal_user_id}, internal_admin_id={internal_admin_id}")

        # Получаем текущий счетчик предупреждений перед обновлением
        current_warnings_query = "SELECT warnings FROM users WHERE telegram_id = ?"
        current_warnings_row = self._fetch_one(current_warnings_query, (user_id,))
        current_warnings = current_warnings_row['warnings'] if current_warnings_row else 0
        print(f"[DEBUG] Repository.add_warning: current warnings before update: {current_warnings}")

        query = "INSERT INTO warnings (user_id, reason, admin_id) VALUES (?, ?, ?)"
        cursor = self._execute_query(query, (internal_user_id, reason, internal_admin_id))
        print(f"[DEBUG] Repository.add_warning: warning inserted, rowcount={cursor.rowcount}")

        # Обновляем счетчик предупреждений в профиле пользователя
        update_query = "UPDATE users SET warnings = warnings + 1 WHERE telegram_id = ?"
        update_cursor = self._execute_query(update_query, (user_id,))
        print(f"[DEBUG] Repository.add_warning: warnings counter updated, rowcount={update_cursor.rowcount}")

        # Проверяем результат обновления
        new_warnings_query = "SELECT warnings FROM users WHERE telegram_id = ?"
        new_warnings_row = self._fetch_one(new_warnings_query, (user_id,))
        new_warnings = new_warnings_row['warnings'] if new_warnings_row else 0
        print(f"[DEBUG] Repository.add_warning: warnings after update: {new_warnings}")

        return cursor.rowcount > 0

    def get_warnings_count(self, user_id: int) -> int:
        """Получение количества предупреждений пользователя"""
        query = "SELECT warnings FROM users WHERE telegram_id = ?"
        row = self._fetch_one(query, (user_id,))
        return row['warnings'] if row else 0

    def update_rank(self, user_id: int, new_rank: str) -> bool:
        """Обновление ранга пользователя"""
        query = "UPDATE users SET rank = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?"
        cursor = self._execute_query(query, (new_rank, user_id))
        return cursor.rowcount > 0

    def get_days_active(self, user_id: int) -> int:
        """Получение количества активных дней пользователя"""
        query = """
            SELECT COUNT(DISTINCT DATE(last_activity)) as active_days
            FROM users
            WHERE telegram_id = ?
        """
        row = self._fetch_one(query, (user_id,))
        return row['active_days'] if row else 0

    def add_donation(self, user_id: int, amount: float, year: int) -> bool:
        """Добавление доната пользователя"""
        try:
            print(f"[DEBUG] add_donation called with user_id={user_id}, amount={amount}, year={year}")
            # Находим внутренний ID пользователя
            user_query = "SELECT id FROM users WHERE telegram_id = ?"
            user_row = self._fetch_one(user_query, (user_id,))
            print(f"[DEBUG] User lookup result for telegram_id {user_id}: {user_row}")

            if not user_row:
                print(f"Ошибка: пользователь {user_id} не найден в базе данных")
                return False

            internal_user_id = user_row['id']
            print(f"[DEBUG] Internal user ID: {internal_user_id}")

            # Проверяем, существует ли таблица donations
            table_check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='donations'"
            table_exists = self._fetch_one(table_check_query)
            print(f"[DEBUG] Donations table exists: {table_exists is not None}")

            if not table_exists:
                print(f"[ERROR] Таблица donations не существует!")
                return False

            # Добавляем запись в таблицу donations
            query = "INSERT INTO donations (user_id, amount, year, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)"
            print(f"[DEBUG] Executing donation insert query: {query} with params: ({internal_user_id}, {amount}, {year})")
            cursor = self._execute_query(query, (internal_user_id, amount, year))
            print(f"[DEBUG] Donation insert result - rowcount: {cursor.rowcount}")

            return cursor.rowcount > 0

        except Exception as e:
            print(f"Ошибка при добавлении доната для пользователя {user_id}: {e}")
            import logging
            logging.getLogger(__name__).error(f"Ошибка при добавлении доната: {e}", exc_info=True)
            return False

    def get_total_donations(self, user_id: int, year: int = None) -> float:
        """Получение общей суммы донатов пользователя"""
        # Находим внутренний ID пользователя
        user_query = "SELECT id FROM users WHERE telegram_id = ?"
        user_row = self._fetch_one(user_query, (user_id,))

        if not user_row:
            return 0.0

        internal_user_id = user_row['id']

        if year:
            query = """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM donations
                WHERE user_id = ? AND year = ?
            """
            params = (internal_user_id, year)
        else:
            query = """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM donations
                WHERE user_id = ?
            """
            params = (internal_user_id,)

        row = self._fetch_one(query, params)
        return row['total'] if row else 0.0

    def _create_user_if_not_exists(self, telegram_id: int, username: str = None,
                                  first_name: str = None, last_name: str = None) -> bool:
        """Создание пользователя, если он не существует"""
        # Проверяем, существует ли пользователь
        existing_user = self.get_by_id(telegram_id)
        if existing_user:
            return True  # Пользователь уже существует

        # Создаем нового пользователя
        user_data = {
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name or '',
            'last_name': last_name,
            'joined_date': datetime.now(),
            'last_activity': datetime.now()
        }

        self.create_user(user_data)
        return True

    def get_all_achievements(self) -> List[Dict]:
        """Получение всех достижений"""
        query = "SELECT id, name, description, condition_type, condition_value, badge FROM achievements WHERE is_active = 1"
        return self._fetch_all(query)

    def has_achievement(self, user_id: int, achievement_id: int) -> bool:
        """Проверка, есть ли у пользователя достижение"""
        query = """
            SELECT COUNT(*) as count
            FROM user_achievements
            WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?) AND achievement_id = ?
        """
        row = self._fetch_one(query, (user_id, achievement_id))
        return row['count'] > 0 if row else False

    def unlock_achievement(self, user_id: int, achievement_id: int) -> bool:
        """Разблокировка достижения для пользователя"""
        # Проверяем, что пользователь еще не имеет это достижение
        if self.has_achievement(user_id, achievement_id):
            return False

        # Находим внутренний ID пользователя
        user_query = "SELECT id FROM users WHERE telegram_id = ?"
        user_row = self._fetch_one(user_query, (user_id,))
        if not user_row:
            print(f"Ошибка: пользователь с telegram_id {user_id} не найден в базе данных")
            return False
        internal_user_id = user_row['id']

        print(f"[DEBUG] Unlocking achievement: internal_user_id={internal_user_id}, achievement_id={achievement_id}")

        query = "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)"
        cursor = self._execute_query(query, (internal_user_id, achievement_id))
        return cursor.rowcount > 0

    def get_user_achievements(self, user_id: int) -> List[Tuple[int, datetime]]:
        """Получение достижений пользователя"""
        query = """
            SELECT a.badge, ua.unlocked_at
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = (SELECT id FROM users WHERE telegram_id = ?)
            ORDER BY ua.unlocked_at DESC
        """
        rows = self._fetch_all(query, (user_id,))
        return [(row['badge'], row['unlocked_at']) for row in rows]


class ScoreRepository(BaseRepository):
    """Репозиторий очков и статистики"""

    async def update_score(self, user_id: int, points: int = 1) -> bool:
        """Обновление очков пользователя"""
        # Обновляем total_score в таблице scores
        score_query = """
            UPDATE scores
            SET total_score = total_score + ?, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
        """
        cursor = await self._execute_query_async(score_query, (points, user_id))

        # Также обновляем reputation в таблице users
        reputation_query = """
            UPDATE users
            SET reputation = reputation + ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """
        reputation_cursor = await self._execute_query_async(reputation_query, (points, user_id))

        return cursor.rowcount > 0 and reputation_cursor.rowcount > 0

    def get_total_score(self, user_id: int) -> int:
        """Получение общего количества очков"""
        query = """
            SELECT COALESCE(total_score, 0) as score
            FROM scores
            WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
        """
        row = self._fetch_one(query, (user_id,))
        return row['score'] if row else 0

    def get_message_count(self, user_id: int) -> int:
        """Получение количества сообщений пользователя"""
        query = """
            SELECT COALESCE(message_count, 0) as count
            FROM scores
            WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
        """
        row = self._fetch_one(query, (user_id,))
        return row['count'] if row else 0

    def add_donation(self, user_id: int, amount: float, year: int = None) -> bool:
        """Добавление доната пользователя"""
        try:
            # Находим внутренний ID пользователя
            user_query = "SELECT id FROM users WHERE telegram_id = ?"
            user_row = self._fetch_one(user_query, (user_id,))

            if not user_row:
                print(f"Ошибка: пользователь {user_id} не найден в базе данных")
                return False

            internal_user_id = user_row['id']
            print(f"Добавляем донат для пользователя {user_id} (internal ID: {internal_user_id})")

            if year is None:
                year = datetime.now().year

            # Обновляем сумму донатов в scores
            query = """
                UPDATE scores
                SET donations_total = donations_total + ?
                WHERE user_id = ?
            """
            self._execute_query(query, (amount, internal_user_id))

            # Добавляем запись в таблицу donations
            donation_query = "INSERT INTO donations (user_id, amount, year, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)"
            cursor = self._execute_query(donation_query, (internal_user_id, amount, year))

            return cursor.rowcount > 0

        except Exception as e:
            print(f"Ошибка при добавлении доната для пользователя {user_id}: {e}")
            import logging
            logging.getLogger(__name__).error(f"Ошибка при добавлении доната: {e}", exc_info=True)
            return False

    def get_total_donations(self, user_id: int, year: int = None) -> float:
        """Получение общей суммы донатов"""
        if year:
            query = """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM donations d
                WHERE d.user_id = (SELECT id FROM users WHERE telegram_id = ?)
                AND strftime('%Y', d.created_at) = ?
            """
            params = (user_id, str(year))
        else:
            query = """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM donations d
                WHERE d.user_id = (SELECT id FROM users WHERE telegram_id = ?)
            """
            params = (user_id,)

        row = self._fetch_one(query, params)
        return row['total'] if row else 0.0


class ErrorRepository(BaseRepository):
    """Репозиторий ошибок"""

    def add_error(self, admin_id: int, error_type: str, title: str, description: str, priority: str) -> int:
        """Добавление новой ошибки"""
        # Находим внутренний ID админа
        admin_query = "SELECT id FROM users WHERE telegram_id = ?"
        admin_row = self._fetch_one(admin_query, (admin_id,))
        if not admin_row:
            print(f"Ошибка: админ с telegram_id {admin_id} не найден в базе данных")
            return None
        internal_admin_id = admin_row['id']

        print(f"[DEBUG] Adding error: internal_admin_id={internal_admin_id}, error_type={error_type}")

        query = """
            INSERT INTO errors (admin_id, error_type, title, description, priority)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self._execute_query(query, (internal_admin_id, error_type, title, description, priority))
        return cursor.lastrowid

    def get_errors(self, status: str = None, limit: int = 20) -> List[Dict]:
        """Получение списка ошибок"""
        if status:
            query = """
                SELECT e.*, u.first_name as admin_name, u.username as admin_username
                FROM errors e
                LEFT JOIN users u ON e.admin_id = u.telegram_id
                WHERE e.status = ?
                ORDER BY e.created_at DESC
                LIMIT ?
            """
            params = (status, limit)
        else:
            query = """
                SELECT e.*, u.first_name as admin_name, u.username as admin_username
                FROM errors e
                LEFT JOIN users u ON e.admin_id = u.telegram_id
                ORDER BY e.created_at DESC
                LIMIT ?
            """
            params = (limit,)

        return self._fetch_all(query, params)

    def get_error_by_id(self, error_id: int) -> Optional[Dict]:
        """Получение ошибки по ID"""
        query = """
            SELECT e.*, u.first_name as admin_name, u.username as admin_username
            FROM errors e
            LEFT JOIN users u ON e.admin_id = u.telegram_id
            WHERE e.id = ?
        """
        return self._fetch_one(query, (error_id,))

    def update_error_status(self, error_id: int, status: str) -> bool:
        """Обновление статуса ошибки"""
        query = "UPDATE errors SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cursor = self._execute_query(query, (status, error_id))
        return cursor.rowcount > 0

    def update_error_ai_analysis(self, error_id: int, analysis: str) -> bool:
        """Обновление анализа ИИ"""
        query = "UPDATE errors SET ai_analysis = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cursor = self._execute_query(query, (analysis, error_id))
        return cursor.rowcount > 0

    def mark_error_todo_added(self, error_id: int) -> bool:
        """Пометка ошибки как добавленной в TODO"""
        query = "UPDATE errors SET todo_added = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cursor = self._execute_query(query, (error_id,))
        return cursor.rowcount > 0


class ScheduledPostRepository(BaseRepository):
    """Репозиторий запланированных постов"""

    def add_post(self, chat_id: int, text: str, schedule_time: str, created_by: int, image_path: str = None) -> int:
        """Добавление запланированного поста"""
        query = """
            INSERT INTO scheduled_posts (chat_id, text, schedule_time, created_by, image_path)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self._execute_query(query, (chat_id, text, schedule_time, created_by, image_path))
        return cursor.lastrowid

    def get_posts(self, chat_id: int = None, status: str = "pending") -> List[Dict]:
        """Получение запланированных постов"""
        if chat_id:
            query = """
                SELECT sp.*, u.first_name as creator_name, u.username as creator_username
                FROM scheduled_posts sp
                LEFT JOIN users u ON sp.created_by = u.telegram_id
                WHERE sp.chat_id = ? AND sp.status = ?
                ORDER BY sp.schedule_time ASC
            """
            params = (chat_id, status)
        else:
            query = """
                SELECT sp.*, u.first_name as creator_name, u.username as creator_username
                FROM scheduled_posts sp
                LEFT JOIN users u ON sp.created_by = u.telegram_id
                WHERE sp.status = ?
                ORDER BY sp.schedule_time ASC
            """
            params = (status,)

        return self._fetch_all(query, params)

    def mark_post_published(self, post_id: int) -> bool:
        """Пометка поста как опубликованного"""
        query = """
            UPDATE scheduled_posts
            SET status = 'published', published_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        cursor = self._execute_query(query, (post_id,))
        return cursor.rowcount > 0

    def delete_post(self, post_id: int, user_id: int) -> bool:
        """Удаление поста"""
        query = "DELETE FROM scheduled_posts WHERE id = ? AND created_by = ?"
        cursor = self._execute_query(query, (post_id, user_id))
        return cursor.rowcount > 0
    
    
class TriggerRepository(BaseRepository):
    """Репозиторий триггеров"""

    def get_active_triggers(self, chat_type: str = "group") -> List[Dict]:
        """Получение активных триггеров для указанного типа чата"""
        query = """
            SELECT id, name, description, pattern, response_text, response_sticker, response_gif,
                   is_active, created_by, created_at, trigger_count, last_triggered, chat_type
            FROM triggers
            WHERE is_active = 1 AND chat_type = ?
            ORDER BY created_at DESC
        """
        return self._fetch_all(query, (chat_type,))

    async def get_active_triggers_async(self, chat_type: str = "group") -> List[Dict]:
        """Асинхронное получение активных триггеров"""
        query = """
            SELECT id, name, description, pattern, response_text, response_sticker, response_gif,
                   is_active, created_by, created_at, trigger_count, last_triggered, chat_type
            FROM triggers
            WHERE is_active = 1 AND chat_type = ?
            ORDER BY created_at DESC
        """
        return await self._fetch_all_async(query, (chat_type,))

    def add_trigger(self, trigger_data: Dict) -> int:
        """Добавление нового триггера"""
        query = """
            INSERT INTO triggers (name, description, pattern, response_text, response_sticker,
                                 response_gif, created_by, chat_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            trigger_data['name'],
            trigger_data.get('description'),
            trigger_data['pattern'],
            trigger_data.get('response_text'),
            trigger_data.get('response_sticker'),
            trigger_data.get('response_gif'),
            trigger_data.get('created_by', 0),
            trigger_data.get('chat_type', 'group')
        )
        cursor = self._execute_query(query, params)
        return cursor.lastrowid

    def update_trigger_stats(self, trigger_id: int) -> bool:
        """Обновление статистики срабатывания триггера"""
        query = """
            UPDATE triggers
            SET trigger_count = trigger_count + 1, last_triggered = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        cursor = self._execute_query(query, (trigger_id,))
        return cursor.rowcount > 0

    def get_trigger_by_id(self, trigger_id: int) -> Optional[Dict]:
        """Получение триггера по ID"""
        query = """
            SELECT id, name, description, pattern, response_text, response_sticker, response_gif,
                   is_active, created_by, created_at, trigger_count, last_triggered, chat_type
            FROM triggers
            WHERE id = ?
        """
        return self._fetch_one(query, (trigger_id,))

    def update_trigger(self, trigger_id: int, update_data: Dict) -> bool:
        """Обновление триггера"""
        if not update_data:
            return True

        set_parts = [f"{key} = ?" for key in update_data.keys()]
        query = f"UPDATE triggers SET {', '.join(set_parts)} WHERE id = ?"

        params = list(update_data.values()) + [trigger_id]
        cursor = self._execute_query(query, tuple(params))
        return cursor.rowcount > 0

    def delete_trigger(self, trigger_id: int) -> bool:
        """Удаление триггера"""
        query = "DELETE FROM triggers WHERE id = ?"
        cursor = self._execute_query(query, (trigger_id,))
        return cursor.rowcount > 0

    def get_all_triggers(self) -> List[Dict]:
        """Получение всех триггеров"""
        query = """
            SELECT id, name, description, pattern, response_text, response_sticker, response_gif,
                   is_active, created_by, created_at, trigger_count, last_triggered, chat_type
            FROM triggers
            ORDER BY created_at DESC
        """
        return self._fetch_all(query)

    def toggle_trigger(self, trigger_id: int, is_active: bool) -> bool:
        """Включение/выключение триггера"""
        query = "UPDATE triggers SET is_active = ? WHERE id = ?"
        cursor = self._execute_query(query, (1 if is_active else 0, trigger_id))
        return cursor.rowcount > 0
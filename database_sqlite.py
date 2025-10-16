import sqlite3
import os
from datetime import datetime
import csv
from messages import TECH_MESSAGES

class Database:
    def __init__(self, db_file='telegram_bot.db'):
        self.db_file = db_file
        self.connection = None
        self.connect()
        self.create_tables()

    def connect(self):
        """Установка соединения с SQLite базой данных"""
        try:
            self.connection = sqlite3.connect(self.db_file)
            print(TECH_MESSAGES['db_connected'])
        except sqlite3.Error as error:
            print(TECH_MESSAGES['db_connection_error'].format(error=error))
            self.connection = None

    def create_tables(self):
        """Создание таблиц в базе данных"""
        try:
            cursor = self.connection.cursor()

            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    reputation INTEGER DEFAULT 0,
                    rank TEXT DEFAULT 'Рядовой',
                    message_count INTEGER DEFAULT 0,
                    active_days INTEGER DEFAULT 0,
                    days_since_join INTEGER DEFAULT 0,
                    last_message TIMESTAMP,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    left_at TIMESTAMP,
                    language TEXT DEFAULT 'ru',
                    actions TEXT DEFAULT '[]',
                    score INTEGER DEFAULT 0,
                    warnings INTEGER DEFAULT 0,
                    role TEXT DEFAULT 'user'
                )
            """)

            # Таблица предупреждений
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    reason TEXT,
                    issued_by INTEGER,
                    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица игр
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    status TEXT DEFAULT 'active',
                    participants TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица запланированных постов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    text TEXT NOT NULL,
                    image_path TEXT,
                    schedule_time TIMESTAMP NOT NULL,
                    created_by INTEGER,
                    status TEXT DEFAULT 'scheduled',
                    published_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (user_id)
                )
            """)

            # Таблица достижений
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS achievements (
                    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    achievement_type TEXT NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица донатов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS donations (
                    donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'RUB',
                    donated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            self.connection.commit()
            print(TECH_MESSAGES['db_tables_created'])
        except sqlite3.Error as error:
            print(TECH_MESSAGES['db_tables_error'].format(error=error))

    def add_user(self, user_id, username, first_name, last_name):
        """Добавление нового пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, joined_at, message_count, active_days, days_since_join)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0, 0, 0)
            """, (user_id, username, first_name, last_name))
            self.connection.commit()
        except sqlite3.Error as error:
            print(TECH_MESSAGES['user_added_error'].format(error=error))

    def update_score(self, user_id, points=1):
        """Обновление очков пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE users SET score = score + ?, message_count = message_count + 1, last_message = CURRENT_TIMESTAMP WHERE user_id = ?
            """, (points, user_id))
            self.connection.commit()
        except sqlite3.Error as error:
            print(TECH_MESSAGES['score_update_error'].format(error=error))

    def update_reputation(self, user_id, rep_points=1):
        """Обновление репутации пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE users SET reputation = reputation + ? WHERE user_id = ?
            """, (rep_points, user_id))
            self.connection.commit()
            # Обновление ранга на основе репутации
            self.update_rank(user_id)
        except sqlite3.Error as error:
            print(TECH_MESSAGES['reputation_update_error'].format(error=error))

    def update_rank(self, user_id, chat_id=None, first_name=None):
        """Обновление ранга пользователя на основе репутации"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT reputation, rank FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                reputation = result[0]
                old_rank = result[1]
                new_rank = self.calculate_rank(reputation)

                if new_rank != old_rank:
                    cursor.execute("""
                        UPDATE users SET rank = ? WHERE user_id = ?
                    """, (new_rank, user_id))
                    self.connection.commit()

                    # Если передан chat_id, объявить о повышении в чате
                    if chat_id and first_name:
                        return {"promoted": True, "new_rank": new_rank, "old_rank": old_rank, "name": first_name}
                else:
                    self.connection.commit()
        except sqlite3.Error as error:
            print(TECH_MESSAGES['rank_update_error'].format(error=error))
        return None

    def calculate_rank(self, reputation):
        """Расчет ранга на основе репутации"""
        # Используем константы из messages.py
        from messages import RANK_THRESHOLDS

        for threshold, rank_name in reversed(RANK_THRESHOLDS):
            if reputation >= threshold:
                return rank_name

        return "Рядовой"

    def get_top_users(self, limit=10):
        """Получение топ пользователей по очкам"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, score
                FROM users
                ORDER BY score DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
        except sqlite3.Error as error:
            print(TECH_MESSAGES['top_users_error'].format(error=error))
            return []

    def add_warning(self, user_id, reason, issued_by):
        """Добавление предупреждения пользователю"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO warnings (user_id, reason, issued_by)
                VALUES (?, ?, ?)
            """, (user_id, reason, issued_by))

            cursor.execute("""
                UPDATE users SET warnings = warnings + 1 WHERE user_id = ?
            """, (user_id,))

            self.connection.commit()
        except sqlite3.Error as error:
            print(TECH_MESSAGES['warning_add_error'].format(error=error))

    def get_user_warnings(self, user_id):
        """Получение количества предупреждений пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT warnings FROM users WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as error:
            print(TECH_MESSAGES['warnings_get_error'].format(error=error))
            return 0

    def get_user_info(self, user_id):
        """Получение информации о пользователе"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT user_id, first_name, username, reputation, rank, message_count, active_days, days_since_join, last_message, joined_at, left_at, language, actions, score, warnings, role
                FROM users WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'ID': result[0],
                    'Имя': result[1],
                    'Имя пользователя': result[2] or 'не указано',
                    'Репутация': result[3],
                    'Ранг': result[4],
                    'Количество сообщений': result[5],
                    'Активные дни': result[6],
                    'Дней с присоединения': result[7],
                    'Последнее сообщение': result[8],
                    'Присоединился': result[9],
                    'Покинул': result[10],
                    'Язык': result[11],
                    'Действия': result[12],
                    'Очки': result[13],
                    'Предупреждений': result[14],
                    'Роль': result[15]
                }
            return None
        except sqlite3.Error as error:
            print(TECH_MESSAGES['user_info_error'].format(error=error))
            return None

    def import_users_from_csv(self, csv_file_path):
        """Импорт пользователей из CSV файла"""
        try:
            if not os.path.exists(csv_file_path):
                print(TECH_MESSAGES['csv_file_not_found'].format(file=csv_file_path))
                return False

            imported_count = 0
            updated_count = 0

            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)

                for row in csv_reader:
                    try:
                        user_id = int(row['User ID'])
                        name = row['Name'].strip()
                        username = row['Username'].strip() if row['Username'] != 'N/A' else None
                        xp = int(row['XP']) if row['XP'] else 0
                        rep = int(row['REP']) if row['REP'] else 0

                        # Разделяем имя на first_name и last_name
                        name_parts = name.split(' ', 1)
                        first_name = name_parts[0] if name_parts else name
                        last_name = name_parts[1] if len(name_parts) > 1 else None

                        # Проверяем, существует ли пользователь
                        cursor = self.connection.cursor()
                        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                        existing_user = cursor.fetchone()

                        if existing_user:
                            # Обновляем существующего пользователя
                            cursor.execute("""
                                UPDATE users
                                SET username = ?, first_name = ?, last_name = ?, score = ?, warnings = ?, reputation = ?
                                WHERE user_id = ?
                            """, (username, first_name, last_name, xp, rep, rep, user_id))
                            updated_count += 1
                        else:
                            # Добавляем нового пользователя
                            cursor.execute("""
                                INSERT INTO users (user_id, username, first_name, last_name, score, warnings, reputation)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (user_id, username, first_name, last_name, xp, rep, rep))
                            imported_count += 1

                        self.connection.commit()

                    except (ValueError, KeyError) as e:
                        print(TECH_MESSAGES['csv_row_error'].format(row=row, error=e))
                        continue

            print(f"Импорт завершен. Добавлено: {imported_count}, Обновлено: {updated_count}")
            return True

        except sqlite3.Error as error:
            print(TECH_MESSAGES['csv_import_error'].format(error=error))
            return False

    def add_scheduled_post(self, chat_id, text, schedule_time, created_by, image_path=None):
        """Добавление запланированного поста"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO scheduled_posts (chat_id, text, image_path, schedule_time, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, text, image_path, schedule_time, created_by))
            self.connection.commit()
            return cursor.lastrowid
        except sqlite3.Error as error:
            print(f"Ошибка при добавлении поста: {error}")
            return None

    def get_scheduled_posts(self, chat_id=None, limit=50):
        """Получение списка запланированных постов"""
        try:
            cursor = self.connection.cursor()
            if chat_id:
                cursor.execute("""
                    SELECT sp.post_id, sp.chat_id, sp.text, sp.image_path, sp.schedule_time,
                           sp.created_by, sp.status, sp.published_at, sp.created_at, u.first_name
                    FROM scheduled_posts sp
                    LEFT JOIN users u ON sp.created_by = u.user_id
                    WHERE sp.chat_id = ? AND sp.status = 'scheduled'
                    ORDER BY sp.schedule_time ASC
                    LIMIT ?
                """, (chat_id, limit))
            else:
                cursor.execute("""
                    SELECT sp.post_id, sp.chat_id, sp.text, sp.image_path, sp.schedule_time,
                           sp.created_by, sp.status, sp.published_at, sp.created_at, u.first_name
                    FROM scheduled_posts sp
                    LEFT JOIN users u ON sp.created_by = u.user_id
                    WHERE sp.status = 'scheduled'
                    ORDER BY sp.schedule_time ASC
                    LIMIT ?
                """, (limit,))

            return cursor.fetchall()
        except sqlite3.Error as error:
            print(f"Ошибка при получении постов: {error}")
            return []

    def get_pending_posts(self):
        """Получение постов, готовых к публикации"""
        try:
            cursor = self.connection.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT post_id, chat_id, text, image_path
                FROM scheduled_posts
                WHERE schedule_time <= ? AND status = 'scheduled'
                ORDER BY schedule_time ASC
            """, (current_time,))

            return cursor.fetchall()
        except sqlite3.Error as error:
            print(f"Ошибка при получении ожидающих постов: {error}")
            return []

    def mark_post_published(self, post_id):
        """Отметить пост как опубликованный"""
        try:
            cursor = self.connection.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                UPDATE scheduled_posts
                SET status = 'published', published_at = ?
                WHERE post_id = ?
            """, (current_time, post_id))
            self.connection.commit()
            return True
        except sqlite3.Error as error:
            print(f"Ошибка при обновлении статуса поста: {error}")
            return False

    def delete_scheduled_post(self, post_id, user_id):
        """Удалить запланированный пост (только создатель или админ)"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                DELETE FROM scheduled_posts
                WHERE post_id = ? AND (created_by = ? OR ? IN (
                    SELECT user_id FROM users WHERE role = 'admin'
                ))
            """, (post_id, user_id, user_id))
            self.connection.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as error:
            print(f"Ошибка при удалении поста: {error}")
            return False

    def unlock_achievement(self, user_id, achievement_type):
        """Разблокировать достижение для пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO achievements (user_id, achievement_type)
                VALUES (?, ?)
            """, (user_id, achievement_type))
            self.connection.commit()
            return cursor.rowcount > 0  # True если достижение было разблокировано впервые
        except sqlite3.Error as error:
            print(f"Ошибка при разблокировке достижения: {error}")
            return False

    def get_user_achievements(self, user_id):
        """Получить достижения пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT achievement_type, unlocked_at
                FROM achievements
                WHERE user_id = ?
                ORDER BY unlocked_at DESC
            """, (user_id,))
            return cursor.fetchall()
        except sqlite3.Error as error:
            print(f"Ошибка при получении достижений: {error}")
            return []

    def add_donation(self, user_id, amount, currency='RUB'):
        """Добавить донат пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO donations (user_id, amount, currency)
                VALUES (?, ?, ?)
            """, (user_id, amount, currency))

            # Начисляем очки за донат (1 очко за каждые 100 рублей)
            points = int(amount // 100)
            if points > 0:
                self.update_score(user_id, points)

            self.connection.commit()
            return True
        except sqlite3.Error as error:
            print(f"Ошибка при добавлении доната: {error}")
            return False

    def get_total_donations(self, user_id, year=None):
        """Получить общую сумму донатов пользователя"""
        try:
            cursor = self.connection.cursor()
            if year:
                cursor.execute("""
                    SELECT SUM(amount) FROM donations
                    WHERE user_id = ? AND strftime('%Y', donated_at) = ?
                """, (user_id, str(year)))
            else:
                cursor.execute("""
                    SELECT SUM(amount) FROM donations
                    WHERE user_id = ?
                """, (user_id,))
            result = cursor.fetchone()
            return result[0] if result[0] else 0
        except sqlite3.Error as error:
            print(f"Ошибка при получении донатов: {error}")
            return 0

    def check_and_unlock_achievements(self, user_id, message_count=None, games_won=None, donations=None):
        """Проверяет и разблокирует достижения"""
        achievements_unlocked = []

        # Достижения за сообщения
        if message_count is None:
            user_info = self.get_user_info(user_id)
            if user_info:
                message_count = user_info['Количество сообщений']

        if message_count >= 1:
            # Проверяем, было ли уже разблокировано достижение первого сообщения
            existing_achievements = self.get_user_achievements(user_id)
            has_first_message = any(achievement[0] == 'first_message' for achievement in existing_achievements)

            if not has_first_message:
                if self.unlock_achievement(user_id, 'first_message'):
                    achievements_unlocked.append('first_message')
        if message_count >= 100:
            existing_achievements = self.get_user_achievements(user_id)
            has_100_messages = any(achievement[0] == '100_messages' for achievement in existing_achievements)
            if not has_100_messages:
                if self.unlock_achievement(user_id, '100_messages'):
                    achievements_unlocked.append('100_messages')

        if message_count >= 1000:
            existing_achievements = self.get_user_achievements(user_id)
            has_1000_messages = any(achievement[0] == '1000_messages' for achievement in existing_achievements)
            if not has_1000_messages:
                if self.unlock_achievement(user_id, '1000_messages'):
                    achievements_unlocked.append('1000_messages')

        # Достижения за игры
        if games_won is None:
            # Здесь можно добавить логику подсчета побед в играх
            pass

        if games_won and games_won >= 10:
            existing_achievements = self.get_user_achievements(user_id)
            has_games_master = any(achievement[0] == 'games_master' for achievement in existing_achievements)
            if not has_games_master:
                if self.unlock_achievement(user_id, 'games_master'):
                    achievements_unlocked.append('games_master')

        # Достижения за донаты
        if donations is None:
            current_year = datetime.now().year
            donations = self.get_total_donations(user_id, current_year)

        if donations >= 100000:  # 100k рублей в год
            existing_achievements = self.get_user_achievements(user_id)
            has_sponsor_year = any(achievement[0] == 'sponsor_year' for achievement in existing_achievements)
            if not has_sponsor_year:
                if self.unlock_achievement(user_id, 'sponsor_year'):
                    achievements_unlocked.append('sponsor_year')

        return achievements_unlocked

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
            print(TECH_MESSAGES['db_closed'])
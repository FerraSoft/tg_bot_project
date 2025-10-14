import psycopg2
from psycopg2 import Error
from config import DB_CONFIG
import csv
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            self.connection.autocommit = True
            print("Успешное подключение к базе данных PostgreSQL")
            self.create_tables()
        except (Exception, Error) as error:
            print(f"Ошибка при подключении к PostgreSQL: {error}")
            self.connection = None

    def create_tables(self):
        """Создание таблиц в базе данных"""
        try:
            cursor = self.connection.cursor()

            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    score INTEGER DEFAULT 0,
                    warnings INTEGER DEFAULT 0,
                    role TEXT DEFAULT 'user',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица предупреждений
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    reason TEXT,
                    issued_by BIGINT,
                    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица игр
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    game_id SERIAL PRIMARY KEY,
                    type TEXT,
                    status TEXT DEFAULT 'active',
                    participants TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            print("Таблицы созданы успешно")
        except (Exception, Error) as error:
            print(f"Ошибка при создании таблиц: {error}")

    def add_user(self, user_id, username, first_name, last_name):
        """Добавление нового пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, username, first_name, last_name))
        except (Exception, Error) as error:
            print(f"Ошибка при добавлении пользователя: {error}")

    def update_score(self, user_id, points=1):
        """Обновление очков пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE users SET score = score + %s WHERE user_id = %s
            """, (points, user_id))
        except (Exception, Error) as error:
            print(f"Ошибка при обновлении очков: {error}")

    def get_top_users(self, limit=10):
        """Получение топ пользователей по очкам"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, score
                FROM users
                ORDER BY score DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
        except (Exception, Error) as error:
            print(f"Ошибка при получении топ пользователей: {error}")
            return []

    def add_warning(self, user_id, reason, issued_by):
        """Добавление предупреждения пользователю"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO warnings (user_id, reason, issued_by)
                VALUES (%s, %s, %s)
            """, (user_id, reason, issued_by))

            cursor.execute("""
                UPDATE users SET warnings = warnings + 1 WHERE user_id = %s
            """, (user_id,))
        except (Exception, Error) as error:
            print(f"Ошибка при добавлении предупреждения: {error}")

    def get_user_warnings(self, user_id):
        """Получение количества предупреждений пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT warnings FROM users WHERE user_id = %s
            """, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except (Exception, Error) as error:
            print(f"Ошибка при получении предупреждений: {error}")
            return 0

    def get_user_info(self, user_id):
        """Получение информации о пользователе"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, last_name, score, warnings, role
                FROM users WHERE user_id = %s
            """, (user_id,))
            return cursor.fetchone()
        except (Exception, Error) as error:
            print(f"Ошибка при получении информации о пользователе: {error}")
            return None

    def import_users_from_csv(self, csv_file_path):
        """Импорт пользователей из CSV файла"""
        try:
            if not os.path.exists(csv_file_path):
                print(f"Файл {csv_file_path} не найден")
                return False

            imported_count = 0
            skipped_count = 0

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
                        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                        existing_user = cursor.fetchone()

                        if existing_user:
                            # Обновляем существующего пользователя
                            cursor.execute("""
                                UPDATE users
                                SET username = %s, first_name = %s, last_name = %s, score = %s, warnings = %s
                                WHERE user_id = %s
                            """, (username, first_name, last_name, xp, rep, user_id))
                            skipped_count += 1
                        else:
                            # Добавляем нового пользователя
                            cursor.execute("""
                                INSERT INTO users (user_id, username, first_name, last_name, score, warnings)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (user_id, username, first_name, last_name, xp, rep))
                            imported_count += 1

                    except (ValueError, KeyError) as e:
                        print(f"Ошибка обработки строки: {row}. Ошибка: {e}")
                        continue

            print(f"Импорт завершен. Добавлено: {imported_count}, Обновлено: {skipped_count}")
            return True

        except (Exception, Error) as error:
            print(f"Ошибка при импорте пользователей из CSV: {error}")
            return False

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
            print("Соединение с PostgreSQL закрыто")
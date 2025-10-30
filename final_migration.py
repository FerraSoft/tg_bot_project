import sqlite3
import os

def final_migration():
    """Финальная миграция для полного соответствия схеме models.py"""
    try:
        # Создаем резервную копию текущей базы данных
        if os.path.exists('telegram_bot.db'):
            backup_name = f"telegram_bot_backup_{sqlite3.datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            os.rename('telegram_bot.db', backup_name)
            print(f"Создана резервная копия: {backup_name}")

        # Создаем новую базу данных с правильной схемой
        conn = sqlite3.connect('telegram_bot.db')
        cursor = conn.cursor()

        print("СОЗДАНИЕ НОВОЙ БАЗЫ ДАННЫХ ПО ПРАВИЛЬНОЙ СХЕМЕ")

        # Создаем все таблицы согласно схеме из models.py
        tables_sql = [
            '''CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                reputation INTEGER DEFAULT 0,
                rank TEXT DEFAULT 'Новичок',
                warnings INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                total_score INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                game_wins INTEGER DEFAULT 0,
                donations_total REAL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )''',

            '''CREATE TABLE achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                condition_type TEXT NOT NULL,
                condition_value TEXT NOT NULL,
                badge TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_id INTEGER NOT NULL,
                unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (achievement_id) REFERENCES achievements(id),
                UNIQUE(user_id, achievement_id)
            )''',

            '''CREATE TABLE warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                admin_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (admin_id) REFERENCES users(id)
            )''',

            '''CREATE TABLE donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                year INTEGER NOT NULL DEFAULT (strftime('%Y', 'now')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )''',

            '''CREATE TABLE errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                error_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'new',
                priority TEXT DEFAULT 'medium',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ai_analysis TEXT,
                todo_added BOOLEAN DEFAULT 0,
                resolved_at DATETIME,
                FOREIGN KEY (admin_id) REFERENCES users(id)
            )''',

            '''CREATE TABLE scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                image_path TEXT,
                schedule_time DATETIME NOT NULL,
                created_by INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                published_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',

            '''CREATE TABLE games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                participants TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )'''
        ]

        # Создаем таблицы
        for i, sql in enumerate(tables_sql, 1):
            cursor.execute(sql)
            print(f"Создана таблица {i}/{len(tables_sql)}")

        # Инициализируем достижения
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

        # Добавляем достижения
        for name, description, condition_type, condition_value, badge in achievements:
            cursor.execute("""
                INSERT INTO achievements (name, description, condition_type, condition_value, badge)
                VALUES (?, ?, ?, ?, ?)
            """, (name, description, condition_type, condition_value, badge))

        print(f"Добавлено {len(achievements)} достижений")

        # Проверяем созданные таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]

        print(f"СОЗДАНО ТАБЛИЦ: {len(table_names)}")
        print(f"СПИСОК ТАБЛИЦ: {table_names}")

        conn.commit()
        conn.close()

        print("ФИНАЛЬНАЯ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        return True

    except Exception as e:
        print(f"Ошибка финальной миграции: {e}")
        return False

if __name__ == "__main__":
    final_migration()
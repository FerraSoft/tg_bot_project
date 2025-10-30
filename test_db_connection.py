import sqlite3

# Тестируем подключение к базе данных
def test_db():
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('telegram_bot.db')
        cursor = conn.cursor()

        # Проверяем существующие таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]

        # Проверяем, есть ли таблица scores
        has_scores = 'scores' in table_names

        # Создаем таблицу scores если её нет
        if not has_scores:
            cursor.execute('''
                CREATE TABLE scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    total_score INTEGER DEFAULT 0,
                    message_count INTEGER DEFAULT 0,
                    game_wins INTEGER DEFAULT 0,
                    donations_total REAL DEFAULT 0.0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        # Проверяем таблицу users
        if 'users' not in table_names:
            cursor.execute('''
                CREATE TABLE users (
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
                )
            ''')

        # Сохраняем изменения
        conn.commit()

        # Проверяем таблицы еще раз
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        final_table_names = [table[0] for table in tables]

        # Закрываем соединение
        conn.close()

        return True

    except Exception as e:
        return False

# Запускаем тест
if __name__ == "__main__":
    success = test_db()
    if success:
        print("SUCCESS")
    else:
        print("FAILED")
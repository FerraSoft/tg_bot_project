import sqlite3

# Простой скрипт создания таблиц базы данных
def create_tables():
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()

    # Создаем таблицу scores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            total_score INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            game_wins INTEGER DEFAULT 0,
            donations_total REAL DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Создаем остальные основные таблицы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
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

    conn.commit()
    conn.close()
    print("Таблицы созданы")

if __name__ == "__main__":
    create_tables()
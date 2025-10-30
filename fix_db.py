import sqlite3

# Создаем соединение с базой данных
conn = sqlite3.connect('telegram_bot.db')
cursor = conn.cursor()

# Создаем таблицу scores если она не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        total_score INTEGER DEFAULT 0,
        message_count INTEGER DEFAULT 0,
        game_wins INTEGER DEFAULT 0,
        donations_total REAL DEFAULT 0.0,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

# Проверяем таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

conn.commit()
conn.close()
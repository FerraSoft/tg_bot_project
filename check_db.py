import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'database.db')

print(f"Checking database at: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    print(f"File size: {os.path.getsize(db_path)} bytes")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"Tables found: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")

        # Check specific tables
        required_tables = ['users', 'scores', 'donations']
        for table in required_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Table '{table}' has {count} rows")

        # Create tables if they don't exist
        print("Creating tables...")

        # SQL for creating tables
        tables_sql = [
            """
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
            """,
            """
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
            """,
            """
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                year INTEGER NOT NULL DEFAULT (strftime('%Y', 'now')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        ]

        for sql in tables_sql:
            try:
                cursor.execute(sql)
                print(f"Created table")
            except sqlite3.Error as e:
                print(f"Error creating table: {e}")

        conn.commit()
        conn.close()
        print("Database check completed successfully")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

else:
    print("Database file does not exist")
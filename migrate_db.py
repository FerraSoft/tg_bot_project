import sqlite3

def migrate_database():
    """Миграция базы данных для добавления недостающих колонок"""
    try:
        conn = sqlite3.connect('telegram_bot.db')
        cursor = conn.cursor()

        print("НАЧАЛО МИГРАЦИИ БАЗЫ ДАННЫХ")

        # Проверяем, есть ли колонка telegram_id в таблице users
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        has_telegram_id = any(col[1] == 'telegram_id' for col in columns)

        if not has_telegram_id:
            print("Добавляем колонку telegram_id в таблицу users...")

            # Добавляем колонку telegram_id
            cursor.execute("ALTER TABLE users ADD COLUMN telegram_id INTEGER")

            # Если user_id и telegram_id должны быть разными, здесь можно добавить логику преобразования
            # Пока предполагаем, что они эквивалентны
            cursor.execute("UPDATE users SET telegram_id = user_id WHERE telegram_id IS NULL")

            print("Колонка telegram_id успешно добавлена")
        else:
            print("Колонка telegram_id уже существует")

        # Проверяем таблицу scores - она должна ссылаться на правильный user_id
        cursor.execute("PRAGMA table_info(scores)")
        scores_columns = cursor.fetchall()
        print(f"Структура таблицы scores проверена: {len(scores_columns)} колонок")

        # Проверяем, что все необходимые таблицы существуют
        required_tables = ['users', 'scores', 'achievements', 'user_achievements', 'warnings', 'donations', 'errors']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        print(f"Существующие таблицы: {existing_tables}")
        print(f"Необходимые таблицы: {required_tables}")

        for table in required_tables:
            if table in existing_tables:
                print(f"Таблица {table}: OK")
            else:
                print(f"Таблица {table}: ОТСУТСТВУЕТ")

        # Проверяем несколько записей для понимания структуры данных
        try:
            cursor.execute("SELECT user_id, username, first_name FROM users LIMIT 3")
            sample_users = cursor.fetchall()
            if sample_users:
                print(f"\nПримеры пользователей ({len(sample_users)} записей):")
                for i, user in enumerate(sample_users, 1):
                    print(f"  Пользователь {i}: ID={user[0]}, Username={user[1]}, Name={user[2]}")
            else:
                print("\nТаблица users пуста")
        except Exception as e:
            print(f"Ошибка чтения пользователей: {e}")

        conn.commit()
        conn.close()

        print("МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
        return True

    except Exception as e:
        print(f"Ошибка миграции базы данных: {e}")
        return False

if __name__ == "__main__":
    migrate_database()
import sqlite3

def analyze_database():
    """Анализ схемы базы данных"""
    try:
        conn = sqlite3.connect('telegram_bot.db')
        cursor = conn.cursor()

        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print("=== АНАЛИЗ СХЕМЫ БАЗЫ ДАННЫХ ===")
        print(f"Найдено таблиц: {len(tables)}")

        for table in tables:
            table_name = table[0]
            print(f"\nТАБЛИЦА: {table_name}")

            # Получаем схему таблицы
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            print("Колонки:")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, is_pk = col
                pk_str = " (PRIMARY KEY)" if is_pk else ""
                not_null_str = " NOT NULL" if not_null else ""
                default_str = f" DEFAULT {default_val}" if default_val else ""
                print(f"  - {col_name} ({col_type}){not_null_str}{default_str}{pk_str}")

        # Проверяем конкретно таблицу users
        print("\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ТАБЛИЦЫ USERS:")
        cursor.execute("PRAGMA table_info(users)")
        users_columns = cursor.fetchall()

        print(f"Количество колонок в users: {len(users_columns)}")
        for col in users_columns:
            col_id, col_name, col_type, not_null, default_val, is_pk = col
            print(f"  {col_id}: {col_name} ({col_type})")

        # Проверяем, есть ли telegram_id
        has_telegram_id = any(col[1] == 'telegram_id' for col in users_columns)
        print(f"\n❓ Есть колонка telegram_id: {'ДА' if has_telegram_id else 'НЕТ'}")

        conn.close()
        return True

    except Exception as e:
        print(f"Ошибка анализа базы данных: {e}")
        return False

if __name__ == "__main__":
    analyze_database()
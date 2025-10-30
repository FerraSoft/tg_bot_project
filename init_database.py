#!/usr/bin/env python3
"""
Скрипт инициализации базы данных для телеграм-бота.
Создает все необходимые таблицы согласно схеме в models.py
"""

import os
import sys
import sqlite3
from database.models import DatabaseSchema

def init_database(db_path: str = "telegram_bot.db"):
    """Инициализация базы данных"""
    print(f"🔄 Инициализация базы данных: {db_path}")

    # Проверяем, существует ли файл базы данных
    db_exists = os.path.exists(db_path)
    print(f"📁 База данных {'уже существует' if db_exists else 'будет создана'}")

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем SQL для создания таблиц
        create_tables_sql = DatabaseSchema.get_create_tables_sql()

        # Создаем таблицы
        for i, sql in enumerate(create_tables_sql, 1):
            print(f"📋 Создание таблицы {i}/{len(create_tables_sql)}")
            cursor.execute(sql)

        # Проверяем созданные таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table['name'] for table in tables]

        print(f"✅ Успешно создано таблиц: {len(table_names)}")
        print(f"📊 Доступные таблицы: {table_names}")

        # Сохраняем изменения
        conn.commit()
        conn.close()

        print("🎉 Инициализация базы данных завершена успешно!")
        return True

    except sqlite3.Error as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    # Если путь к БД передан как аргумент
    db_path = sys.argv[1] if len(sys.argv) > 1 else "telegram_bot.db"
    success = init_database(db_path)
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Скрипт миграции для внедрения системы ролей пользователей.
Добавляет таблицу roles и колонку role_id в таблицу users.
"""

import sqlite3
import json
import sys
import os

# Set UTF-8 encoding for Windows console
try:
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
except:
    pass  # Ignore if encoding setup fails

def migrate_roles():
    """Выполняет миграцию системы ролей"""

    db_path = 'telegram_bot.db'

    # Проверяем существование файла базы данных
    if not os.path.exists(db_path):
        print(f"❌ Файл базы данных {db_path} не найден!")
        return False

    print("🚀 Начинаем миграцию системы ролей...")

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("📋 Создаем таблицу ролей...")

        # Создаем таблицу ролей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                permissions TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Таблица roles создана")

        # Вставляем стандартные роли
        roles_data = [
            (1, 'user', 'Пользователь', 'Обычный пользователь чата', json.dumps({
                "can_use_basic_commands": True,
                "can_play_games": True
            })),
            (2, 'moderator', 'Модератор', 'Модератор чата с правами управления', json.dumps({
                "can_use_basic_commands": True,
                "can_play_games": True,
                "can_moderate": True,
                "can_warn_users": True
            })),
            (3, 'admin', 'Администратор', 'Администратор бота с полными правами', json.dumps({
                "can_use_basic_commands": True,
                "can_play_games": True,
                "can_moderate": True,
                "can_warn_users": True,
                "can_manage_users": True,
                "can_schedule_posts": True,
                "can_export_data": True
            }))
        ]

        print("📝 Добавляем стандартные роли...")
        for role_data in roles_data:
            cursor.execute('''
                INSERT OR IGNORE INTO roles (id, name, display_name, description, permissions)
                VALUES (?, ?, ?, ?, ?)
            ''', role_data)

        print("✅ Стандартные роли добавлены")

        # Добавляем колонку role_id в таблицу users
        print("🔧 Добавляем колонку role_id в таблицу users...")
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN role_id INTEGER DEFAULT 1')
            print("✅ Колонка role_id добавлена")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print("ℹ️  Колонка role_id уже существует")
            else:
                raise e

        # Создаем индекс для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id)')
        print("✅ Индекс idx_users_role_id создан")

        # Проверяем результаты миграции
        cursor.execute('SELECT COUNT(*) as count FROM roles')
        roles_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) as count FROM users')
        users_count = cursor.fetchone()[0]

        print("\n📊 Статистика после миграции:")
        print(f"   • Ролей: {roles_count}")
        print(f"   • Пользователей: {users_count}")

        # Показываем созданные роли
        cursor.execute('SELECT id, name, display_name FROM roles ORDER BY id')
        roles = cursor.fetchall()
        print("\n📋 Созданные роли:")
        for role in roles:
            print(f"   • {role[0]}: {role[1]} ({role[2]})")

        # Подтверждаем изменения
        conn.commit()
        print("\n🎉 Миграция выполнена успешно!")
        print("Теперь можно использовать систему разделения приветствий по ролям.")

        return True

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False

    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    success = migrate_roles()
    sys.exit(0 if success else 1)
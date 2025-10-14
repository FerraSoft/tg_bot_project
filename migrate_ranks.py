#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция рангов пользователей к новой военной системе
"""

import sqlite3
import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_sqlite import Database

def migrate_ranks():
    """Миграция рангов пользователей к новой системе"""
    db = Database()

    try:
        # Получаем всех пользователей
        cursor = db.connection.cursor()
        cursor.execute("SELECT user_id, reputation, rank FROM users")
        users = cursor.fetchall()

        print(f"Найдено {len(users)} пользователей для миграции")

        migrated_count = 0

        for user_id, reputation, old_rank in users:
            # Рассчитываем новый ранг по новой системе
            new_rank = db.calculate_rank(reputation)

            # Обновляем ранг, если он изменился
            if new_rank != old_rank:
                cursor.execute("UPDATE users SET rank = ? WHERE user_id = ?", (new_rank, user_id))
                print(f"Пользователь {user_id}: '{old_rank}' -> '{new_rank}' (репутация: {reputation})")
                migrated_count += 1

        db.connection.commit()
        print(f"\nМиграция завершена! Обновлено рангов: {migrated_count}")

    except sqlite3.Error as error:
        print(f"Ошибка при миграции: {error}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Запуск миграции рангов к военной системе...")
    migrate_ranks()
    print("Миграция завершена!")
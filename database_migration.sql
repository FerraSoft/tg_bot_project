-- Миграция базы данных для внедрения системы ролей
-- Дата создания: 27 октября 2025 г.
-- Цель: Создание таблицы-справочника ролей и обновление таблицы пользователей

-- Создаем таблицу ролей
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    permissions TEXT,  -- JSON строка с разрешениями
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Вставляем стандартные роли
INSERT OR IGNORE INTO roles (id, name, display_name, description, permissions) VALUES
(1, 'user', 'Пользователь', 'Обычный пользователь чата', '{"can_use_basic_commands": true, "can_play_games": true}'),
(2, 'moderator', 'Модератор', 'Модератор чата с правами управления', '{"can_use_basic_commands": true, "can_play_games": true, "can_moderate": true, "can_warn_users": true}'),
(3, 'admin', 'Администратор', 'Администратор бота с полными правами', '{"can_use_basic_commands": true, "can_play_games": true, "can_moderate": true, "can_warn_users": true, "can_manage_users": true, "can_schedule_posts": true, "can_export_data": true}');

-- Добавляем колонку role_id в таблицу users
ALTER TABLE users ADD COLUMN role_id INTEGER DEFAULT 1;

-- Создаем индекс для быстрого поиска по ролям
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);

-- Добавляем foreign key constraint (SQLite не поддерживает добавление FK после создания таблицы)
-- Для существующих баз данных это нужно будет сделать вручную

-- Выводим информацию о миграции
SELECT 'Migration completed: Added roles table and role_id to users table' as migration_status;
SELECT COUNT(*) as roles_count FROM roles;
SELECT COUNT(*) as users_count FROM users;
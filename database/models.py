"""
Модели данных для телеграм-бота.
Определяют структуру данных и их взаимосвязи.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any, Dict


@dataclass
class Role:
    """Модель роли пользователя"""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: Optional[str] = None  # JSON строка с разрешениями
    is_active: bool = True


@dataclass
class User:
    """Модель пользователя"""
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    joined_date: datetime = None
    last_activity: datetime = None
    reputation: int = 0
    rank: str = "Новичок"
    warnings: int = 0
    is_active: bool = True
    role_id: int = 1  # Ссылка на таблицу roles, по умолчанию user

    def __post_init__(self):
        if self.joined_date is None:
            self.joined_date = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()


@dataclass
class Score:
    """Модель очков и статистики пользователя"""
    id: int
    user_id: int
    total_score: int = 0
    message_count: int = 0
    game_wins: int = 0
    donations_total: float = 0.0
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


@dataclass
class Error:
    """Модель ошибки/отчета об ошибке"""
    id: int
    admin_id: int
    error_type: str
    title: str
    description: str
    status: str = "new"
    priority: str = "medium"
    created_at: datetime = None
    updated_at: datetime = None
    ai_analysis: Optional[str] = None
    todo_added: bool = False
    resolved_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class ScheduledPost:
    """Модель запланированного поста"""
    id: int
    chat_id: int
    text: str
    image_path: Optional[str] = None
    schedule_time: datetime = None
    created_by: int = 0
    status: str = "pending"
    published_at: Optional[datetime] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.schedule_time is None:
            self.schedule_time = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Achievement:
    """Модель достижения"""
    id: int
    name: str
    description: str
    condition_type: str
    condition_value: Any
    badge: str
    is_active: bool = True


@dataclass
class UserAchievement:
    """Модель разблокированного достижения пользователя"""
    id: int
    user_id: int
    achievement_id: int
    unlocked_at: datetime = None

    def __post_init__(self):
        if self.unlocked_at is None:
            self.unlocked_at = datetime.now()


@dataclass
class Trigger:
    """Модель триггера"""
    id: int
    name: str
    pattern: str  # Регулярное выражение для сопоставления текста
    description: Optional[str] = None
    response_text: Optional[str] = None
    response_sticker: Optional[str] = None
    response_gif: Optional[str] = None
    reaction_type: Optional[str] = None  # "emoji" для реакции эмодзи
    action_data: Optional[str] = None  # Данные действия, например emoji
    is_active: bool = True
    created_by: int = 0
    created_at: datetime = None
    trigger_count: int = 0  # Количество срабатываний
    last_triggered: Optional[datetime] = None
    chat_type: str = "group"  # "group" или "private"

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Warning:
    """Модель предупреждения пользователя"""
    id: int
    user_id: int
    reason: str
    admin_id: int
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Donation:
    """Модель доната пользователя"""
    id: int
    user_id: int
    amount: float
    year: int = None
    created_at: datetime = None

    def __post_init__(self):
        if self.year is None:
            self.year = datetime.now().year
        if self.created_at is None:
            self.created_at = datetime.now()


class DatabaseSchema:
    """Схема базы данных"""

    TABLES = {
        'roles': '''
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
        ''',

        'users': '''
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
                role_id INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id)
            )
        ''',

        'scores': '''
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
        ''',

        'errors': '''
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                error_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'new',
                priority TEXT DEFAULT 'medium',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ai_analysis TEXT,
                todo_added BOOLEAN DEFAULT 0,
                resolved_at DATETIME,
                FOREIGN KEY (admin_id) REFERENCES users(id)
            )
        ''',

        'scheduled_posts': '''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                image_path TEXT,
                schedule_time DATETIME NOT NULL,
                created_by INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                published_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',

        'achievements': '''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                condition_type TEXT NOT NULL,
                condition_value TEXT NOT NULL,
                badge TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',

        'user_achievements': '''
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_id INTEGER NOT NULL,
                unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (achievement_id) REFERENCES achievements(id),
                UNIQUE(user_id, achievement_id)
            )
        ''',

        'warnings': '''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                admin_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (admin_id) REFERENCES users(id)
            )
        ''',

        'donations': '''
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                year INTEGER NOT NULL DEFAULT (strftime('%Y', 'now')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''',

        'payments': '''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'RUB',
                provider TEXT NOT NULL, -- 'stripe' или 'yookassa'
                external_id TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME,
                metadata TEXT, -- JSON
                error_message TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''',

        'transactions': '''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id INTEGER NOT NULL,
                type TEXT NOT NULL, -- 'payment', 'refund'
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                external_transaction_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                details TEXT, -- JSON
                FOREIGN KEY (payment_id) REFERENCES payments(id)
            )
        ''',

        'triggers': '''
            CREATE TABLE IF NOT EXISTS triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                pattern TEXT NOT NULL,
                response_text TEXT,
                response_sticker TEXT,
                response_gif TEXT,
                reaction_type TEXT,
                action_data TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                trigger_count INTEGER DEFAULT 0,
                last_triggered DATETIME,
                chat_type TEXT DEFAULT 'group'
            )
        ''',

    }

    @classmethod
    def get_create_tables_sql(cls) -> List[str]:
        """Получение SQL для создания всех таблиц"""
        return list(cls.TABLES.values())

    @classmethod
    def get_table_names(cls) -> List[str]:
        """Получение списка имен таблиц"""
        return list(cls.TABLES.keys())
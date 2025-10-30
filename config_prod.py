"""
Продакшн конфигурация телеграм-бота.
Содержит реальные настройки для развертывания в рабочей среде.
"""

import os

# ТОКЕН БОТА (обязательно заменить на реальный)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'ВАШ_РЕАЛЬНЫЙ_ТОКЕН_ЗДЕСЬ')

# ID администраторов бота (заменить на реальные ID)
ADMIN_IDS = [
    123456789,  # Ваш Telegram ID
    987654321   # ID второго администратора (если есть)
]

# ID чата разработчика для уведомлений (заменить на ваш)
DEVELOPER_CHAT_ID = 123456789  # Ваш Telegram ID для уведомлений

# API ключи для внешних сервисов
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', 'ВАШ_КЛЮЧ_ПОГОДЫ')
NEWS_API_KEY = os.getenv('NEWS_API_KEY', 'ВАШ_КЛЮЧ_НОВОСТЕЙ')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'ВАШ_КЛЮЧ_OPENAI')

# Настройки функций
ENABLE_DEVELOPER_NOTIFICATIONS = True  # Включить уведомления разработчика
ENABLE_AI_ERROR_PROCESSING = True      # Включить обработку ошибок ИИ
AI_MODEL = "gpt-3.5-turbo"             # Модель ИИ для обработки ошибок

# Настройки производительности
LOG_LEVEL = "INFO"  # Уровень логирования: DEBUG, INFO, WARNING, ERROR

# Настройки базы данных
DATABASE_URL = os.getenv('DATABASE_URL', 'telegram_bot.db')  # Путь к файлу БД

# Настройки планировщика
SCHEDULER_ENABLED = True  # Включить планировщик постов
MAX_SCHEDULED_POSTS = 100  # Максимальное количество запланированных постов

# Настройки модерации
PROFANITY_FILTER_ENABLED = True  # Включить фильтр мата
AUTO_DELETE_PROFANITY = True    # Автоматически удалять сообщения с матом

# Настройки игр
GAMES_ENABLED = True  # Включить игровые функции
MAX_GAME_SESSIONS = 50  # Максимальное количество одновременных игровых сессий

# Настройки медиа
MEDIA_MODERATION_ENABLED = True  # Включить модерацию медиафайлов
AUTO_TRANSCRIBE_AUDIO = True    # Автоматически транскрибировать аудио

# Безопасность
MAX_MESSAGE_LENGTH = 4000  # Максимальная длина сообщения
MAX_USERNAME_LENGTH = 32   # Максимальная длина username
RATE_LIMIT_REQUESTS = 30  # Лимит запросов в минуту для одного пользователя

# Файлы и директории
TEMP_DIR = "temp/"          # Директория для временных файлов
LOGS_DIR = "logs/"          # Директория для логов
BACKUP_DIR = "backups/"     # Директория для резервных копий

# Создание необходимых директорий
for directory in [TEMP_DIR, LOGS_DIR, BACKUP_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
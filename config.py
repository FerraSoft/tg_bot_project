# Конфигурация бота
# КОПИРУЙТЕ ЭТОТ ФАЙЛ В config_local.py И ЗАПОЛНИТЕ СВОИМИ ДАННЫМИ
# НЕ ЗАГРУЖАЙТЕ config_local.py НА GITHUB!

import os

# Токен Telegram бота (получить у @BotFather)
BOT_TOKEN = "123456789" #ВАШ_ТОКЕН_ЗДЕСЬ

# Ключ API OpenWeatherMap для получения погоды
OPENWEATHER_API_KEY = "ВАШ_API_КЛЮЧ_ЗДЕСЬ"

# Ключ API NewsAPI для получения новостей
NEWS_API_KEY = "ВАШ_API_КЛЮЧ_ЗДЕСЬ"

# AI API ключи - интеграция с российскими AI платформами
GIGACHAT_API_KEY = os.getenv('GIGACHAT_API_KEY', 'ВАШ_GIGACHAT_API_KEY')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY', 'ВАШ_YANDEX_API_KEY')
YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID', 'ВАШ_YANDEX_FOLDER_ID')
MAX_API_TOKEN = os.getenv('MAX_API_TOKEN', 'ВАШ_MAX_API_TOKEN')

# Конфигурация базы данных PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "database": "telegram_bot",
    "user": "your_username",
    "password": "your_password",
    "port": 5432
}

# Администраторы чата (список ID пользователей)
ADMIN_IDS = [123456789, 987654321]  # Замените на реальные ID администраторов

# Настройки планировщика
SCHEDULER_CONFIG = {
    "time_zone": "Europe/Moscow",  # Часовой пояс
    "check_interval": 60,  # Интервал проверки в секундах
}

# Настройки AI сервисов
AI_SETTINGS = {
    'max_tokens': 1000,
    'temperature': 0.7,
    'cache_ttl': 3600,  # 1 час
    'rate_limit': 10  # запросов в минуту
}

# Домены для веб-интерфейса
DOMAINS = {
    'primary': 'bottohelp.ru',
    'secondary': 'ботвпомощь.рф'
}

# Настройки логирования
LOG_CONFIG = {
    "level": "INFO",
    "file": "bot.log",
    "max_size": 10*1024*1024,  # 10 MB
    "backup_count": 5,
    "format": "json",  # JSON format for structured logging
    "sentry_dsn": "YOUR_SENTRY_DSN_HERE",  # Sentry DSN for error tracking
    "enable_sentry": False,  # Enable Sentry integration
    "prometheus_port": 8000  # Port for Prometheus metrics
}
# Конфигурация бота
# КОПИРУЙТЕ ЭТОТ ФАЙЛ В config_local.py И ЗАПОЛНИТЕ СВОИМИ ДАННЫМИ
# НЕ ЗАГРУЖАЙТЕ config_local.py НА GITHUB!

# Токен Telegram бота (получить у @BotFather)
BOT_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

# Ключ API OpenWeatherMap для получения погоды
OPENWEATHER_API_KEY = "ВАШ_API_КЛЮЧ_ЗДЕСЬ"

# Ключ API NewsAPI для получения новостей
NEWS_API_KEY = "ВАШ_API_КЛЮЧ_ЗДЕСЬ"

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

# Настройки логирования
LOG_CONFIG = {
    "level": "INFO",
    "file": "bot.log",
    "max_size": 10*1024*1024,  # 10 MB
    "backup_count": 5
}
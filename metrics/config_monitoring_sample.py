
# Пример настроек мониторинга для config_local.py

# Включение системы мониторинга
ENABLE_SENTRY = True
SENTRY_DSN = "http://localhost:8000/api/1/project/your-project-id/dsn/"

# Настройки Prometheus
PROMETHEUS_PORT = 8000

# Уведомления разработчиков
ENABLE_DEVELOPER_NOTIFICATIONS = True
DEVELOPER_CHAT_ID = 123456789  # Замените на ваш Telegram ID

# Логирование
LOG_CONFIG = {
    "level": "INFO",
    "file": "bot.log",
    "format": "json",
    "max_size": 10*1024*1024,
    "backup_count": 5
}

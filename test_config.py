"""
Тестовая конфигурация для запуска тестов.
Не содержит реальных секретов и токенов.
"""

# Токен тестового бота (фейковый)
BOT_TOKEN = "1234567890:FAKE_TOKEN_FOR_TESTING_ONLY"

# Администраторы (тестовые ID)
ADMIN_IDS = [123456789, 987654321]

# ID чата разработчика (тестовый)
DEVELOPER_CHAT_ID = 123456789

# Флаги функций
ENABLE_DEVELOPER_NOTIFICATIONS = False
ENABLE_AI_ERROR_PROCESSING = False
ENABLE_SENTRY = False
SENTRY_DSN = None
PROMETHEUS_PORT = 8001

# API ключи (фейковые)
OPENAI_API_KEY = "fake_openai_key"
OPENWEATHER_API_KEY = "fake_weather_key"
NEWS_API_KEY = "fake_news_key"

# Модель ИИ
AI_MODEL = "gpt-3.5-turbo"
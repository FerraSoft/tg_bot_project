"""
Конфигурация pytest для тестов обработчиков.
"""

import os
import sys
import tempfile
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from services.user_service import UserService


@pytest.fixture
def test_config():
    """Фикстура с тестовой конфигурацией"""
    # Создаем временный файл конфигурации для тестов
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
BOT_TOKEN = "123456789:test_token_for_testing"
ADMIN_IDS = [123456789, 987654321]
OPENWEATHER_API_KEY = "test_weather_key"
NEWS_API_KEY = "test_news_key"
OPENAI_API_KEY = "test_openai_key"
""")
        config_path = f.name

    try:
        config = Config(config_path)
        yield config
    finally:
        os.unlink(config_path)


@pytest.fixture
def mock_user_service():
    """Мок сервиса пользователей"""
    service = Mock(spec=UserService)
    service.get_or_create_user = AsyncMock()
    service.update_user_activity = AsyncMock()
    service.get_top_users = AsyncMock()
    service.get_rank_progress = Mock()
    return service


@pytest.fixture
def mock_user():
    """Фикстура с мок-объектом пользователя"""
    user = Mock(spec=User)
    user.id = 123456789
    user.username = "test_user"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_bot = False
    return user


@pytest.fixture
def mock_chat():
    """Фикстура с мок-объектом чата"""
    chat = Mock(spec=Chat)
    chat.id = -1001234567890
    chat.type = "group"
    chat.title = "Test Chat"
    return chat


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Фикстура с мок-объектом сообщения"""
    message = Mock(spec=Message)
    message.message_id = 12345
    message.text = "/test command"
    message.from_user = mock_user
    message.chat = mock_chat
    message.date = datetime.now()
    message.reply_text = AsyncMock()
    message.set_reaction = AsyncMock()
    return message


@pytest.fixture
def mock_update(mock_message):
    """Фикстура с мок-объектом обновления"""
    update = Mock(spec=Update)
    update.effective_user = mock_message.from_user
    update.effective_chat = mock_message.chat
    update.message = mock_message
    update.callback_query = None
    return update


@pytest.fixture
def mock_context():
    """Фикстура с мок-объектом контекста"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {}
    context.chat_data = {}
    context.bot = Mock()
    context.bot.send_message = AsyncMock()
    context.application = Mock()
    context.application._date_time = datetime.now()
    return context
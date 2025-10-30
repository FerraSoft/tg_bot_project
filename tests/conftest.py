"""
Конфигурация pytest для телеграм-бота.
Содержит фикстуры и вспомогательные функции для тестирования.
"""

import os
import tempfile
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from core.exceptions import BotException, ValidationError, DatabaseError


@pytest.fixture
def test_config():
    """Фикстура с тестовой конфигурацией"""
    # Создаем конфигурацию с пустыми списками админов для чистых тестов
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
BOT_TOKEN = "123456789:test_token_for_testing"
ADMIN_IDS = []
SUPER_ADMIN_IDS = []
MODERATOR_IDS = []
OPENWEATHER_API_KEY = "test_weather_key"
NEWS_API_KEY = "test_news_key"
OPENAI_API_KEY = "test_openai_key"
""")
        temp_config_path = f.name

    try:
        config = Config(temp_config_path)
        yield config
    finally:
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)


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


@pytest.fixture
def mock_callback_query(mock_user, mock_chat, mock_message):
    """Фикстура с мок-объектом callback query"""
    callback_query = Mock(spec=CallbackQuery)
    callback_query.id = "test_callback_123"
    callback_query.data = "test_data"
    callback_query.from_user = mock_user
    callback_query.message = mock_message
    callback_query.answer = AsyncMock()
    callback_query.edit_message_text = AsyncMock()
    return callback_query


@pytest.fixture
def sample_user_data():
    """Фикстура с тестовыми данными пользователя"""
    return {
        'id': 123456789,
        'telegram_id': 123456789,
        'username': 'test_user',
        'first_name': 'Test',
        'last_name': 'User',
        'reputation': 150,
        'rank': 'Активист',
        'message_count': 45,
        'joined_date': datetime.now(),
        'last_activity': datetime.now()
    }


@pytest.fixture
def sample_error_data():
    """Фикстура с тестовыми данными ошибки"""
    return {
        'id': 1,
        'admin_id': 123456789,
        'error_type': 'bug',
        'title': 'Тестовая ошибка',
        'description': 'Описание тестовой ошибки для тестирования',
        'status': 'new',
        'priority': 'medium',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }


@pytest.fixture
def temp_db_path():
    """Фикстура с временным путем к базе данных"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # Очистка после теста
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def event_loop():
    """Фикстура для event loop (для асинхронных тестов)"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Вспомогательные функции для тестов

def create_test_config(bot_token: str = "123456789:test_token", admin_ids: list = None) -> Config:
    """Создание тестовой конфигурации"""
    if admin_ids is None:
        admin_ids = []  # По умолчанию пустой список админов для тестов

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(f"""
BOT_TOKEN = "{bot_token}"
ADMIN_IDS = {admin_ids}
SUPER_ADMIN_IDS = []
MODERATOR_IDS = []
OPENWEATHER_API_KEY = "test_weather_key"
NEWS_API_KEY = "test_news_key"
OPENAI_API_KEY = "test_openai_key"
""")
        config_path = f.name

    try:
        return Config(config_path)
    finally:
        if os.path.exists(config_path):
            os.unlink(config_path)


def assert_exception_raised(func, exception_type, *args, **kwargs):
    """Утилита для проверки исключений в тестах"""
    with pytest.raises(exception_type):
        if asyncio.iscoroutinefunction(func):
            asyncio.run(func(*args, **kwargs))
        else:
            func(*args, **kwargs)


async def async_assert_exception_raised(func, exception_type, *args, **kwargs):
    """Асинхронная утилита для проверки исключений"""
    with pytest.raises(exception_type):
        await func(*args, **kwargs)


def create_mock_user(user_id: int = 123456789, username: str = "test_user",
                    first_name: str = "Test", last_name: str = "User"):
    """Создание мок-объекта пользователя"""
    user = Mock(spec=User)
    user.id = user_id
    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.is_bot = False
    return user


def create_mock_chat(chat_id: int = -1001234567890, chat_type: str = "group"):
    """Создание мок-объекта чата"""
    chat = Mock(spec=Chat)
    chat.id = chat_id
    chat.type = chat_type
    return chat


def create_mock_update(user: User = None, chat: Chat = None, text: str = "/test"):
    """Создание мок-объекта обновления"""
    if user is None:
        user = create_mock_user()
    if chat is None:
        chat = create_mock_chat()

    message = Mock(spec=Message)
    message.text = text
    message.from_user = user
    message.chat = chat

    update = Mock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message

    return update
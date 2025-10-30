#!/usr/bin/env python3
"""
Простое тестирование исправления кнопки 'Мини игры'
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock, AsyncMock
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

# Импортируем компоненты бота
from handlers.user_handlers import UserHandlers
from handlers.game_handlers import GameHandlers
from services.user_service import UserService
from database.repository import UserRepository, ScoreRepository

class ButtonFixTester:
    """Тестер исправления кнопки"""

    def __init__(self):
        """Инициализация тестера"""
        self.mock_config = MagicMock()
        self.mock_config.bot_config = MagicMock()
        self.mock_config.bot_config.admin_ids = [1278359005]

        # Создаем репозитории и сервисы
        self.user_repo = UserRepository("telegram_bot.db")
        self.score_repo = ScoreRepository("telegram_bot.db")
        self.user_service = UserService(self.user_repo, self.score_repo)
        self.user_handlers = UserHandlers(self.mock_config, self.user_service)
        self.game_handlers = GameHandlers(self.mock_config, None)

        print("Тестер исправления кнопки инициализирован")

    def create_mock_update(self, text=None, callback_data=None):
        """Создание мок-объекта"""
        user = MagicMock(spec=User)
        user.id = 123456789
        user.username = "test_user"
        user.first_name = "Test"
        user.last_name = "User"

        message = MagicMock(spec=Message)
        message.text = text
        message.message_id = 1

        chat = MagicMock(spec=Chat)
        chat.id = -1001234567890

        update = MagicMock(spec=Update)
        update.effective_user = user
        update.message = message if text else None
        update.effective_chat = chat

        if callback_data:
            callback_query = MagicMock()
            callback_query.data = callback_data
            callback_query.message = MagicMock()
            callback_query.answer = AsyncMock()
            callback_query.edit_message_text = AsyncMock()
            update.callback_query = callback_query

        return update

    def create_mock_context(self):
        """Создание мок-контекста"""
        context = MagicMock(spec=ContextTypes)
        context.args = []
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.edit_message_text = AsyncMock()
        context.user_data = {}
        return context

    async def test_games_button(self):
        """Тестирование кнопки 'Мини игры'"""
        print("НАЧАЛО ТЕСТИРОВАНИЯ КНОПКИ 'МИНИ ИГРЫ'")
        print("=" * 50)

        try:
            # Создаем мок-объекты для callback запроса
            update = self.create_mock_update(callback_data="menu_games")
            context = self.create_mock_context()

            # Тестируем обработчик кнопки "Мини игры"
            await self.game_handlers.handle_game_menu(update, context)

            # Проверяем результат
            if context.bot.edit_message_text.called:
                call_args = context.bot.edit_message_text.call_args
                message_text = call_args[1]['text']
                print("[SUCCESS] Кнопка 'Мини игры' обработана корректно!")
                print(f"Текст ответа: {message_text[:100]}...")
            else:
                print("[ERROR] Сообщение не было отправлено")

        except Exception as e:
            print(f"[ERROR] Ошибка при тестировании кнопки: {e}")
            import traceback
            traceback.print_exc()

    async def test_user_creation(self):
        """Тестирование создания пользователя"""
        print("\nНАЧАЛО ТЕСТИРОВАНИЯ СОЗДАНИЯ ПОЛЬЗОВАТЕЛЯ")
        print("=" * 50)

        try:
            # Тестируем создание пользователя
            user_profile = await self.user_service.get_or_create_user(
                123456789, "test_user", "Test", "User"
            )

            if user_profile:
                print("[SUCCESS] Пользователь создан успешно!")
                print(f"  ID: {user_profile.user_id}")
                print(f"  Имя: {user_profile.first_name}")
                print(f"  Репутация: {user_profile.reputation}")
            else:
                print("[ERROR] Не удалось создать пользователя")

        except Exception as e:
            print(f"[ERROR] Ошибка создания пользователя: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """Главная функция"""
    tester = ButtonFixTester()

    # Тестируем создание пользователя
    await tester.test_user_creation()

    # Тестируем кнопку "Мини игры"
    await tester.test_games_button()

    print("\n" + "="*50)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    asyncio.run(main())
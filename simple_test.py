#!/usr/bin/env python3
"""
Простое тестирование команд бота
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

class SimpleTester:
    """Простой тестер команд"""

    def __init__(self):
        """Инициализация"""
        self.mock_config = MagicMock()
        self.mock_config.api_keys = MagicMock()
        self.mock_config.api_keys.openweather = "test_key"
        self.mock_config.api_keys.news = "test_key"
        self.mock_config.bot_config = MagicMock()
        self.mock_config.bot_config.admin_ids = [1278359005]

        # Создаем репозитории и сервисы
        self.user_repo = UserRepository("telegram_bot.db")
        self.score_repo = ScoreRepository("telegram_bot.db")
        self.user_service = UserService(self.user_repo, self.score_repo)
        self.user_handlers = UserHandlers(self.mock_config, self.user_service)
        self.game_handlers = GameHandlers(self.mock_config, None)

        print("Тестер инициализирован")

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

    async def test_commands(self):
        """Тестирование команд"""
        print("\nНАЧАЛО ТЕСТИРОВАНИЯ КОМАНД")
        print("=" * 50)

        commands = [
            ("/start", "Запуск бота"),
            ("/help", "Помощь"),
            ("/rank", "Ранг"),
            ("/info", "Информация"),
            ("/donate", "Донаты"),
        ]

        for command, description in commands:
            try:
                print(f"\nТестирование: {description}")
                print(f"Команда: {command}")

                update = self.create_mock_update(text=command)
                context = self.create_mock_context()

                if command == "/start":
                    await self.user_handlers.handle_start(update, context)
                elif command == "/help":
                    await self.user_handlers.handle_help(update, context)
                elif command == "/rank":
                    await self.user_handlers.handle_rank(update, context)
                elif command == "/info":
                    await self.user_handlers.handle_info(update, context)
                elif command == "/donate":
                    await self.user_handlers.handle_donate(update, context)

                print(f"[SUCCESS] {command} выполнен успешно")

            except Exception as e:
                print(f"[ERROR] {command}: {e}")

    async def test_callbacks(self):
        """Тестирование callback кнопок"""
        print("\n\nНАЧАЛО ТЕСТИРОВАНИЯ CALLBACK КНОПОК")
        print("=" * 50)

        callbacks = [
            ("menu_main", "Главное меню"),
            ("menu_help", "Помощь"),
            ("donate_100", "Донат 100"),
        ]

        for callback_data, description in callbacks:
            try:
                print(f"\nТестирование: {description}")
                print(f"Callback: {callback_data}")

                update = self.create_mock_update(callback_data=callback_data)
                context = self.create_mock_context()

                if callback_data == "menu_main":
                    await self.user_handlers.handle_main_menu(update, context)
                elif callback_data == "menu_help":
                    await self.user_handlers.handle_help_menu(update, context)
                elif callback_data.startswith("donate_"):
                    await self.user_handlers.handle_donation_callback(update, context)

                print(f"[SUCCESS] {callback_data} выполнен успешно")

            except Exception as e:
                print(f"[ERROR] {callback_data}: {e}")

    async def test_database(self):
        """Тестирование базы данных"""
        print("\n\nНАЧАЛО ТЕСТИРОВАНИЯ БАЗЫ ДАННЫХ")
        print("=" * 50)

        try:
            # Тестируем создание пользователя
            user_profile = await self.user_service.get_or_create_user(
                999999999, "test_user", "Test", "User"
            )

            if user_profile:
                print(f"[SUCCESS] Пользователь создан: {user_profile.first_name}")
            else:
                print("[ERROR] Не удалось создать пользователя")

        except Exception as e:
            print(f"[ERROR] Ошибка базы данных: {e}")

async def main():
    """Главная функция"""
    tester = SimpleTester()

    # Тестируем базу данных
    await tester.test_database()

    # Тестируем команды
    await tester.test_commands()

    # Тестируем callback кнопки
    await tester.test_callbacks()

    print("\n" + "="*50)
    print("ВСЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Финальное тестирование команды /info после исправлений
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
from services.user_service import UserService
from database.repository import UserRepository, ScoreRepository

class FinalInfoTester:
    """Финальный тестер команды /info"""

    def __init__(self):
        """Инициализация тестера"""
        self.mock_config = MagicMock()
        self.mock_config.bot_config = MagicMock()
        self.mock_config.bot_config.admin_ids = [1278359005]

        # Создаем репозитории
        self.user_repo = UserRepository("telegram_bot.db")
        self.score_repo = ScoreRepository("telegram_bot.db")

        # Создаем сервисы
        self.user_service = UserService(self.user_repo, self.score_repo)

        # Создаем обработчики
        self.user_handlers = UserHandlers(self.mock_config, self.mock_config, self.user_service)

        print("Финальный тестер команды /info инициализирован")

    def create_mock_update(self, text=None, user_id=123456789, username="test_user",
                          first_name="Test", last_name="User"):
        """Создание мок-объекта Update"""

        # Создаем мок-пользователя
        user = MagicMock(spec=User)
        user.id = user_id
        user.username = username
        user.first_name = first_name
        user.last_name = last_name

        # Создаем мок-сообщение
        message = MagicMock(spec=Message)
        message.text = text
        message.message_id = 1

        # Создаем мок-чат
        chat = MagicMock(spec=Chat)
        chat.id = -1001234567890
        chat.type = "supergroup"

        # Создаем мок-update
        update = MagicMock(spec=Update)
        update.effective_user = user
        update.message = message
        update.effective_chat = chat

        return update

    def create_mock_context(self):
        """Создание мок-объекта ContextTypes"""
        context = MagicMock(spec=ContextTypes)
        context.args = []
        context.bot = MagicMock()
        context.user_data = {}

        # Настраиваем асинхронные методы
        context.bot.send_message = AsyncMock()

        return context

    async def test_info_command_final(self):
        """Финальное тестирование команды /info"""
        print("ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ КОМАНДЫ /info")
        print("=" * 50)

        try:
            # Создаем мок-объекты
            update = self.create_mock_update(text="/info")
            context = self.create_mock_context()

            # Тестируем команду /info
            await self.user_handlers.handle_info(update, context)

            # Проверяем результат
            if context.bot.send_message.called:
                call_args = context.bot.send_message.call_args
                message_text = call_args[1]['text']
                print(f"[SUCCESS] Команда /info выполнена успешно!")

                # Показываем первые 100 символов без эмодзи для избежания проблем кодировки
                safe_text = message_text.encode('utf-8', errors='replace').decode('utf-8')
                print(f"Текст ответа: {safe_text[:100]}...")
            else:
                print("[ERROR] Сообщение не было отправлено")

        except Exception as e:
            print(f"[ERROR] Ошибка при выполнении команды /info: {e}")
            import traceback
            traceback.print_exc()

    async def test_user_service_directly(self):
        """Прямое тестирование сервиса пользователей"""
        print("\nПРЯМОЕ ТЕСТИРОВАНИЕ СЕРВИСА ПОЛЬЗОВАТЕЛЕЙ")
        print("=" * 50)

        try:
            # Тестируем получение пользователя напрямую
            user_profile = await self.user_service.get_or_create_user(
                123456789, "test_user", "Test", "User"
            )

            if user_profile:
                print(f"[SUCCESS] Профиль пользователя создан успешно!")
                print(f"  ID: {user_profile.user_id}")
                print(f"  Имя: {user_profile.first_name}")
                print(f"  Репутация: {user_profile.reputation}")
                print(f"  Ранг: {user_profile.rank}")
            else:
                print("[ERROR] Профиль пользователя не создан (None)")

        except Exception as e:
            print(f"[ERROR] Ошибка в сервисе пользователей: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """Главная функция тестирования"""
    tester = FinalInfoTester()

    # Тестируем сервис пользователей напрямую
    await tester.test_user_service_directly()

    # Тестируем команду /info
    await tester.test_info_command_final()

    print(f"\n{'='*50}")
    print("ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    asyncio.run(main())
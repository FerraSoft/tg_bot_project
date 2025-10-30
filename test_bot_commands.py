#!/usr/bin/env python3
"""
Автоматическое тестирование команд телеграм-бота.
Проверяет основные команды на корректность работы.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock, AsyncMock
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

# Импортируем компоненты бота
from core.application import Application
from handlers.user_handlers import UserHandlers
from handlers.game_handlers import GameHandlers
from handlers.admin_handlers import AdminHandlers
from services.user_service import UserService
from services.game_service import GameService
from database.repository import UserRepository, ScoreRepository

class BotTester:
    """Класс для тестирования команд бота"""

    def __init__(self):
        """Инициализация тестера"""
        self.app = None
        self.user_handlers = None
        self.game_handlers = None
        self.admin_handlers = None

        # Создаем мок-объекты
        self.mock_config = MagicMock()
        self.mock_config.api_keys = MagicMock()
        self.mock_config.api_keys.openweather = "test_key"
        self.mock_config.api_keys.news = "test_key"
        self.mock_config.bot_config.admin_ids = [1278359005]

        # Настраиваем репозитории
        self.user_repo = UserRepository("telegram_bot.db")
        self.score_repo = ScoreRepository("telegram_bot.db")

        # Создаем сервисы
        self.user_service = UserService(self.user_repo, self.score_repo)
        self.game_service = GameService(self.user_repo, self.score_repo)

        # Создаем обработчики
        self.user_handlers = UserHandlers(self.mock_config, self.user_service)
        self.game_handlers = GameHandlers(self.mock_config, self.game_service)

        print("Тестер бота инициализирован")

    def create_mock_update(self, text=None, user_id=123456789, username="test_user",
                          first_name="Тест", last_name="Пользователь"):
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

    async def test_command(self, command, description):
        """Тестирование одной команды"""
        print(f"\n{'='*50}")
        print(f"ТЕСТИРОВАНИЕ: {description}")
        print(f"Команда: {command}")
        print(f"{'='*50}")

        try:
            # Создаем мок-объекты
            update = self.create_mock_update(text=command)
            context = self.create_mock_context()

            # Определяем, какой обработчик использовать
            if command in ['/start', '/help', '/rank', '/leaderboard', '/info', '/donate']:
                handler = self.user_handlers
                if hasattr(handler, f'handle_{command[1:]}'):
                    method = getattr(handler, f'handle_{command[1:]}')
                    await method(update, context)
                    print(f"[SUCCESS] Команда {command} выполнена успешно")
                else:
                    print(f"[ERROR] Обработчик для команды {command} не найден")

            elif command in ['/play_game', '/rock_paper_scissors', '/battleship']:
                handler = self.game_handlers
                if hasattr(handler, f'handle_{command[1:]}'):
                    method = getattr(handler, f'handle_{command[1:]}')
                    await method(update, context)
                    print(f"[SUCCESS] Игровая команда {command} выполнена успешно")
                else:
                    print(f"[ERROR] Игровой обработчик для команды {command} не найден")

            else:
                print(f"[ERROR] Неизвестная команда: {command}")

        except Exception as e:
            print(f"[ERROR] Ошибка при выполнении команды {command}: {e}")
            import traceback
            traceback.print_exc()

    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("НАЧАЛО АВТОМАТИЧЕСКОГО ТЕСТИРОВАНИЯ КОМАНД БОТА")
        print("=" * 60)

        # Список команд для тестирования
        commands_to_test = [
            ("/start", "Запуск бота и приветственное сообщение"),
            ("/help", "Справка по командам"),
            ("/rank", "Информация о ранге пользователя"),
            ("/leaderboard", "Таблица лидеров"),
            ("/info", "Информация о пользователе"),
            ("/donate", "Команда донатов"),
            ("/play_game", "Меню выбора игр"),
            ("/rock_paper_scissors", "Игра камень-ножницы-бумага"),
            ("/battleship", "Игра морской бой"),
        ]

        # Тестируем каждую команду
        for command, description in commands_to_test:
            await self.test_command(command, description)
            await asyncio.sleep(0.1)  # Небольшая пауза между тестами

        print(f"\n{'='*60}")
        print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print(f"Протестировано команд: {len(commands_to_test)}")
        print("=" * 60)

    def check_database_integrity(self):
        """Проверка целостности базы данных"""
        print(f"\n{'='*50}")
        print("ПРОВЕРКА ЦЕЛОСТНОСТИ БАЗЫ ДАННЫХ")
        print(f"{'='*50}")

        try:
            # Проверяем таблицы
            tables = ['users', 'scores', 'achievements', 'user_achievements',
                     'warnings', 'donations', 'errors', 'scheduled_posts', 'games']

            for table in tables:
                # Проверяем, существует ли таблица
                cursor = self.user_repo._get_connection().cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                result = cursor.fetchone()

                if result:
                    print(f"[OK] Таблица {table}: существует")

                    # Проверяем количество записей
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()['count']
                    print(f"   Записей: {count}")
                else:
                    print(f"[ERROR] Таблица {table}: отсутствует")

        except Exception as e:
            print(f"[ERROR] Ошибка при проверке базы данных: {e}")

async def main():
    """Главная функция тестирования"""
    tester = BotTester()

    # Проверяем базу данных
    tester.check_database_integrity()

    # Запускаем тестирование команд
    await tester.run_all_tests()

if __name__ == "__main__":
    # Запускаем асинхронное тестирование
    asyncio.run(main())
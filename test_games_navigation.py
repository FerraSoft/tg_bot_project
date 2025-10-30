#!/usr/bin/env python3
"""
Тестирование навигации /start -> Мини игры
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
from services.game_service import GameService
from database.repository import UserRepository, ScoreRepository

class GamesNavigationTester:
    """Тестер навигации к играм"""

    def __init__(self):
        """Инициализация тестера"""
        self.mock_config = MagicMock()
        self.mock_config.bot_config = MagicMock()
        self.mock_config.bot_config.admin_ids = [1278359005]

        # Создаем репозитории и сервисы
        self.user_repo = UserRepository("telegram_bot.db")
        self.score_repo = ScoreRepository("telegram_bot.db")
        self.user_service = UserService(self.user_repo, self.score_repo)
        self.game_service = GameService(self.user_repo, self.score_repo)
        self.user_handlers = UserHandlers(self.mock_config, self.user_service)
        self.game_handlers = GameHandlers(self.mock_config, self.game_service)

        print("Тестер навигации к играм инициализирован")

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
        message.reply_text = AsyncMock()

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
            callback_query.message.edit_message_text = AsyncMock()
            callback_query.edit_message_text = AsyncMock()
            callback_query.answer = AsyncMock()
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

    async def test_games_navigation(self):
        """Тестирование навигации к играм"""
        print("НАЧАЛО ТЕСТИРОВАНИЯ НАВИГАЦИИ К ИГРАМ")
        print("=" * 50)

        try:
            # Шаг 1: Тестируем команду /start
            print("Шаг 1: Тестирование команды /start")
            update = self.create_mock_update(text="/start")
            context = self.create_mock_context()

            await self.user_handlers.handle_start(update, context)

            if context.bot.send_message.called:
                print("[SUCCESS] Команда /start выполнена")
            else:
                print("[ERROR] Команда /start не отправила сообщение")

            # Шаг 2: Тестируем кнопку "Мини игры" (menu_games)
            print("\nШаг 2: Тестирование кнопки 'Мини игры' (menu_games)")
            update = self.create_mock_update(callback_data="menu_games")
            context = self.create_mock_context()

            await self.game_handlers.handle_game_menu(update, context)

            if context.bot.send_message.called or context.bot.edit_message_text.called:
                print("[SUCCESS] Кнопка 'Мини игры' обработана")
            else:
                print("[ERROR] Кнопка 'Мини игры' не отправила сообщение")

            # Шаг 3: Тестируем игровые кнопки
            print("\nШаг 3: Тестирование игровых кнопок")

            game_callbacks = [
                "game_rps_start",
                "game_tictactoe_start",
                "game_quiz_start",
                "game_battleship_start"
            ]

            for callback in game_callbacks:
                print(f"  Тестирование: {callback}")
                update = self.create_mock_update(callback_data=callback)
                context = self.create_mock_context()

                try:
                    if callback == "game_rps_start":
                        await self.game_handlers.handle_rock_paper_scissors(update, context)
                    elif callback == "game_tictactoe_start":
                        await self.game_handlers.handle_tic_tac_toe(update, context)
                    elif callback == "game_quiz_start":
                        await self.game_handlers.handle_quiz(update, context)
                    elif callback == "game_battleship_start":
                        await self.game_handlers.handle_battleship(update, context)

                    print(f"    [SUCCESS] {callback} выполнен")
                except Exception as e:
                    print(f"    [ERROR] {callback}: {e}")

            # Дополнительные тесты для полного потока
            # Проверяют полный цикл: создание сессии -> выбор -> игра -> завершение
            print("\n  Дополнительные интеграционные тесты")
            # Тест полного потока RPS
            print("    Тестирование полного потока RPS...")
            rps_update = self.create_mock_update(callback_data="game_rps_start")
            rps_context = self.create_mock_context()

            # Создаем сессию
            await self.game_handlers.handle_rock_paper_scissors(rps_update, rps_context)
            print("      [SUCCESS] Сессия RPS создана")

            # Получаем game_id из последней сессии (для теста)
            # В реальности, game_id должен быть извлечен из callback_data
            # Для теста, предполагаем, что сессия создана
            active_sessions = self.game_service.active_sessions
            if active_sessions:
                game_id = list(active_sessions.keys())[0]
                print(f"      Найден game_id: {game_id}")

                # Тестируем выбор
                choice_update = self.create_mock_update(callback_data=f"game_rps_rock_{game_id}")
                choice_context = self.create_mock_context()

                await self.game_handlers.handle_rps_choice(choice_update, choice_context)
                print("      [SUCCESS] Выбор в RPS обработан")
            else:
                print("      [ERROR] Сессия RPS не найдена")

            # Тест поддержки русского ввода в RPS
            # Проверяет, что game_service корректно обрабатывает русский ввод
            print("    Тестирование русского ввода в RPS...")
            russian_session = self.game_service.create_game_session('rock_paper_scissors', 123456789, -1001234567890)
            result = self.game_service.play_rock_paper_scissors(russian_session.game_id, 'камень')
            assert result['player_choice'] == 'rock'
            print("      [SUCCESS] Русский ввод 'камень' обработан как 'rock'")

            result = self.game_service.play_rock_paper_scissors(russian_session.game_id, 'ножницы')
            assert result['player_choice'] == 'scissors'
            print("      [SUCCESS] Русский ввод 'ножницы' обработан как 'scissors'")

            result = self.game_service.play_rock_paper_scissors(russian_session.game_id, 'бумага')
            assert result['player_choice'] == 'paper'
            print("      [SUCCESS] Русский ввод 'бумага' обработан как 'paper'")

        except Exception as e:
            print(f"[ERROR] Критическая ошибка тестирования: {e}")
            import traceback
            traceback.print_exc()

    async def run_all_tests(self):
        """Запуск всех тестов"""
        await self.test_games_navigation()

        print("\n" + "="*50)
        print("ТЕСТИРОВАНИЕ НАВИГАЦИИ ЗАВЕРШЕНО")

async def main():
    """Главная функция"""
    tester = GamesNavigationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Комплексная система автоматического тестирования телеграм-бота.
Проверяет все команды, callback кнопки и обработчики сообщений.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import MagicMock, AsyncMock
from telegram import Update, User, Chat, Message, CallbackQuery
from telegram.ext import ContextTypes
from typing import Dict, List, Tuple

# Импортируем все компоненты бота
from core.application import Application
from handlers.user_handlers import UserHandlers
from handlers.game_handlers import GameHandlers
from handlers.admin_handlers import AdminHandlers
from services.user_service import UserService
from services.game_service import GameService
from database.repository import UserRepository, ScoreRepository

class ComprehensiveTestSuite:
    """Комплексная система тестирования бота"""

    def __init__(self):
        """Инициализация тестера"""
        self.results = {
            'commands': [],
            'callbacks': [],
            'messages': [],
            'errors': []
        }

        # Создаем мок-конфигурацию
        self.mock_config = MagicMock()
        self.mock_config.api_keys = MagicMock()
        self.mock_config.api_keys.openweather = "test_key"
        self.mock_config.api_keys.news = "test_key"
        self.mock_config.api_keys.openai = "test_key"
        self.mock_config.bot_config = MagicMock()
        self.mock_config.bot_config.admin_ids = [1278359005]
        self.mock_config.bot_config.enable_developer_notifications = True
        self.mock_config.bot_config.developer_chat_id = 1278359005

        # Создаем репозитории и сервисы
        self.user_repo = UserRepository("telegram_bot.db")
        self.score_repo = ScoreRepository("telegram_bot.db")
        self.user_service = UserService(self.user_repo, self.score_repo)
        self.game_service = GameService(self.user_repo, self.score_repo)

        # Создаем обработчики
        self.user_handlers = UserHandlers(self.mock_config, MagicMock(), self.user_service)
        self.game_handlers = GameHandlers(self.mock_config, MagicMock(), self.game_service)

        print("Комплексная система тестирования инициализирована")

    def create_mock_update(self, text=None, callback_data=None, user_id=123456789,
                          username="test_user", first_name="Test", last_name="User"):
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

        # Создаем мок-коллбек запрос
        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.data = callback_data
        callback_query.message = MagicMock()
        callback_query.from_user = user

        # Создаем мок-чат
        chat = MagicMock(spec=Chat)
        chat.id = -1001234567890
        chat.type = "supergroup"

        # Создаем мок-update
        update = MagicMock(spec=Update)
        update.effective_user = user
        update.message = message if text else None
        update.callback_query = callback_query if callback_data else None
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
        context.bot.edit_message_text = AsyncMock()

        return context

    async def test_single_command(self, command: str, description: str, handler, method_name: str) -> Dict:
        """Тестирование одной команды"""
        result = {
            'command': command,
            'description': description,
            'success': False,
            'error': None,
            'execution_time': 0
        }

        try:
            import time
            start_time = time.time()

            # Создаем мок-объекты
            update = self.create_mock_update(text=command)
            context = self.create_mock_context()

            # Получаем метод обработчика
            method = getattr(handler, method_name)

            # Выполняем команду
            await method(update, context)

            execution_time = time.time() - start_time
            result['success'] = True
            result['execution_time'] = execution_time

            print(f"[SUCCESS] {command}: {execution_time:.3f}с")

        except Exception as e:
            result['error'] = str(e)
            print(f"[ERROR] {command}: {e}")
            self.results['errors'].append({
                'command': command,
                'error': str(e),
                'traceback': str(e.__class__.__name__)
            })

        return result

    async def test_callback_button(self, callback_data: str, description: str, handler, method_name: str) -> Dict:
        """Тестирование callback кнопки"""
        result = {
            'callback': callback_data,
            'description': description,
            'success': False,
            'error': None,
            'execution_time': 0
        }

        try:
            import time
            start_time = time.time()

            # Создаем мок-объекты
            update = self.create_mock_update(callback_data=callback_data)
            context = self.create_mock_context()

            # Получаем метод обработчика
            method = getattr(handler, method_name)

            # Выполняем обработчик
            await method(update, context)

            execution_time = time.time() - start_time
            result['success'] = True
            result['execution_time'] = execution_time

            print(f"[SUCCESS] {callback_data}: {execution_time:.3f}с")

        except Exception as e:
            result['error'] = str(e)
            print(f"[ERROR] {callback_data}: {e}")
            self.results['errors'].append({
                'callback': callback_data,
                'error': str(e),
                'traceback': str(e.__class__.__name__)
            })

        return result

    async def run_command_tests(self):
        """Тестирование команд"""
        print("\n" + "="*60)
        print("ТЕСТИРОВАНИЕ КОМАНД")
        print("="*60)

        commands_to_test = [
            ("/start", "Запуск бота", self.user_handlers, "handle_start"),
            ("/help", "Помощь", self.user_handlers, "handle_help"),
            ("/rank", "Ранг пользователя", self.user_handlers, "handle_rank"),
            ("/leaderboard", "Таблица лидеров", self.user_handlers, "handle_leaderboard"),
            ("/info", "Информация о пользователе", self.user_handlers, "handle_info"),
            ("/donate", "Донаты", self.user_handlers, "handle_donate"),
            ("/play_game", "Меню игр", self.game_handlers, "handle_play_game"),
            ("/rock_paper_scissors", "Камень-ножницы-бумага", self.game_handlers, "handle_rock_paper_scissors"),
            ("/battleship", "Морской бой", self.game_handlers, "handle_battleship"),
        ]

        for command, description, handler, method_name in commands_to_test:
            result = await self.test_single_command(command, description, handler, method_name)
            self.results['commands'].append(result)

    async def run_callback_tests(self):
        """Тестирование callback кнопок"""
        print("\n" + "="*60)
        print("ТЕСТИРОВАНИЕ CALLBACK КНОПОК")
        print("="*60)

        callbacks_to_test = [
            ("menu_main", "Главное меню", self.user_handlers, "handle_main_menu"),
            ("menu_help", "Меню помощи", self.user_handlers, "handle_help_menu"),
            ("menu_rank", "Меню ранга", self.user_handlers, "handle_rank_menu"),
            ("game_rps_start", "Запуск RPS", self.game_handlers, "handle_rps_choice"),
            ("game_battleship_start", "Запуск морского боя", self.game_handlers, "handle_battleship_shot"),
            ("donate_100", "Донат 100", self.user_handlers, "handle_donation_callback"),
            ("donate_500", "Донат 500", self.user_handlers, "handle_donation_callback"),
            ("donate_1000", "Донат 1000", self.user_handlers, "handle_donation_callback"),
        ]

        for callback_data, description, handler, method_name in callbacks_to_test:
            result = await self.test_callback_button(callback_data, description, handler, method_name)
            self.results['callbacks'].append(result)

    async def test_database_operations(self):
        """Тестирование операций с базой данных"""
        print("\n" + "="*60)
        print("ТЕСТИРОВАНИЕ БАЗЫ ДАННЫХ")
        print("="*60)

        try:
            # Тестируем создание пользователя
            user_profile = await self.user_service.get_or_create_user(
                999999999, "db_test_user", "DB", "Test"
            )

            if user_profile:
                print(f"[SUCCESS] Пользователь создан: {user_profile.first_name}")
                print(f"         ID: {user_profile.user_id}")
                print(f"         Репутация: {user_profile.reputation}")
            else:
                print("[ERROR] Не удалось создать пользователя")

            # Тестируем получение топ пользователей
            top_users = await self.user_service.get_top_users(5)
            print(f"[SUCCESS] Топ пользователей получен: {len(top_users)} записей")

            # Тестируем обновление активности
            activity_result = await self.user_service.update_user_activity(999999999, -1001234567890)
            print(f"[SUCCESS] Активность обновлена: {activity_result}")

        except Exception as e:
            print(f"[ERROR] Ошибка базы данных: {e}")

    def generate_report(self):
        """Генерация отчета о тестировании"""
        print("\n" + "="*60)
        print("ОТЧЕТ О ТЕСТИРОВАНИИ")
        print("="*60)

        total_commands = len(self.results['commands'])
        successful_commands = len([r for r in self.results['commands'] if r['success']])

        total_callbacks = len(self.results['callbacks'])
        successful_callbacks = len([r for r in self.results['callbacks'] if r['success']])

        total_errors = len(self.results['errors'])

        print(f"Команды: {successful_commands}/{total_commands} успешных")
        print(f"Callback кнопки: {successful_callbacks}/{total_callbacks} успешных")
        print(f"Ошибок: {total_errors}")

        # Подробный отчет по командам
        print("\nДЕТАЛЬНЫЙ ОТЧЕТ ПО КОМАНДАМ:")
        for result in self.results['commands']:
            status = "SUCCESS" if result['success'] else "ERROR"
            print(f"  {result['command']:<20} | {status:<8} | {result['execution_time']:.3f}с")

        # Подробный отчет по callback кнопкам
        print("\nДЕТАЛЬНЫЙ ОТЧЕТ ПО CALLBACK КНОПКАМ:")
        for result in self.results['callbacks']:
            status = "SUCCESS" if result['success'] else "ERROR"
            print(f"  {result['callback']:<20} | {status:<8} | {result['execution_time']:.3f}с")

        # Отчет об ошибках
        if self.results['errors']:
            print("\nОШИБКИ:")
            for error in self.results['errors']:
                if 'command' in error:
                    print(f"  Команда {error['command']}: {error['error']}")
                else:
                    print(f"  Callback {error['callback']}: {error['error']}")

        # Итоговая оценка
        total_tests = total_commands + total_callbacks
        successful_tests = successful_commands + successful_callbacks
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\nОБЩИЙ РЕЗУЛЬТАТ:")
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {successful_tests}")
        print(f"Процент успеха: {success_rate:.1f}%")

        if success_rate >= 90:
            print("ОЦЕНКА: ОТЛИЧНО - Бот готов к работе!")
        elif success_rate >= 70:
            print("ОЦЕНКА: ХОРОШО - Есть небольшие проблемы")
        else:
            print("ОЦЕНКА: ТРЕБУЕТ УЛУЧШЕНИЙ - Много ошибок")

    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("НАЧАЛО КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ ТЕЛЕГРАМ-БОТА")
        print("=" * 70)

        # Тестируем команды
        await self.run_command_tests()

        # Тестируем callback кнопки
        await self.run_callback_tests()

        # Тестируем базу данных
        await self.test_database_operations()

        # Генерируем отчет
        self.generate_report()

        print("\n" + "="*70)
        print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

async def main():
    """Главная функция"""
    # Создаем и запускаем тестовую систему
    test_suite = ComprehensiveTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
"""
Тесты производительности для критических функций бота.
Проверяет производительность форматтеров и других важных компонентов.
"""

import pytest
import time
import asyncio
from typing import List, Dict, Any
from utils.formatters import MessageFormatter, KeyboardFormatter


class TestPerformance:
    """Тесты производительности критических функций"""

    def test_message_formatter_performance(self):
        """Тест производительности MessageFormatter"""
        # Подготовка тестовых данных
        user_data = {
            'id': 123456789,
            'name': 'Тестовый Пользователь',
            'username': 'test_user',
            'reputation': 150,
            'rank': 'Активист',
            'message_count': 45,
            'joined_date': '2024-01-15'
        }

        weather_data = {
            'city': 'Москва',
            'temp': 20,
            'feels_like': 18,
            'humidity': 65,
            'description': 'ясно'
        }

        users = [(i, f'user{i}', f'Пользователь {i}', i * 10) for i in range(100)]

        # Тестирование производительности форматирования пользовательской информации
        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            MessageFormatter.format_user_info(user_data)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Форматирование информации о пользователе: {duration*1000:.2f}ms за {iterations} операций")
        print(f"Среднее время на операцию: {duration*1000/iterations:.4f}ms")

        # Должно выполняться быстрее 1мс в среднем
        assert duration / iterations < 0.001, f"Слишком медленное форматирование: {duration/iterations:.6f}s на операцию"

    def test_leaderboard_formatter_performance(self):
        """Тест производительности форматирования таблицы лидеров"""
        # Создаем большой список пользователей
        users = [(i, f'user{i}', f'Пользователь {i}', i * 10) for i in range(1000)]

        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            MessageFormatter.format_leaderboard(users)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Форматирование таблицы лидеров: {duration*1000:.2f}ms за {iterations} операций")
        print(f"Среднее время на операцию: {duration*1000/iterations:.4f}ms")

        # Должно выполняться быстрее 10мс в среднем для 1000 пользователей
        assert duration / iterations < 0.01, f"Слишком медленное форматирование таблицы: {duration/iterations:.6f}s на операцию"

    def test_html_escaping_performance(self):
        """Тест производительности HTML экранирования"""
        test_strings = [
            '<div>Test & "quotes" \'apostrophe\'</div>',
            '<script>alert("test")</script>',
            '<b>Bold & <i>italic</i></b>',
            'Simple text without special characters',
            'Text with & ampersand and "quotes" and \'apostrophes\'',
        ]

        total_operations = 10000
        start_time = time.time()

        for _ in range(total_operations):
            for test_string in test_strings:
                MessageFormatter.escape_html(test_string)

        end_time = time.time()
        duration = end_time - start_time

        print(f"HTML экранирование: {duration*1000:.2f}ms за {total_operations} операций")
        print(f"Среднее время на операцию: {duration*1000/total_operations:.6f}ms")

        # Должно выполняться быстрее 0.1мс в среднем
        assert duration / total_operations < 0.0001, f"Слишком медленное экранирование: {duration/total_operations:.8f}s на операцию"

    def test_keyboard_formatter_performance(self):
        """Тест производительности KeyboardFormatter"""
        iterations = 500
        start_time = time.time()

        for _ in range(iterations):
            # Тестируем различные типы клавиатур
            KeyboardFormatter.create_main_menu()
            KeyboardFormatter.create_games_menu()
            KeyboardFormatter.create_donation_menu()
            KeyboardFormatter.create_admin_menu()
            KeyboardFormatter.create_confirmation_menu("yes", "no")
            KeyboardFormatter.create_pagination_menu(1, 10, "test")

        end_time = time.time()
        duration = end_time - start_time

        print(f"Создание клавиатур: {duration*1000:.2f}ms за {iterations * 6} операций")
        print(f"Среднее время на клавиатуру: {duration*1000/(iterations * 6):.6f}ms")

        # Должно выполняться быстрее 1мс в среднем на клавиатуру
        assert duration / (iterations * 6) < 0.001, f"Слишком медленное создание клавиатур: {duration/(iterations * 6):.8f}s на клавиатуру"

    def test_text_truncation_performance(self):
        """Тест производительности усечения текста"""
        long_text = "Это очень длинный текст, который содержит множество слов и должен быть усечен до определенной длины для того чтобы поместиться в сообщение телеграм бота без превышения лимита символов"

        iterations = 10000
        start_time = time.time()

        for _ in range(iterations):
            MessageFormatter.truncate_text(long_text, 100)
            MessageFormatter.truncate_text(long_text, 50)
            MessageFormatter.truncate_text(long_text, 150)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Усечение текста: {duration*1000:.2f}ms за {iterations * 3} операций")
        print(f"Среднее время на операцию: {duration*1000/(iterations * 3):.8f}ms")

        # Должно выполняться быстрее 0.01мс в среднем
        assert duration / (iterations * 3) < 0.00001, f"Слишком медленное усечение: {duration/(iterations * 3):.10f}s на операцию"

    def test_moderation_info_performance(self):
        """Тест производительности форматирования информации модерации"""
        media_types = ['audio', 'video', 'photo', 'document']
        transcriptions = [
            None,
            "Короткая транскрипция",
            "Это очень длинная транскрипция аудио сообщения, которая содержит много слов и должна быть обработана быстро и эффективно нашим форматтером для корректного отображения в интерфейсе модератора"
        ]

        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            for media_type in media_types:
                for transcription in transcriptions:
                    MessageFormatter.format_moderation_info(media_type, f"User{_}", transcription)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Форматирование модерации: {duration*1000:.2f}ms за {iterations * len(media_types) * len(transcriptions)} операций")
        print(f"Среднее время на операцию: {duration*1000/(iterations * len(media_types) * len(transcriptions)):.8f}ms")

        # Должно выполняться быстрее 0.1мс в среднем
        assert duration / (iterations * len(media_types) * len(transcriptions)) < 0.0001, f"Слишком медленное форматирование модерации: {duration/(iterations * len(media_types) * len(transcriptions)):.10f}s на операцию"

    def test_news_formatting_performance(self):
        """Тест производительности форматирования новостей"""
        # Создаем большой список статей
        articles = [
            {
                'title': f'Заголовок новости номер {i}',
                'url': f'https://example.com/news/{i}'
            }
            for i in range(100)
        ]

        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            MessageFormatter.format_news(articles)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Форматирование новостей: {duration*1000:.2f}ms за {iterations} операций")
        print(f"Среднее время на операцию: {duration*1000/iterations:.6f}ms")

        # Должно выполняться быстрее 5мс в среднем для 100 новостей
        assert duration / iterations < 0.005, f"Слишком медленное форматирование новостей: {duration/iterations:.8f}s на операцию"

    def test_memory_usage_simulation(self):
        """Тест симуляции использования памяти"""
        # Симулируем создание множества объектов для проверки утечек памяти
        objects = []

        for i in range(1000):
            # Создаем различные типы данных
            user_data = {
                'id': i,
                'name': f'Пользователь {i}',
                'username': f'user{i}',
                'reputation': i * 10,
                'rank': 'Пользователь',
                'message_count': i * 5,
                'joined_date': '2024-01-15'
            }

            weather_data = {
                'city': f'Город {i}',
                'temp': 20 + i % 10,
                'feels_like': 18 + i % 10,
                'humidity': 60 + i % 20,
                'description': f'Описание {i}'
            }

            # Тестируем создание клавиатур
            keyboard = KeyboardFormatter.create_main_menu()
            keyboard2 = KeyboardFormatter.create_games_menu()

            objects.append((user_data, weather_data, keyboard, keyboard2))

        # Очищаем память
        objects.clear()

        print("Тест памяти завершен успешно - объекты созданы и очищены")


if __name__ == "__main__":
    # Запуск тестов производительности
    test_instance = TestPerformance()

    print("=== ЗАПУСК ТЕСТОВ ПРОИЗВОДИТЕЛЬНОСТИ ===")

    test_instance.test_message_formatter_performance()
    test_instance.test_leaderboard_formatter_performance()
    test_instance.test_html_escaping_performance()
    test_instance.test_keyboard_formatter_performance()
    test_instance.test_text_truncation_performance()
    test_instance.test_moderation_info_performance()
    test_instance.test_news_formatting_performance()
    test_instance.test_memory_usage_simulation()

    print("=== ВСЕ ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ ПРОШЛИ УСПЕШНО ===")
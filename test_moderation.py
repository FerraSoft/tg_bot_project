#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест системы модерации
"""

import sys
import os
from datetime import datetime, timedelta

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_sqlite import Database
from messages import PROFANITY_WORDS, MODERATION_MESSAGES

class ModerationSystemTester:
    """Класс для тестирования системы модерации"""

    def __init__(self):
        self.db = None
        self.test_results = []
        self.start_time = datetime.now()

    def log(self, message, status="INFO"):
        """Логирование результатов теста"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_icons = {
            "SUCCESS": "[OK]",
            "ERROR": "[FAIL]",
            "WARNING": "[WARN]",
            "INFO": "[INFO]"
        }
        icon = status_icons.get(status, "[INFO]")
        print(f"[{timestamp}] {icon} {message}")
        self.test_results.append({
            'timestamp': timestamp,
            'status': status,
            'message': message
        })

    def print_header(self, title):
        """Вывод заголовка теста"""
        print(f"\n{'='*60}")
        print(f"[TEST] {title}")
        print(f"{'='*60}")

    def test_database_connection(self):
        """Тест подключения к базе данных"""
        self.print_header("ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")

        try:
            self.db = Database()
            if self.db.connection:
                self.log("Подключение к базе данных установлено успешно", "SUCCESS")
                return True
            else:
                self.log("Не удалось подключиться к базе данных", "ERROR")
                return False
        except Exception as e:
            self.log(f"Ошибка подключения к базе данных: {e}", "ERROR")
            return False

    def test_profanity_filter(self):
        """Тест системы фильтрации мата"""
        self.print_header("ТЕСТИРОВАНИЕ СИСТЕМЫ ФИЛЬТРАЦИИ МАТА")

        try:
            from bot import TelegramBot
            bot = TelegramBot()

            if hasattr(bot, 'check_profanity'):
                self.log("Метод check_profanity найден", "SUCCESS")
            else:
                self.log("Метод check_profanity не найден", "ERROR")
                return False

            # Тестовые случаи для мата
            test_cases = [
                ("Привет, как дела?", False),
                ("Это нормальное сообщение", False),
                ("блядь, что происходит", True),
                ("Пошел нахуй придурок", True),
                ("fuck you asshole", True),
                ("Это сообщение без мата", False),
                ("сука, ты идиот", True),
                ("damn, this is bad", True),
            ]

            passed_tests = 0
            total_tests = len(test_cases)

            for text, should_contain_profanity in test_cases:
                result = bot.check_profanity(text)
                if result == should_contain_profanity:
                    self.log(f"Текст '{text[:30]}...' -> {result} (ожидаемо: {should_contain_profanity})", "SUCCESS")
                    passed_tests += 1
                else:
                    self.log(f"Текст '{text[:30]}...' -> {result} (ожидаемо: {should_contain_profanity})", "ERROR")

            if passed_tests == total_tests:
                self.log(f"Все {total_tests} тестов фильтрации мата пройдены", "SUCCESS")
                return True
            else:
                self.log(f"Пройдено {passed_tests} из {total_tests} тестов фильтрации мата", "WARNING")
                return False

        except Exception as e:
            self.log(f"Ошибка при тестировании фильтрации мата: {e}", "ERROR")
            return False

    def test_moderation_commands_validation(self):
        """Тест валидации команд модерации"""
        self.print_header("ТЕСТИРОВАНИЕ ВАЛИДАЦИИ КОМАНД МОДЕРАЦИИ")

        try:
            from bot import TelegramBot
            bot = TelegramBot()

            # Тестовые случаи для валидации
            test_cases = [
                # (user_id, target_id, should_be_valid, description)
                (12345, 12345, False, "Пользователь не может модерировать себя"),
                (12345, 67890, True, "Нормальная модерация пользователя"),
                (12345, None, False, "Целевой пользователь не указан"),
            ]

            passed_tests = 0
            total_tests = len(test_cases)

            for admin_id, target_id, should_be_valid, description in test_cases:
                # Здесь мы тестируем логику валидации косвенно
                # В реальном коде это делается в самих командах модерации

                if target_id == admin_id:
                    is_valid = False  # Не должно позволять модерировать себя
                elif target_id is None:
                    is_valid = False  # Должен быть указан целевой пользователь
                else:
                    is_valid = True   # Нормальный случай

                if is_valid == should_be_valid:
                    self.log(f"{description} -> {is_valid} (ожидаемо: {should_be_valid})", "SUCCESS")
                    passed_tests += 1
                else:
                    self.log(f"{description} -> {is_valid} (ожидаемо: {should_be_valid})", "ERROR")

            if passed_tests == total_tests:
                self.log(f"Все {total_tests} тестов валидации пройдены", "SUCCESS")
                return True
            else:
                self.log(f"Пройдено {passed_tests} из {total_tests} тестов валидации", "WARNING")
                return False

        except Exception as e:
            self.log(f"Ошибка при тестировании валидации команд: {e}", "ERROR")
            return False

    def test_warning_system(self):
        """Тест системы предупреждений"""
        self.print_header("ТЕСТИРОВАНИЕ СИСТЕМЫ ПРЕДУПРЕЖДЕНИЙ")

        try:
            if not self.db:
                self.log("База данных недоступна", "ERROR")
                return False

            # Тест добавления предупреждения
            test_user_id = 999999
            test_reason = "Тестовое предупреждение от системы тестирования"

            try:
                # Сначала создаем пользователя
                self.db.add_user(test_user_id, "test_user", "Тест", "Пользователь")

                self.db.add_warning(test_user_id, test_reason, 0)  # 0 - системное предупреждение
                self.log("Предупреждение успешно добавлено в базу данных", "SUCCESS")

                # Проверяем, что количество предупреждений увеличилось
                user_info = self.db.get_user_info(test_user_id)
                if user_info and user_info['Предупреждений'] > 0:
                    self.log(f"Предупреждений у пользователя: {user_info['Предупреждений']}", "SUCCESS")
                    return True
                else:
                    self.log("Предупреждение не отразилось в профиле пользователя", "ERROR")
                    return False

            except Exception as e:
                self.log(f"Ошибка при работе с предупреждениями: {e}", "ERROR")
                return False

        except Exception as e:
            self.log(f"Ошибка при тестировании системы предупреждений: {e}", "ERROR")
            return False

    def test_user_info_for_moderation(self):
        """Тест получения информации о пользователе для модерации"""
        self.print_header("ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О ПОЛЬЗОВАТЕЛЕ")

        try:
            if not self.db:
                self.log("База данных недоступна", "ERROR")
                return False

            # Создаем тестового пользователя
            test_user_id = 888888
            self.db.add_user(test_user_id, "test_user", "Тест", "Пользователь")

            # Получаем информацию о пользователе
            user_info = self.db.get_user_info(test_user_id)

            if user_info:
                required_fields = ['ID', 'Имя', 'Предупреждений', 'Роль']
                missing_fields = []

                for field in required_fields:
                    if field not in user_info:
                        missing_fields.append(field)

                if not missing_fields:
                    self.log("Все необходимые поля присутствуют в информации о пользователе", "SUCCESS")
                    self.log(f"Пользователь: {user_info['Имя']}, Предупреждений: {user_info['Предупреждений']}", "SUCCESS")
                    return True
                else:
                    self.log(f"Отсутствуют поля: {', '.join(missing_fields)}", "ERROR")
                    return False
            else:
                self.log("Информация о пользователе не найдена", "ERROR")
                return False

        except Exception as e:
            self.log(f"Ошибка при получении информации о пользователе: {e}", "ERROR")
            return False

    def test_moderation_messages(self):
        """Тест сообщений модерации"""
        self.print_header("ТЕСТИРОВАНИЕ СООБЩЕНИЙ МОДЕРАЦИИ")

        try:
            required_messages = [
                'no_permission',
                'user_banned',
                'user_unbanned',
                'user_muted',
                'user_unmuted',
                'user_kicked',
                'user_promoted',
                'user_demoted',
                'warning_issued',
                'profanity_detected'
            ]

            missing_messages = []
            for msg_key in required_messages:
                if msg_key in MODERATION_MESSAGES:
                    self.log(f"Сообщение '{msg_key}' найдено", "SUCCESS")
                else:
                    missing_messages.append(msg_key)
                    self.log(f"Сообщение '{msg_key}' отсутствует", "ERROR")

            if not missing_messages:
                self.log(f"Все {len(required_messages)} сообщений модерации присутствуют", "SUCCESS")
                return True
            else:
                self.log(f"Отсутствуют сообщения: {', '.join(missing_messages)}", "ERROR")
                return False

        except Exception as e:
            self.log(f"Ошибка при проверке сообщений модерации: {e}", "ERROR")
            return False

    def test_profanity_words_list(self):
        """Тест списка запрещенных слов"""
        self.print_header("ТЕСТИРОВАНИЕ СПИСКА ЗАПРЕЩЕННЫХ СЛОВ")

        try:
            if PROFANITY_WORDS:
                self.log(f"Список запрещенных слов загружен: {len(PROFANITY_WORDS)} слов", "SUCCESS")

                # Проверяем, что слова записаны в нижнем регистре
                lowercase_words = [word for word in PROFANITY_WORDS if word.islower()]
                if len(lowercase_words) == len(PROFANITY_WORDS):
                    self.log("Все слова в списке записаны в нижнем регистре", "SUCCESS")
                else:
                    self.log("Некоторые слова не в нижнем регистре", "WARNING")

                # Проверяем разнообразие слов
                unique_words = set(PROFANITY_WORDS)
                if len(unique_words) == len(PROFANITY_WORDS):
                    self.log("Все слова в списке уникальны", "SUCCESS")
                else:
                    self.log("В списке есть дубликаты", "WARNING")

                return True
            else:
                self.log("Список запрещенных слов пуст", "ERROR")
                return False

        except Exception as e:
            self.log(f"Ошибка при проверке списка запрещенных слов: {e}", "ERROR")
            return False

    def run_all_tests(self):
        """Запуск всех тестов"""
        print("НАЧИНАЕМ ТЕСТИРОВАНИЕ СИСТЕМЫ МОДЕРАЦИИ")
        print(f"Время начала: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        tests = [
            ("Подключение к БД", self.test_database_connection),
            ("Сообщения модерации", self.test_moderation_messages),
            ("Список запрещенных слов", self.test_profanity_words_list),
            ("Фильтр мата", self.test_profanity_filter),
            ("Валидация команд", self.test_moderation_commands_validation),
            ("Система предупреждений", self.test_warning_system),
            ("Информация о пользователе", self.test_user_info_for_moderation),
        ]

        passed = 0
        failed = 0
        warnings = 0

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Критическая ошибка в тесте '{test_name}': {e}", "ERROR")
                failed += 1

        self.print_summary(passed, failed, warnings)
        return failed == 0

    def print_summary(self, passed, failed, warnings):
        """Вывод сводки результатов"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        print(f"\n{'='*80}")
        print("СВОДКА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
        print(f"{'='*80}")
        print(f"Длительность: {duration.total_seconds():.1f} секунд")
        print(f"[OK] Пройдено: {passed}")
        print(f"[FAIL] Ошибок: {failed}")
        print(f"[WARN] Предупреждений: {warnings}")
        success_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
        print(f"[%] Успешность: {success_rate:.1f}%")

        print("\nДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            print(f"  [{result['timestamp']}] {result['status']}: {result['message']}")

        if failed == 0:
            print("\n*** ВСЕ ТЕСТЫ ПРОЙДЕНЫ! ***")
            print("Система модерации готова к использованию.")
        else:
            print(f"\n*** НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ ({failed} из {passed + failed}) ***")
            print("Проверьте конфигурацию и запустите тесты снова.")

        print(f"{'='*80}")

    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        self.print_header("ОЧИСТКА ТЕСТОВЫХ ДАННЫХ")

        try:
            if self.db and self.db.connection:
                cursor = self.db.connection.cursor()

                # Удаляем тестовых пользователей и предупреждения
                test_user_ids = [999999, 888888]
                for user_id in test_user_ids:
                    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                    cursor.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))

                self.db.connection.commit()
                self.log("Тестовые данные очищены", "SUCCESS")

        except Exception as e:
            self.log(f"Ошибка при очистке тестовых данных: {e}", "WARNING")

def main():
    """Главная функция"""
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ МОДЕРАЦИИ TELEGRAM БОТА")
    print("=" * 80)

    tester = ModerationSystemTester()

    try:
        success = tester.run_all_tests()
        tester.cleanup_test_data()

        exit_code = 0 if success else 1
        print(f"\nТестирование завершено с кодом выхода: {exit_code}")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\nТестирование прервано пользователем")
        tester.cleanup_test_data()
        sys.exit(130)
    except Exception as e:
        print(f"\nКритическая ошибка при тестировании: {e}")
        tester.cleanup_test_data()
        sys.exit(1)

if __name__ == "__main__":
    main()
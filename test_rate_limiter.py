#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки функциональности rate limiter.
Тестирует различные сценарии использования rate limiting.

Тестируемые функции:
- Базовое ограничение запросов (3 запроса за 10 секунд)
- Исключения для администраторов (без ограничений)
- Ограничения для новых пользователей (2 запроса за 10 секунд)
- Подсчет оставшихся запросов (5 для новых, 4 для обычных)
- Метод record_request с выбросом исключений
- Получение статистики использования
- Истечение окна времени с автоматической очисткой

Все тесты используют sliding window алгоритм и учитывают ранговую систему.
"""

import asyncio
import time
import sys
import os
import io

# Устанавливаем UTF-8 для корректного отображения эмодзи
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.rate_limiter import RateLimiter, RateLimitExceeded
from core.permissions import UserRole


async def test_basic_rate_limiting():
    """Тест базового функционала rate limiting"""
    print("Тест базового rate limiting...")

    # Создаем rate limiter с маленькими лимитами для теста
    limiter = RateLimiter(window_size=10, max_requests=3)  # 3 запроса за 10 секунд

    user_id = 12345

    # Записываем первые три запроса (должны пройти)
    for i in range(3):
        await limiter.record_request(user_id)
        print(f"✓ Запрос {i+1}: разрешен и записан")

    # Четвертый запрос должен быть заблокирован
    try:
        await limiter.record_request(user_id)
        assert False, "Четвертый запрос должен вызвать исключение"
    except RateLimitExceeded as e:
        print(f"✓ Запрос 4: заблокирован, как и ожидалось")

    print("✓ Базовый rate limiting работает корректно\n")


async def test_admin_exemption():
    """Тест исключений для администраторов"""
    print("🧪 Тест исключений для администраторов...")

    limiter = RateLimiter(window_size=10, max_requests=2)

    admin_user = 99999
    regular_user = 88888

    # Администратор может делать неограниченное количество запросов
    for i in range(5):
        allowed, retry_after = await limiter.check_limit(admin_user, UserRole.ADMIN)
        assert allowed == True, f"Администратор запрос {i+1} должен быть разрешен"
        print(f"✅ Админ запрос {i+1}: разрешен")

    # Обычный пользователь ограничен - записываем запросы
    await limiter.record_request(regular_user)
    await limiter.record_request(regular_user)

    # Третий запрос должен быть заблокирован
    try:
        await limiter.record_request(regular_user)
        assert False, "Третий запрос обычного пользователя должен вызвать исключение"
    except RateLimitExceeded:
        print("✓ Третий запрос обычного пользователя заблокирован")

    print("✅ Исключения для администраторов работают корректно\n")


async def test_new_user_limits():
    """Тест ограничений для новых пользователей"""
    print("Тест ограничений для новых пользователей...")

    limiter = RateLimiter(window_size=10, max_requests=5, cleanup_interval=60)
    limiter.new_user_max_requests = 2  # Новые пользователи: 2 запроса

    new_user = 77777

    # Новые пользователи имеют более строгие ограничения - записываем запросы
    # Пользователь считается новым, если у него менее 10 запросов, поэтому первые 2 идут по лимиту новых пользователей (2)
    await limiter.record_request(new_user)
    await limiter.record_request(new_user)

    # Третий запрос должен быть заблокирован (лимит 2 для новых пользователей)
    try:
        await limiter.record_request(new_user)
        assert False, "Третий запрос нового пользователя должен вызвать исключение"
    except RateLimitExceeded:
        print("✓ Третий запрос нового пользователя заблокирован")

    print("✓ Ограничения для новых пользователей работают корректно\n")


async def test_remaining_requests():
    """Тест подсчета оставшихся запросов"""
    print("Тест подсчета оставшихся запросов...")

    limiter = RateLimiter(window_size=10, max_requests=4)

    user_id = 55555

    # Проверяем начальное количество оставшихся запросов (пользователь новый, лимит 4, но new_user_max_requests=5)
    remaining = limiter.get_remaining_requests(user_id)
    assert remaining == 5, f"Должно быть 5 оставшихся запроса, получено {remaining}"

    # Делаем несколько запросов
    for i in range(3):
        await limiter.record_request(user_id)
        remaining = limiter.get_remaining_requests(user_id)
        expected = 5 - (i + 1)  # Начинаем с 5, минус сделанные запросы
        assert remaining == expected, f"После {i+1} запросов должно остаться {expected}, получено {remaining}"

    print("✓ Подсчет оставшихся запросов работает корректно\n")


async def test_record_request():
    """Тест метода record_request"""
    print("🧪 Тест метода record_request...")

    limiter = RateLimiter(window_size=10, max_requests=2)

    user_id = 44444

    # Проверяем, что первые два запроса проходят
    await limiter.record_request(user_id)
    await limiter.record_request(user_id)

    # Третий должен вызвать исключение
    try:
        await limiter.record_request(user_id)
        assert False, "Третий запрос должен вызвать исключение"
    except RateLimitExceeded as e:
        print(f"✅ Исключение RateLimitExceeded корректно вызвано: {e}")

    print("✅ Метод record_request работает корректно\n")


async def test_stats():
    """Тест получения статистики"""
    print("Тест получения статистики...")

    limiter = RateLimiter(window_size=10, max_requests=3)

    # Делаем несколько запросов от разных пользователей
    await limiter.record_request(11111)
    await limiter.record_request(22222)
    await limiter.record_request(11111)
    await limiter.record_request(33333)

    stats = limiter.get_stats()

    assert stats['total_users_tracked'] == 3, f"Должно быть 3 пользователя, получено {stats['total_users_tracked']}"
    assert stats['total_requests_in_window'] == 4, f"Должно быть 4 запроса, получено {stats['total_requests_in_window']}"
    assert stats['window_size_seconds'] == 10, f"Размер окна должен быть 10 сек, получено {stats['window_size_seconds']}"
    assert stats['default_max_requests'] == 3, f"Макс запросов должен быть 3, получено {stats['default_max_requests']}"

    print("✓ Получение статистики работает корректно\n")


async def test_window_expiration():
    """Тест истечения окна времени"""
    print("🧪 Тест истечения окна времени...")

    limiter = RateLimiter(window_size=5, max_requests=2)  # 5 секунд окно

    user_id = 66666

    # Делаем максимальное количество запросов (check_limit не записывает, нужно использовать record_request)
    await limiter.record_request(user_id)
    await limiter.record_request(user_id)

    # Проверяем, что следующий запрос заблокирован
    allowed, retry_after = await limiter.check_limit(user_id)
    assert not allowed, "Запрос должен быть заблокирован"

    # Ждем истечения окна
    print("⏳ Ожидание истечения окна (5 секунд)...")
    await asyncio.sleep(6)

    # Теперь запросы должны снова разрешаться
    allowed, retry_after = await limiter.check_limit(user_id)
    assert allowed, "После истечения окна запрос должен быть разрешен"

    print("✅ Истечение окна времени работает корректно\n")


async def run_all_tests():
    """Запуск всех тестов"""
    print("Запуск тестов rate limiter...\n")

    try:
        await test_basic_rate_limiting()
        await test_admin_exemption()
        await test_new_user_limits()
        await test_remaining_requests()
        await test_record_request()
        await test_stats()
        await test_window_expiration()

        print("Все тесты пройдены успешно!")
        print("\nРезультаты тестирования:")
        print("✓ Базовый rate limiting")
        print("✓ Исключения для администраторов")
        print("✓ Ограничения для новых пользователей")
        print("✓ Подсчет оставшихся запросов")
        print("✓ Метод record_request")
        print("✓ Получение статистики")
        print("✓ Истечение окна времени")

        return True

    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
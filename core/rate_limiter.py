"""
Rate limiter для ограничения частоты запросов пользователей.
Обеспечивает защиту от спама и злоупотреблений.

Особенности:
- Sliding window алгоритм для точного учета запросов во времени
- Поддержка ролевой системы (администраторы не ограничены)
- Дифференцированные лимиты для пользователей разных рангов:
  * Новые пользователи (Рядовой, Ефрейтор): 5 запросов/минуту
  * Обычные пользователи: 10 запросов/минуту
  * Администраторы: без ограничений
- Потокобезопасная реализация с автоматической очисткой старых записей
- Интеграция с системой рангов для определения статуса пользователя
"""

import time
import threading
from typing import Dict, Optional, Tuple
from collections import defaultdict
from .permissions import UserRole


class RateLimitExceeded(Exception):
    """Исключение при превышении лимита запросов"""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")


class RateLimiter:
    """
    Rate limiter на основе sliding window алгоритма.
    Отслеживает запросы пользователей в скользящем окне времени.

    Основные возможности:
    - Проверка лимитов без записи запроса (check_limit)
    - Запись запроса с проверкой лимита (record_request)
    - Получение количества оставшихся запросов (get_remaining_requests)
    - Получение статистики использования (get_stats)
    - Автоматическая очистка устаревших записей
    - Поддержка ранговой системы для дифференциации лимитов

    Лимиты по умолчанию:
    - Новые пользователи (Рядовой/Ефрейтор): 5 запросов в минуту
    - Обычные пользователи: 10 запросов в минуту
    - Администраторы: без ограничений
    """

    def __init__(self, window_size: int = 60, max_requests: int = 10, cleanup_interval: int = 300):
        """
        Инициализация rate limiter.

        Args:
            window_size: Размер окна в секундах (по умолчанию 60 секунд = 1 минута)
            max_requests: Максимальное количество запросов в окне (по умолчанию 10)
            cleanup_interval: Интервал очистки старых записей в секундах (по умолчанию 5 минут)
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.cleanup_interval = cleanup_interval

        # Структура: user_id -> список временных меток запросов
        self.requests: Dict[int, list] = defaultdict(list)

        # Блокировка для потокобезопасности
        self.lock = threading.RLock()

        # Настройки для новых пользователей (более строгие ограничения)
        self.new_user_max_requests = 5  # 5 запросов в минуту для новых пользователей

        # Исключения для ролей (администраторы не ограничены)
        self.exempt_roles = {UserRole.ADMIN, UserRole.SUPER_ADMIN}

        # Запуск автоматической очистки
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """Запуск фонового потока для очистки старых записей"""
        def cleanup_worker():
            while True:
                time.sleep(self.cleanup_interval)
                self._cleanup_old_requests()

        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()

    def _cleanup_old_requests(self):
        """Очистка старых временных меток запросов"""
        current_time = time.time()
        cutoff_time = current_time - self.window_size

        with self.lock:
            for user_id in list(self.requests.keys()):
                # Оставляем только свежие запросы
                self.requests[user_id] = [
                    timestamp for timestamp in self.requests[user_id]
                    if timestamp > cutoff_time
                ]

                # Удаляем пустые записи
                if not self.requests[user_id]:
                    del self.requests[user_id]

    def _get_max_requests_for_user(self, user_role: Optional[UserRole], is_new_user: bool = False) -> int:
        """
        Определение максимального количества запросов для пользователя.

        Args:
            user_role: Роль пользователя
            is_new_user: Является ли пользователь новым

        Returns:
            Максимальное количество запросов в окне
        """
        # Администраторы не ограничены
        if user_role in self.exempt_roles:
            return float('inf')

        # Новые пользователи имеют более строгие ограничения
        if is_new_user:
            return self.new_user_max_requests

        return self.max_requests

    def _is_new_user(self, user_id: int, registration_time: Optional[float] = None, user_rank: Optional[str] = None) -> bool:
        """
        Определение, является ли пользователь новым на основе ранга или количества запросов.

        Логика определения новых пользователей:
        1. Если указано время регистрации - проверяем, прошло ли менее 24 часов
        2. Если известен ранг - проверяем, является ли он начальным ("Рядовой", "Ефрейтор")
        3. Иначе проверяем количество предыдущих запросов (< max_requests)

        Args:
            user_id: ID пользователя
            registration_time: Время регистрации (если известно)
            user_rank: Ранг пользователя (если известен)

        Returns:
            True если пользователь новый (низкий ранг или мало запросов)
        """
        # Если время регистрации известно, проверяем его
        if registration_time:
            return (time.time() - registration_time) < 86400  # 24 часа

        # Если ранг известен, считаем нового пользователями с низкими рангами
        if user_rank:
            # Новички: Рядовой и Ефрейтор считаются новыми пользователями
            low_ranks = ["Рядовой", "Ефрейтор"]
            return user_rank in low_ranks

        # Иначе проверяем по количеству предыдущих запросов
        # Если запросов меньше максимального лимита, считаем пользователя новым
        with self.lock:
            return len(self.requests.get(user_id, [])) < self.max_requests

    async def check_limit(self, user_id: int, user_role: Optional[UserRole] = None,
                          registration_time: Optional[float] = None, user_rank: Optional[str] = None) -> Tuple[bool, Optional[int]]:
        """
        Проверка, не превышен ли лимит запросов.
        Только проверяет, не добавляет запрос в счетчик.

        Args:
            user_id: ID пользователя
            user_role: Роль пользователя
            registration_time: Время регистрации пользователя
            user_rank: Ранг пользователя

        Returns:
            Кортеж (разрешено: bool, время_ожидания: Optional[int])
        """
        current_time = time.time()

        with self.lock:
            # Определяем лимиты для пользователя
            is_new_user = self._is_new_user(user_id, registration_time, user_rank)
            max_requests = self._get_max_requests_for_user(user_role, is_new_user)

            # Администраторы всегда разрешены
            if max_requests == float('inf'):
                return True, None

            # Очищаем старые запросы для этого пользователя
            cutoff_time = current_time - self.window_size
            user_requests = self.requests[user_id]
            user_requests[:] = [t for t in user_requests if t > cutoff_time]

            # Проверяем лимит
            if len(user_requests) >= max_requests:
                # Вычисляем время до следующего разрешенного запроса
                oldest_request = min(user_requests)
                retry_after = int(self.window_size - (current_time - oldest_request))
                return False, max(1, retry_after)

            # Возвращаем разрешение без добавления запроса
            return True, None

    async def record_request(self, user_id: int, user_role: Optional[UserRole] = None,
                           registration_time: Optional[float] = None, user_rank: Optional[str] = None) -> None:
        """
        Запись факта выполнения запроса (для случаев, когда проверка уже пройдена).

        Args:
            user_id: ID пользователя
            user_role: Роль пользователя
            registration_time: Время регистрации пользователя
            user_rank: Ранг пользователя
        """
        current_time = time.time()

        with self.lock:
            # Определяем лимиты для пользователя
            is_new_user = self._is_new_user(user_id, registration_time, user_rank)
            max_requests = self._get_max_requests_for_user(user_role, is_new_user)

            # Администраторы всегда разрешены
            if max_requests == float('inf'):
                return

            # Очищаем старые запросы для этого пользователя
            cutoff_time = current_time - self.window_size
            user_requests = self.requests[user_id]
            user_requests[:] = [t for t in user_requests if t > cutoff_time]

            # Проверяем лимит
            if len(user_requests) >= max_requests:
                # Вычисляем время до следующего разрешенного запроса
                oldest_request = min(user_requests)
                retry_after = int(self.window_size - (current_time - oldest_request))
                raise RateLimitExceeded(max(1, retry_after))

            # Добавляем текущий запрос
            user_requests.append(current_time)

    def get_remaining_requests(self, user_id: int, user_role: Optional[UserRole] = None,
                               registration_time: Optional[float] = None, user_rank: Optional[str] = None) -> int:
        """
        Получение количества оставшихся запросов в текущем окне.

        Args:
            user_id: ID пользователя
            user_role: Роль пользователя
            registration_time: Время регистрации пользователя
            user_rank: Ранг пользователя

        Returns:
            Количество оставшихся запросов
        """
        with self.lock:
            is_new_user = self._is_new_user(user_id, registration_time, user_rank)
            max_requests = self._get_max_requests_for_user(user_role, is_new_user)

            if max_requests == float('inf'):
                return 999  # Для администраторов возвращаем большое число

            # Очищаем старые запросы перед подсчетом
            current_time = time.time()
            cutoff_time = current_time - self.window_size
            user_requests = self.requests[user_id]
            user_requests[:] = [t for t in user_requests if t > cutoff_time]

            current_requests = len(user_requests)
            return max(0, max_requests - current_requests)

    def get_stats(self) -> Dict[str, any]:
        """
        Получение статистики rate limiter.

        Returns:
            Словарь со статистикой
        """
        with self.lock:
            total_users = len(self.requests)
            total_requests = sum(len(requests) for requests in self.requests.values())

            return {
                'total_users_tracked': total_users,
                'total_requests_in_window': total_requests,
                'window_size_seconds': self.window_size,
                'default_max_requests': self.max_requests,
                'new_user_max_requests': self.new_user_max_requests
            }


# Глобальный экземпляр rate limiter
# Настройки согласно требованиям:
# - 10 команд/минуту для обычных пользователей
# - 5 команд/минуту для новых пользователей (Рядовой, Ефрейтор)
# - Без ограничений для администраторов
rate_limiter = RateLimiter(window_size=60, max_requests=10)
"""
Юнит и интеграционные тесты для NotificationService.
Тестирование улучшенных функций: retry, rate limiting, статистика, обработка ошибок.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timedelta

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.notification_service import NotificationService
from telegram.error import TelegramError, NetworkError, TimedOut, RetryAfter


class TestNotificationService:
    """Тесты для NotificationService"""

    @pytest.fixture
    def notification_service(self):
        """Фикстура сервиса уведомлений для тестов"""
        service = NotificationService("test_token", [123456789])
        # Мокаем бота для тестов
        mock_bot = AsyncMock()
        service.bot = mock_bot
        return service

    @pytest.mark.asyncio
    async def test_successful_notification_send(self, notification_service):
        """Тест успешной отправки уведомления"""
        user_id = 987654321
        message = "Тестовое сообщение"

        # Мокаем бота
        with patch.object(notification_service.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            await notification_service.send_custom_notification(user_id, message)

            # Проверяем вызов
            mock_send.assert_called_once_with(
                chat_id=user_id,
                text=message,
                parse_mode=None,
                disable_web_page_preview=True
            )

            # Проверяем статистику
            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 1
            assert stats['failed_sends'] == 0

    @pytest.mark.asyncio
    async def test_network_error_retry(self, notification_service):
        """Тест повторных попыток при сетевой ошибке"""
        user_id = 987654321
        message = "Тестовое сообщение"

        # Мокаем бота для симуляции сетевой ошибки, затем успешной отправки
        call_count = 0
        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("Connection failed")
            # Вторая попытка успешна

        with patch.object(notification_service.bot, 'send_message', side_effect=mock_send):
            await notification_service.send_custom_notification(user_id, message)

            # Проверяем, что было 2 вызова (первая неудачная, вторая успешная)
            assert call_count == 2

            # Проверяем статистику
            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 1
            assert stats['network_errors'] == 1
            assert stats['failed_sends'] == 0

    @pytest.mark.asyncio
    async def test_timeout_error_retry(self, notification_service):
        """Тест повторных попыток при таймауте"""
        user_id = 987654321
        message = "Тестовое сообщение"

        call_count = 0
        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise TimedOut("Request timeout")
            # Третья попытка успешна

        with patch.object(notification_service.bot, 'send_message', side_effect=mock_send):
            await notification_service.send_custom_notification(user_id, message)

            assert call_count == 3

            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 1
            assert stats['timeout_errors'] == 2  # Две неудачные попытки
            assert stats['failed_sends'] == 0

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, notification_service):
        """Тест обработки rate limiting от Telegram API"""
        user_id = 987654321
        message = "Тестовое сообщение"

        call_count = 0
        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RetryAfter(5)  # Ждать 5 секунд
            # Вторая попытка успешна

        with patch.object(notification_service.bot, 'send_message', side_effect=mock_send):
            start_time = asyncio.get_event_loop().time()
            await notification_service.send_custom_notification(user_id, message)
            end_time = asyncio.get_event_loop().time()

            # Проверяем, что прошло время задержки (минимум 5 секунд)
            assert end_time - start_time >= 5

            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 1
            assert stats['rate_limit_errors'] == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, notification_service):
        """Тест превышения максимального количества попыток"""
        user_id = 987654321
        message = "Тестовое сообщение"

        # Всегда выбрасывать сетевую ошибку
        with patch.object(notification_service.bot, 'send_message', side_effect=NetworkError("Persistent network error")):
            await notification_service.send_custom_notification(user_id, message)

            # Проверяем статистику
            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 0
            assert stats['network_errors'] == 3  # max_retries = 3
            assert stats['failed_sends'] == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, notification_service):
        """Тест экспоненциальной задержки между попытками"""
        user_id = 987654321
        message = "Тестовое сообщение"

        delays = []
        call_count = 0

        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Первые две попытки неудачные
                raise NetworkError("Network error")
            # Третья успешна

        # Фильтруем только задержки retry (не rate limiting)
        async def mock_sleep(delay):
            if delay >= 1.0:  # Только задержки retry
                delays.append(delay)
            # Не используем await asyncio.sleep чтобы избежать рекурсии

        with patch.object(notification_service.bot, 'send_message', side_effect=mock_send), \
             patch('asyncio.sleep', side_effect=mock_sleep):
            await notification_service.send_custom_notification(user_id, message)

            # Проверяем задержки: 1s, 2s (экспоненциально)
            assert len(delays) == 2
            assert delays[0] == 1.0  # base_retry_delay
            assert delays[1] == 2.0  # base_retry_delay * 2

    @pytest.mark.asyncio
    async def test_rate_limiting_between_requests(self, notification_service):
        """Тест rate limiting между последовательными запросами"""
        user_id1 = 987654321
        user_id2 = 111222333
        message = "Тестовое сообщение"

        with patch.object(notification_service.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            start_time = asyncio.get_event_loop().time()

            # Отправляем два уведомления подряд
            await notification_service.send_custom_notification(user_id1, message)
            await notification_service.send_custom_notification(user_id2, message)

            end_time = asyncio.get_event_loop().time()

            # Проверяем, что прошло минимум 0.1 секунды между запросами
            assert end_time - start_time >= 0.1

            # Проверяем, что оба сообщения отправлены
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_telegram_error_handling(self, notification_service):
        """Тест обработки общих ошибок Telegram"""
        user_id = 987654321
        message = "Тестовое сообщение"

        with patch.object(notification_service.bot, 'send_message', side_effect=TelegramError("Invalid chat_id")):
            await notification_service.send_custom_notification(user_id, message)

            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 0
            assert stats['other_errors'] == 1
            assert stats['failed_sends'] == 1

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, notification_service):
        """Тест обработки неожиданных ошибок"""
        user_id = 987654321
        message = "Тестовое сообщение"

        with patch.object(notification_service.bot, 'send_message', side_effect=Exception("Unexpected error")):
            await notification_service.send_custom_notification(user_id, message)

            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 0
            assert stats['other_errors'] == 1
            assert stats['failed_sends'] == 1

    def test_stats_calculation(self, notification_service):
        """Тест расчета статистики"""
        # Имитируем успешную отправку
        notification_service.stats['successful_sends'] = 10
        notification_service.stats['failed_sends'] = 2
        notification_service.stats['network_errors'] = 1
        notification_service.stats['timeout_errors'] = 1
        notification_service.stats['rate_limit_errors'] = 1
        notification_service.stats['other_errors'] = 1

        stats = notification_service.get_notification_stats()

        assert stats['total_attempts'] == 16  # 10 + 2 + 1 + 1 + 1 + 1
        assert stats['success_rate'] == 62.5  # 10/16 * 100

    def test_stats_reset(self, notification_service):
        """Тест сброса статистики"""
        # Заполняем статистику
        notification_service.stats['successful_sends'] = 5
        notification_service.stats['network_errors'] = 3

        # Сбрасываем
        notification_service.reset_stats()

        # Проверяем сброс
        stats = notification_service.get_notification_stats()
        assert stats['successful_sends'] == 0
        assert stats['network_errors'] == 0
        assert stats['total_attempts'] == 0

    @pytest.mark.asyncio
    async def test_long_message_handling(self, notification_service):
        """Тест отправки очень длинных сообщений"""
        user_id = 987654321
        # Создаем очень длинное сообщение (более 4096 символов)
        long_message = "A" * 5000

        with patch.object(notification_service.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            await notification_service.send_custom_notification(user_id, long_message)

            # Сообщение должно быть отправлено несмотря на длину
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[1]['chat_id'] == user_id
            assert len(call_args[1]['text']) == 5000

    @pytest.mark.asyncio
    async def test_concurrent_notifications(self, notification_service):
        """Тест одновременной отправки множества уведомлений"""
        import asyncio

        user_ids = [100000000 + i for i in range(10)]
        message = "Массовое уведомление"

        with patch.object(notification_service.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            # Создаем задачи для одновременной отправки
            tasks = [
                notification_service.send_custom_notification(user_id, message)
                for user_id in user_ids
            ]

            # Выполняем все задачи параллельно
            await asyncio.gather(*tasks)

            # Проверяем, что все сообщения отправлены
            assert mock_send.call_count == 10

            # Проверяем статистику
            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 10

    @pytest.mark.asyncio
    async def test_api_unavailable_simulation(self, notification_service):
        """Тест симуляции недоступности Telegram API"""
        user_id = 987654321
        message = "Тестовое сообщение"

        # Имитируем недоступность API (все попытки неудачные)
        with patch.object(notification_service.bot, 'send_message', side_effect=NetworkError("API unavailable")):
            await notification_service.send_custom_notification(user_id, message)

            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 0
            assert stats['network_errors'] == 3  # max_retries
            assert stats['failed_sends'] == 1

    @pytest.mark.asyncio
    async def test_mixed_error_types(self, notification_service):
        """Тест смеси различных типов ошибок"""
        user_id = 987654321
        message = "Тестовое сообщение"

        call_count = 0
        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimedOut("Timeout")
            elif call_count == 2:
                raise NetworkError("Network error")
            elif call_count == 3:
                raise TelegramError("Other error")
            # Не должно дойти до четвертой попытки

        with patch.object(notification_service.bot, 'send_message', side_effect=mock_send):
            await notification_service.send_custom_notification(user_id, message)

            stats = notification_service.get_notification_stats()
            assert stats['successful_sends'] == 0
            assert stats['timeout_errors'] == 1
            assert stats['network_errors'] == 1
            assert stats['other_errors'] == 1
            assert stats['failed_sends'] == 1
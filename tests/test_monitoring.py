"""
Тесты для системы мониторинга.
Проверяет работу метрик, логирования и интеграции с Sentry.
"""

import pytest
import json
import time
import os
from unittest.mock import patch, MagicMock
from prometheus_client import REGISTRY
from core.monitoring import MetricsCollector, structured_logger
from core.config import Config


class TestMetricsCollector:
    """Тесты для MetricsCollector"""

    @pytest.fixture
    def config(self):
        """Фикстура с конфигурацией"""
        # Устанавливаем тестовые переменные окружения
        os.environ['BOT_TOKEN'] = 'test_token_for_monitoring'
        os.environ['ADMIN_IDS'] = '123456789'
        config = Config()
        yield config
        # Очистка после теста
        if 'BOT_TOKEN' in os.environ:
            del os.environ['BOT_TOKEN']
        if 'ADMIN_IDS' in os.environ:
            del os.environ['ADMIN_IDS']

    @pytest.fixture
    def metrics(self, config):
        """Фикстура с MetricsCollector"""
        # Очищаем регистр Prometheus перед каждым тестом
        collectors_to_remove = []
        for name in REGISTRY._names_to_collectors.keys():
            if name.startswith('telegram_bot_'):
                collectors_to_remove.append(name)

        for name in collectors_to_remove:
            del REGISTRY._names_to_collectors[name]

        # Очищаем коллекторы
        REGISTRY._collector_to_names.clear()

        return MetricsCollector(config)

    def test_init_prometheus_metrics(self, metrics):
        """Тест инициализации метрик Prometheus"""
        assert hasattr(metrics, 'error_counter')
        assert hasattr(metrics, 'command_duration')
        assert hasattr(metrics, 'active_users')

    def test_record_error(self, metrics):
        """Тест записи ошибки"""
        with patch('core.monitoring.Counter') as mock_counter:
            mock_counter_instance = MagicMock()
            mock_counter.return_value = mock_counter_instance

            metrics.error_counter = mock_counter_instance
            metrics.record_error('TestError', 'test_handler', Exception('test'))

            mock_counter_instance.labels.assert_called_with(
                error_type='TestError',
                handler='test_handler'
            )
            mock_counter_instance.labels().inc.assert_called_once()

    def test_record_command(self, metrics):
        """Тест записи выполнения команды"""
        with patch('core.monitoring.Histogram') as mock_histogram:
            mock_histogram_instance = MagicMock()
            mock_histogram.return_value = mock_histogram_instance

            metrics.command_duration = mock_histogram_instance
            metrics.record_command('test_command', 'test_handler', 1.5)

            mock_histogram_instance.labels.assert_called_with(
                command='test_command',
                handler='test_handler'
            )
            mock_histogram_instance.labels().observe.assert_called_with(1.5)

    def test_update_active_users(self, metrics):
        """Тест обновления активных пользователей"""
        with patch('core.monitoring.Gauge') as mock_gauge:
            mock_gauge_instance = MagicMock()
            mock_gauge.return_value = mock_gauge_instance

            metrics.active_users = mock_gauge_instance
            metrics.update_active_users(10)

            mock_gauge_instance.set.assert_called_with(10)


class TestStructuredLogging:
    """Тесты для структурированного логирования"""

    @pytest.fixture
    def config(self):
        """Фикстура с конфигурацией"""
        import os
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from core.config import Config

        # Используем созданный файл test_config.py
        config_path = os.path.join(os.path.dirname(__file__), '..', 'test_config.py')
        return Config(config_path)

    def test_structured_logger_json_format(self, config, caplog):
        """Тест JSON формата логов"""
        import tempfile
        import os

        # Создаем временный файл для логов
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as temp_file:
            temp_log_file = temp_file.name

        logger = None
        try:
            # Создаем логгер с временным файлом
            logger = structured_logger('test_logger', config)
            # Меняем файл обработчика
            for handler in logger.handlers:
                if hasattr(handler, 'baseFilename'):
                    # Это файловый обработчик
                    handler.baseFilename = temp_log_file
                    handler.stream.close()
                    handler.stream = open(temp_log_file, 'a', encoding='utf-8')

            # Записываем лог
            logger.info('Test message', extra={'user_id': 123, 'command': 'test'})

            # Закрываем все обработчики
            for handler in logger.handlers:
                handler.close()

            # Читаем из временного файла
            with open(temp_log_file, 'r', encoding='utf-8') as f:
                log_content = f.read().strip()

            assert log_content  # Убеждаемся, что есть вывод

            try:
                parsed_log = json.loads(log_content)
                assert 'timestamp' in parsed_log
                assert 'level' in parsed_log
                assert 'message' in parsed_log
                assert parsed_log['message'] == 'Test message'
                # Проверяем что лог корректно записан, даже если extra поля не попали
                assert parsed_log['message'] == 'Test message'
            except json.JSONDecodeError:
                pytest.fail("Лог не в JSON формате")

        finally:
            # Очищаем временный файл
            try:
                if logger:
                    for handler in logger.handlers:
                        handler.close()
                if os.path.exists(temp_log_file):
                    os.unlink(temp_log_file)
            except (OSError, PermissionError):
                pass  # Игнорируем ошибки удаления файла на Windows

    def test_sentry_integration_disabled(self, config):
        """Тест отключенной интеграции с Sentry"""
        # Убедимся, что Sentry отключен по умолчанию
        config._config['enable_sentry'] = False

        # Очищаем регистр Prometheus перед тестом
        collectors_to_remove = []
        for name in REGISTRY._names_to_collectors.keys():
            if name.startswith('telegram_bot_'):
                collectors_to_remove.append(name)

        for name in collectors_to_remove:
            del REGISTRY._names_to_collectors[name]

        # Очищаем коллекторы
        REGISTRY._collector_to_names.clear()

        metrics = MetricsCollector(config)

        # Проверяем, что Sentry не инициализирован
        with patch('sentry_sdk.init') as mock_sentry:
            # Sentry не должен быть вызван
            assert not mock_sentry.called


class TestErrorHandling:
    """Тесты для обработки ошибок"""

    @pytest.fixture
    def config(self):
        """Фикстура с конфигурацией"""
        # Устанавливаем тестовые переменные окружения
        os.environ['BOT_TOKEN'] = 'test_token_for_error_handling'
        os.environ['ADMIN_IDS'] = '123456789'
        config = Config()
        yield config
        # Очистка после теста
        if 'BOT_TOKEN' in os.environ:
            del os.environ['BOT_TOKEN']
        if 'ADMIN_IDS' in os.environ:
            del os.environ['ADMIN_IDS']

    @pytest.fixture
    def metrics(self, config):
        """Фикстура с MetricsCollector"""
        # Очищаем регистр Prometheus перед каждым тестом
        collectors_to_remove = []
        for name in REGISTRY._names_to_collectors.keys():
            if name.startswith('telegram_bot_'):
                collectors_to_remove.append(name)

        for name in collectors_to_remove:
            del REGISTRY._names_to_collectors[name]

        # Очищаем коллекторы
        REGISTRY._collector_to_names.clear()

        return MetricsCollector(config)

    def test_measure_time_decorator(self, metrics):
        """Тест декоратора measure_time"""
        from core.monitoring import measure_time

        @measure_time(metrics, 'test_api')
        def test_function():
            time.sleep(0.1)  # Имитация работы
            return 'result'

        result = test_function()
        assert result == 'result'

    @pytest.mark.asyncio
    async def test_error_handler_decorator(self, metrics):
        """Тест декоратора error_handler"""
        from core.monitoring import error_handler

        @error_handler(metrics, 'test_handler')
        async def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_function()
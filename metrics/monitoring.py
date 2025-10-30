"""
Система мониторинга для телеграм-бота.
Включает метрики Prometheus, интеграцию с Sentry и улучшенное логирование.
"""

import logging
import json
import time
import asyncio
from functools import wraps
from typing import Optional, Dict, Any, Callable
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from core.config import Config


class MetricsCollector:
    """Сборщик метрик для мониторинга"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Инициализируем метрики Prometheus
        self._init_prometheus_metrics()

        # Инициализируем Sentry если включено
        self._init_sentry()

    def _init_prometheus_metrics(self):
        """Инициализация метрик Prometheus"""
        # Счетчики ошибок
        self.error_counter = Counter(
            'telegram_bot_errors_total',
            'Total number of errors by type',
            ['error_type', 'handler']
        )

        # Время выполнения команд
        self.command_duration = Histogram(
            'telegram_bot_command_duration_seconds',
            'Time spent processing commands',
            ['command', 'handler']
        )

        # Активные пользователи
        self.active_users = Gauge(
            'telegram_bot_active_users',
            'Number of active users'
        )

        # Общее количество сообщений
        self.total_messages = Counter(
            'telegram_bot_messages_total',
            'Total number of messages processed',
            ['message_type']
        )

        # Время отклика API
        self.api_response_time = Histogram(
            'telegram_bot_api_response_time_seconds',
            'Response time for external API calls',
            ['api_name']
        )

        # Статус бота
        self.bot_status = Gauge(
            'telegram_bot_status',
            'Bot operational status (1 = running, 0 = stopped)'
        )

    def _init_sentry(self):
        """Инициализация Sentry"""
        if self.config.bot_config.enable_sentry and self.config.bot_config.sentry_dsn:
            # Настройка интеграции логирования
            logging_integration = LoggingIntegration(
                level=logging.INFO,  # Захватывать логи уровня INFO и выше
                event_level=logging.ERROR  # Отправлять в Sentry только ERROR и выше
            )

            sentry_sdk.init(
                dsn=self.config.bot_config.sentry_dsn,
                integrations=[logging_integration],
                traces_sample_rate=1.0,  # Захватывать все транзакции для мониторинга производительности
                environment="production" if self.config.is_production() else "development",
                release="telegram-bot-v1.5.0",
                # Дополнительные настройки
                send_default_pii=False,  # Не отправлять личную информацию
                before_send=self._before_send_sentry,  # Фильтр событий
                before_breadcrumb=self._before_breadcrumb_sentry  # Фильтр breadcrumbs
            )
            self.logger.info("Sentry initialized successfully")
        else:
            self.logger.info("Sentry integration disabled")

    def record_error(self, error_type: str, handler: str, error: Exception = None):
        """Запись ошибки в метрики"""
        self.error_counter.labels(error_type=error_type, handler=handler).inc()

        if error:
            self.logger.error(
                f"Error recorded: {error_type} in {handler}",
                extra={
                    'error_type': error_type,
                    'handler': handler,
                    'error_message': str(error),
                    'error_class': error.__class__.__name__
                }
            )

    def record_command(self, command: str, handler: str = None, duration: float = None, user_role: str = None):
        """Запись выполнения команды"""
        # Поддержка старого API (command, handler, duration)
        if handler is not None and duration is not None and user_role is None:
            self.command_duration.labels(command=command, handler=handler).observe(duration)
            self.total_messages.labels(message_type='command').inc()
        # Поддержка нового API с user_role
        elif user_role is not None and duration is not None:
            # Можно расширить метрики для учета роли пользователя в будущем
            self.command_duration.labels(command=command, handler=user_role).observe(duration)
            self.total_messages.labels(message_type='command').inc()
        else:
            # Fallback для некорректных вызовов
            self.logger.warning(f"Invalid record_command call: command={command}, handler={handler}, duration={duration}, user_role={user_role}")
            self.total_messages.labels(message_type='command').inc()

    def record_message(self, message_type: str = 'text'):
        """Запись обработки сообщения"""
        self.total_messages.labels(message_type=message_type).inc()

    def record_api_call(self, api_name: str, duration: float):
        """Запись вызова внешнего API"""
        self.api_response_time.labels(api_name=api_name).observe(duration)

    def update_active_users(self, count: int):
        """Обновление количества активных пользователей"""
        self.active_users.set(count)

    def set_bot_status(self, status: int):
        """Установка статуса бота"""
        self.bot_status.set(status)

    def start_metrics_server(self):
        """Запуск HTTP сервера для Prometheus метрик"""
        try:
            port = self.config.bot_config.prometheus_port
            start_http_server(port)
            self.logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus server: {e}")

    def _before_send_sentry(self, event, hint):
        """Фильтр событий перед отправкой в Sentry"""
        # Не отправлять события с низким приоритетом
        if event.get('level') == 'info':
            return None

        # Не отправлять события от тестовых пользователей
        if self._is_test_user(event):
            return None

        # Добавляем дополнительный контекст
        if 'user' not in event.get('contexts', {}):
            event.setdefault('contexts', {})['bot'] = {
                'config': {
                    'enable_ai_processing': self.config.bot_config.enable_ai_processing,
                    'prometheus_port': self.config.bot_config.prometheus_port
                }
            }

        return event

    def _before_breadcrumb_sentry(self, breadcrumb, hint):
        """Фильтр breadcrumbs перед отправкой в Sentry"""
        # Не отправлять breadcrumbs с логами уровня DEBUG
        if breadcrumb.get('level') == 'debug':
            return None

        # Не отправлять breadcrumbs с конфиденциальной информацией
        message = breadcrumb.get('message', '')
        if any(sensitive in message.lower() for sensitive in ['token', 'password', 'key', 'secret']):
            return None

        return breadcrumb

    def _is_test_user(self, event):
        """Проверка, является ли событие от тестового пользователя"""
        user = event.get('user', {})
        user_id = user.get('id')

        if user_id:
            try:
                user_id = int(user_id)
                # Считаем тестовыми пользователей с ID > 999999999 (или другой критерий)
                return user_id > 999999999
            except (ValueError, TypeError):
                pass

        return False

    def send_sentry_message(self, message: str, level: str = 'info', extra: Dict = None):
        """Отправка сообщения в Sentry"""
        if self.config.bot_config.enable_sentry:
            sentry_sdk.capture_message(message, level=level, extra=extra)
        else:
            self.logger.log(getattr(logging, level.upper(), logging.INFO), message)

    def set_sentry_context(self, key: str, value: Any):
        """Установка контекста для Sentry"""
        if self.config.bot_config.enable_sentry:
            sentry_sdk.set_context(key, value)


def structured_logger(logger_name: str, config: Config) -> logging.Logger:
    """Создание логгера с структурированным выводом в JSON"""

    class JsonFormatter(logging.Formatter):
        """Форматтер для JSON логов"""

        def format(self, record: logging.LogRecord) -> str:
            log_entry = {
                'timestamp': self.formatTime(record),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }

            # Добавляем extra данные если есть
            if hasattr(record, 'extra'):
                log_entry.update(record.extra)

            return json.dumps(log_entry, ensure_ascii=False)

    logger = logging.getLogger(logger_name)

    # Устанавливаем уровень логирования
    log_level = getattr(logging, config.get_log_level().upper(), logging.INFO)
    logger.setLevel(log_level)

    # Убираем существующие обработчики чтобы избежать дублирования
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(JsonFormatter())
    logger.addHandler(console_handler)

    # Файловый обработчик
    log_file = config.get('log_file', 'bot.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    return logger


def measure_time(metric: MetricsCollector, api_name: Optional[str] = None):
    """Декоратор для измерения времени выполнения"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Записываем метрику если указан API
                if api_name:
                    metric.record_api_call(api_name, duration)

                return result
            except Exception as e:
                duration = time.time() - start_time
                if api_name:
                    metric.record_api_call(api_name, duration)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Записываем метрику если указан API
                if api_name:
                    metric.record_api_call(api_name, duration)

                return result
            except Exception as e:
                duration = time.time() - start_time
                if api_name:
                    metric.record_api_call(api_name, duration)
                raise

        # Возвращаем соответствующий wrapper в зависимости от типа функции
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def error_handler(metric: MetricsCollector, handler_name: str):
    """Декоратор для обработки ошибок в обработчиках"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                metric.record_error(e.__class__.__name__, handler_name, e)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                metric.record_error(e.__class__.__name__, handler_name, e)
                raise

        # Возвращаем соответствующий wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
"""
Middleware для обработки команд и проверки прав доступа.
Реализует цепочку middleware: валидация → логирование → авторизация → обработка.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from telegram import Update
from telegram.ext import ContextTypes
from .permissions import permission_manager, UserRole
from .exceptions import PermissionError, ValidationError
from .rate_limiter import rate_limiter, RateLimitExceeded


class MiddlewareContext:
    """
    Контекст выполнения middleware.
    Содержит информацию о текущем запросе и пользователе.
    """

    def __init__(self, update: Update, context: ContextTypes):
        self.update = update
        self.context = context
        self.user_id: Optional[int] = None
        self.user_role: Optional[UserRole] = None
        self.command: Optional[str] = None
        self.args: list = []
        self.metadata: Dict[str, Any] = {}
        self.registration_time: Optional[float] = None  # Время регистрации пользователя

    async def initialize(self, config):
        """Инициализация контекста"""
        # Получаем информацию о пользователе
        if hasattr(self.update, 'effective_user') and self.update.effective_user:
            user = self.update.effective_user
            self.user_id = user.id
            # Используем тот же конфиг, что и в Application
            self.user_role = await permission_manager.get_effective_role(
                self.update, self.user_id, config
            )
            print(f"[DEBUG] MiddlewareContext.initialize: user {self.user_id} role = {self.user_role}, config type: {type(config)}")
            if hasattr(config, 'bot_config'):
                print(f"[DEBUG] Config has super_admin_ids: {config.bot_config.super_admin_ids}")
                print(f"[DEBUG] Config has admin_ids: {config.bot_config.admin_ids}")

            # Получаем время регистрации пользователя из базы данных
            # (предполагаем, что есть метод для получения информации о пользователе)
            try:
                from ..database import get_user_registration_time
                self.registration_time = await get_user_registration_time(self.user_id)
            except Exception:
                # Если не удается получить время регистрации, оставляем None
                self.registration_time = None

        # Парсим команду из сообщения или callback
        if hasattr(self.update, 'message') and self.update.message and hasattr(self.update.message, 'text') and self.update.message.text:
            text = self.update.message.text.strip()
            if text.startswith('/'):
                parts = text.split()
                self.command = parts[0][1:].split('@')[0]  # Убираем слеш и username бота
                self.args = parts[1:] if len(parts) > 1 else []
        elif hasattr(self.update, 'callback_query') and self.update.callback_query and hasattr(self.update.callback_query, 'data') and self.update.callback_query.data:
            # Для callback'ов парсим команду из callback_data
            callback_data = self.update.callback_query.data
            # Если callback_data соответствует команде меню или действия, устанавливаем как команду
            if callback_data.startswith(('menu_', 'donate_')) or callback_data in ['help', 'rank', 'leaderboard', 'info', 'start']:
                self.command = callback_data
                self.args = []


class MiddlewareResult:
    """Результат выполнения middleware"""

    def __init__(self, success: bool = True, error_message: str = None, stop_processing: bool = False):
        self.success = success
        self.error_message = error_message
        self.stop_processing = stop_processing

    @classmethod
    def success(cls):
        """Успешный результат"""
        return cls(success=True)

    @classmethod
    def error(cls, message: str, stop_processing: bool = True):
        """Результат с ошибкой"""
        return cls(success=False, error_message=message, stop_processing=stop_processing)

    @classmethod
    def stop(cls):
        """Остановить обработку без ошибки"""
        return cls(success=True, stop_processing=True)


class BaseMiddleware:
    """
    Базовый класс для middleware.
    """

    async def process(self, context: MiddlewareContext, config) -> MiddlewareResult:
        """
        Обработка запроса в middleware.

        Args:
            context: Контекст middleware
            config: Конфигурация приложения

        Returns:
            Результат обработки
        """
        raise NotImplementedError("Middleware must implement process method")


class ValidationMiddleware(BaseMiddleware):
    """
    Middleware для валидации входящих данных.
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    async def process(self, context: MiddlewareContext, config) -> MiddlewareResult:
        """Валидация данных"""
        try:
            # Проверяем наличие пользователя
            if not context.user_id:
                return MiddlewareResult.error("Не удалось определить пользователя")

            # Проверяем корректность команды
            if context.command:
                # Базовая валидация названия команды
                if not context.command.replace('_', '').isalnum():
                    return MiddlewareResult.error("Неверный формат команды")

                # Проверяем длину аргументов
                for arg in context.args:
                    if len(arg) > 1000:  # Ограничение на длину аргумента
                        return MiddlewareResult.error("Слишком длинный аргумент команды")

            self.logger.debug(f"Validation passed for user {context.user_id}, command: {context.command}")
            return MiddlewareResult.success()

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return MiddlewareResult.error("Ошибка валидации данных")


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования действий пользователей.
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    async def process(self, context: MiddlewareContext, config) -> MiddlewareResult:
        """Логирование действия"""
        try:
            user_info = f"user_{context.user_id}" if context.user_id else "unknown_user"
            command_info = context.command or "unknown_command"
            args_info = f" with {len(context.args)} args" if context.args else ""

            self.logger.info(f"Command executed: {user_info} -> /{command_info}{args_info}")

            # Сохраняем время начала в метаданных
            context.metadata['start_time'] = time.time()

            return MiddlewareResult.success()

        except Exception as e:
            self.logger.error(f"Logging error: {e}")
            return MiddlewareResult.error("Ошибка логирования")


class AuthorizationMiddleware(BaseMiddleware):
    """
    Middleware для проверки прав доступа.
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    async def process(self, context: MiddlewareContext, config) -> MiddlewareResult:
        """Проверка авторизации"""
        try:
            # Если команда не указана, пропускаем проверку (например, для callback'ов)
            if not context.command:
                self.logger.debug(f"Authorization skipped for user {context.user_id} (no command)")
                return MiddlewareResult.success()

            # Проверяем права доступа
            if not permission_manager.can_execute_command(context.user_role, context.command):
                role_name = context.user_role.value if context.user_role else "unknown"
                self.logger.warning(f"Access denied: user {context.user_id} (role: {role_name}) "
                                   f"tried to execute /{context.command}")
                return MiddlewareResult.error("У вас нет прав для выполнения этой команды")

            self.logger.debug(f"Authorization passed for user {context.user_id}, command: {context.command}")
            return MiddlewareResult.success()

        except Exception as e:
            self.logger.error(f"Authorization error: {e}")
            return MiddlewareResult.error("Ошибка проверки прав доступа")


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов (rate limiting).
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    async def process(self, context: MiddlewareContext, config) -> MiddlewareResult:
        """Проверка rate limit"""
        try:
            # Пропускаем проверку для не-команд (сообщения, callback'и)
            if not context.command:
                return MiddlewareResult.success()

            # Проверяем лимит запросов
            allowed, retry_after = await rate_limiter.check_limit(
                context.user_id,
                context.user_role,
                context.registration_time
            )

            if not allowed:
                self.logger.warning(f"Rate limit exceeded for user {context.user_id}, "
                                   f"command: /{context.command}, retry after: {retry_after}s")

                remaining = rate_limiter.get_remaining_requests(
                    context.user_id,
                    context.user_role,
                    context.registration_time
                )

                if retry_after and retry_after > 0:
                    message = (f"🚫 Превышен лимит запросов. "
                              f"Повторите попытку через {retry_after} сек. "
                              f"(Осталось запросов: {remaining})")
                else:
                    message = (f"🚫 Превышен лимит запросов. "
                              f"Попробуйте позже. (Осталось запросов: {remaining})")

                return MiddlewareResult.error(message)

            self.logger.debug(f"Rate limit check passed for user {context.user_id}, command: /{context.command}")
            return MiddlewareResult.success()

        except Exception as e:
            self.logger.error(f"Rate limit check error: {e}")
            # В случае ошибки разрешаем выполнение, чтобы не блокировать пользователей
            return MiddlewareResult.success()


class MetricsMiddleware(BaseMiddleware):
    """
    Middleware для сбора метрик производительности.
    """

    def __init__(self, metrics_collector=None, logger=None):
        self.metrics = metrics_collector
        self.logger = logger or logging.getLogger(__name__)

    async def process(self, context: MiddlewareContext, config) -> MiddlewareResult:
        """Сбор метрик"""
        try:
            # Если есть метрики, собираем их
            if self.metrics and context.command:
                start_time = context.metadata.get('start_time', time.time())
                duration = time.time() - start_time

                # Записываем метрики
                self.metrics.record_command(
                    command=context.command,
                    user_role=context.user_role.value if context.user_role else "unknown",
                    duration=duration
                )

                self.logger.debug(f"Metrics recorded for command /{context.command}: {duration:.3f}s")

            return MiddlewareResult.success()

        except Exception as e:
            self.logger.error(f"Metrics collection error: {e}")
            # Не останавливаем обработку из-за ошибки метрик
            return MiddlewareResult.success()


class MiddlewareChain:
    """
    Цепочка middleware для последовательной обработки запросов.
    """

    def __init__(self, config, metrics=None, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Создаем цепочку middleware
        self.middlewares = [
            ValidationMiddleware(self.logger),
            LoggingMiddleware(self.logger),
            RateLimitMiddleware(self.logger),  # Rate limiting после логирования, но перед авторизацией
            AuthorizationMiddleware(self.logger),
            MetricsMiddleware(metrics, self.logger)
        ]

    async def process_request(self, update: Update, context: ContextTypes,
                            handler: Callable[[Update, ContextTypes], Awaitable]) -> bool:
        """
        Обработка запроса через цепочку middleware.

        Args:
            update: Обновление от Telegram
            context: Контекст бота
            handler: Финальный обработчик

        Returns:
            True если обработка должна продолжиться
        """
        # Создаем контекст middleware
        middleware_context = MiddlewareContext(update, context)
        await middleware_context.initialize(self.config)

        # Выполняем цепочку middleware
        for middleware in self.middlewares:
            try:
                result = await middleware.process(middleware_context, self.config)

                if not result.success:
                    # Отправляем сообщение об ошибке пользователю
                    if result.error_message:
                        await self._send_error_message(update, result.error_message)
                    return False  # Останавливаем обработку

                if result.stop_processing:
                    return False  # Останавливаем обработку без ошибки

            except Exception as e:
                self.logger.error(f"Middleware {middleware.__class__.__name__} failed: {e}")
                await self._send_error_message(update, "Произошла ошибка при обработке запроса")
                return False

        # Если все middleware прошли успешно, выполняем финальный обработчик
        try:
            await handler(update, context)
            return True

        except Exception as e:
            self.logger.error(f"Handler execution failed: {e}")
            await self._send_error_message(update, "Произошла ошибка при выполнении команды")
            return False

    async def _send_error_message(self, update: Update, message: str):
        """Отправка сообщения об ошибке"""
        try:
            if update.message:
                await update.message.reply_text(message)
            elif update.callback_query:
                await update.callback_query.answer(message, show_alert=True)
        except Exception as e:
            if "Query is too old" in str(e) or "timeout expired" in str(e):
                self.logger.warning(f"Не удалось отправить сообщение об ошибке (query устарел): {e}")
            else:
                self.logger.error(f"Failed to send error message: {e}")


# Глобальная функция для создания цепочки middleware
def create_middleware_chain(config, metrics=None):
    """
    Создание цепочки middleware.

    Args:
        config: Конфигурация приложения
        metrics: Сборщик метрик

    Returns:
        MiddlewareChain: Настроенная цепочка middleware
    """
    return MiddlewareChain(config, metrics)
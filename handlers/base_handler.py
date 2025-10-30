"""
Базовый класс для всех обработчиков команд.
Определяет общий интерфейс и предоставляет общие методы.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from core.exceptions import BotException, ValidationError, PermissionError
from utils.formatters import MessageFormatter
from metrics.monitoring import MetricsCollector


class BaseHandler(ABC):
    """
    Абстрактный базовый класс для обработчиков команд.

    Определяет общий интерфейс и предоставляет:
    - Общие методы валидации
    - Обработку ошибок
    - Логирование действий
    - Проверку прав доступа
    """

    def __init__(self, config, metrics: MetricsCollector, message_formatter: MessageFormatter = None):
        """
        Инициализация базового обработчика.

        Args:
            config: Конфигурация приложения
            metrics: Сборщик метрик
            message_formatter: Форматтер сообщений
        """
        self.config = config
        self.metrics = metrics
        self.message_formatter = message_formatter or MessageFormatter()
        self.logger = logging.getLogger(__name__)

    def _ensure_utf8_encoding(self, text: str) -> str:
        """
        Обеспечение корректной UTF-8 кодировки текста для Telegram API.

        Args:
            text: Исходный текст

        Returns:
            Текст с корректной кодировкой
        """
        if isinstance(text, str):
            # Проверяем, что текст корректно закодирован в UTF-8
            try:
                text.encode('utf-8')
                return text
            except UnicodeEncodeError:
                # Если есть проблемы с кодировкой, используем безопасную версию
                return text.encode('utf-8', errors='replace').decode('utf-8')
        return str(text)

    async def safe_execute(self, update: Update, context: ContextTypes, action: str, func, *args, **kwargs):
        """
        Безопасное выполнение действия обработчика с обработкой ошибок.

        Args:
            update: Обновление от Telegram
            context: Контекст бота
            action: Название действия для логирования
            func: Функция для выполнения
            *args, **kwargs: Аргументы функции

        Returns:
            Результат выполнения или None при ошибке
        """
        start_time = time.time()
        try:
            result = await func(update, context, *args, **kwargs)
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_command(action, self.__class__.__name__, duration)
            return result
        except BotException as e:
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_error(e.__class__.__name__, self.__class__.__name__, e)
            await self._handle_bot_exception(update, e)
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Unexpected error in {action}: {e}", exc_info=True)
            if self.metrics:
                self.metrics.record_error(e.__class__.__name__, self.__class__.__name__, e)
            await self._handle_unexpected_error(update, context, action, e)

    async def _handle_bot_exception(self, update: Update, exception: BotException):
        """Обработка известных ошибок бота"""
        error_message = f"❌ {exception.message}"

        if isinstance(exception, ValidationError):
            error_message = f"⚠️ {exception.message}"
        elif isinstance(exception, PermissionError):
            error_message = f"🚫 {exception.message}"

        await self._send_error_message(update, error_message)

    async def _handle_unexpected_error(self, update: Update, context: ContextTypes, action: str, error: Exception):
        """Обработка неожиданных ошибок"""
        # Более детальные сообщения об ошибках для отладки
        if isinstance(error, TypeError) and "can't be used in 'await' expression" in str(error):
            error_message = "Внутренняя ошибка: проблема с асинхронными операциями. Попробуйте позже."
        elif isinstance(error, Exception) and "FOREIGN KEY" in str(error):
            error_message = "Ошибка базы данных: нарушение целостности данных."
        elif isinstance(error, Exception) and "database is locked" in str(error):
            error_message = "База данных временно недоступна. Попробуйте позже."
        else:
            error_message = "Произошла неожиданная ошибка. Попробуйте позже."

        # Логируем ошибку для администраторов
        await self._log_error_to_admin(context, action, error)

        await self._send_error_message(update, error_message)

    async def send_response(self, update: Update, text: str, parse_mode: str = None, reply_markup=None):
        """
        Унифицированная отправка ответов пользователю.

        Args:
            update: Обновление от Telegram
            text: Текст сообщения
            parse_mode: Режим разметки ('HTML', 'Markdown', etc.)
            reply_markup: Клавиатура для сообщения
        """
        try:
            # Обеспечиваем корректную UTF-8 кодировку
            safe_text = self._ensure_utf8_encoding(text)

            # Определяем способ отправки на основе типа обновления
            if update.message:
                # Отправка нового сообщения
                await update.message.reply_text(
                    safe_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
            elif update.callback_query:
                # Редактирование существующего сообщения
                try:
                    await update.callback_query.edit_message_text(
                        safe_text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
                except Exception as edit_error:
                    # Если редактирование невозможно, отправляем новое сообщение
                    self.logger.warning(f"Не удалось отредактировать сообщение: {edit_error}")
                    if update.callback_query.message:
                        await update.callback_query.message.reply_text(
                            safe_text,
                            parse_mode=parse_mode,
                            reply_markup=reply_markup
                        )
            else:
                # Fallback: отправка в чат
                if update.effective_chat:
                    await update.effective_chat.send_message(
                        safe_text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
                else:
                    self.logger.error("Не удалось определить способ отправки сообщения")

        except Exception as e:
            if "TimedOut" in str(type(e)) or "timeout" in str(e).lower():
                self.logger.warning(f"Timeout при отправке сообщения, пропускаем: {e}")
                return  # Не переотправляем при таймаутах
            elif "Query is too old" in str(e):
                self.logger.warning(f"Query устарел, пропускаем: {e}")
                return  # Не пытаемся отвечать на устаревшие queries
            elif "Message is not modified" in str(e):
                self.logger.warning(f"Сообщение не изменилось, пропускаем: {e}")
                return  # Игнорируем попытки редактирования неизменившихся сообщений
            else:
                self.logger.error(f"Не удалось отправить сообщение: {e}", exc_info=True)

    async def _send_error_message(self, update: Update, message: str):
        """Отправка сообщения об ошибке пользователю"""
        await self.send_response(update, message)

    async def _log_error_to_admin(self, context: ContextTypes, action: str, error: Exception):
        """Логирование ошибки администраторам"""
        try:
            if self.config.bot_config.enable_developer_notifications:
                developer_id = self.config.bot_config.developer_chat_id
                if developer_id:
                    from datetime import datetime
                    error_text = (
                        "🚨 Ошибка в обработчике\n\n"
                        f"Действие: {action}\n"
                        f"Ошибка: {str(error)}\n"
                        f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    # Обеспечиваем корректную UTF-8 кодировку
                    safe_error_text = self._ensure_utf8_encoding(error_text)
                    await context.bot.send_message(
                        chat_id=developer_id,
                        text=safe_error_text
                    )
        except Exception as e:
            self.logger.error(f"Не удалось отправить ошибку разработчику: '{e}'", exc_info=True)

    def validate_user_id(self, user_id: str) -> int:
        """
        Валидация и преобразование ID пользователя.

        Args:
            user_id: Строка с ID пользователя

        Returns:
            Целое число ID

        Raises:
            ValidationError: Если ID некорректен
        """
        try:
            uid = int(user_id)
            if not (1 <= uid <= 2147483647):
                raise ValidationError("Неверный диапазон ID пользователя")
            return uid
        except ValueError:
            raise ValidationError("ID пользователя должен быть числом")

    def validate_chat_id(self, chat_id: str) -> int:
        """
        Валидация и преобразование ID чата.

        Args:
            chat_id: Строка с ID чата

        Returns:
            Целое число ID

        Raises:
            ValidationError: Если ID некорректен
        """
        try:
            cid = int(chat_id)
            if not (-2147483648 <= cid <= 2147483647):
                raise ValidationError("Неверный диапазон ID чата")
            return cid
        except ValueError:
            raise ValidationError("ID чата должен быть числом")

    async def is_admin(self, update: Update, user_id: int) -> bool:
        """
        Проверка прав администратора через PermissionManager.

        Args:
            update: Обновление от Telegram
            user_id: ID пользователя

        Returns:
            True если пользователь администратор или супер-администратор
        """
        from core.permissions import permission_manager, UserRole

        # Получаем эффективную роль пользователя
        effective_role = await permission_manager.get_effective_role(update, user_id, self.config)

        # Проверяем, является ли роль административной
        return effective_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]

    async def require_admin(self, update: Update, user_id: int):
        """
        Проверка прав администратора с генерацией исключения.

        Args:
            update: Обновление от Telegram
            user_id: ID пользователя

        Raises:
            PermissionError: Если пользователь не администратор
        """
        if not await self.is_admin(update, user_id):
            raise PermissionError("Эта команда доступна только администраторам")

    def extract_user_id_from_args(self, args: list) -> Optional[int]:
        """
        Извлечение ID пользователя из аргументов команды.

        Args:
            args: Список аргументов команды

        Returns:
            ID пользователя или None
        """
        if not args:
            return None

        try:
            return self.validate_user_id(args[0])
        except ValidationError:
            return None

    def extract_amount_from_args(self, args: list, default: float = None) -> Optional[float]:
        """
        Извлечение суммы из аргументов команды.

        Args:
            args: Список аргументов команды
            default: Значение по умолчанию

        Returns:
            Сумма или None
        """
        if not args:
            return default

        try:
            amount = float(args[0])
            if amount <= 0:
                return None
            return amount
        except (ValueError, IndexError):
            return None

    def format_user_mention(self, user_id: int, name: str) -> str:
        """
        Форматирование упоминания пользователя.

        Args:
            user_id: ID пользователя
            name: Имя пользователя

        Returns:
            Отформатированная строка упоминания
        """
        return f"[{name}](tg://user?id={user_id})"

    @abstractmethod
    def get_command_handlers(self) -> Dict[str, callable]:
        """
        Получение словаря обработчиков команд.

        Returns:
            Словарь {команда: функция_обработчик}
        """
        pass

    @abstractmethod
    def get_callback_handlers(self) -> Dict[str, callable]:
        """
        Получение словаря обработчиков callback запросов.

        Returns:
            Словарь {callback_data: функция_обработчик}
        """
        pass

    @abstractmethod
    def get_message_handlers(self) -> Dict[str, callable]:
        """
        Получение словаря обработчиков сообщений.

        Returns:
            Словарь {тип_сообщения: функция_обработчик}
        """
        pass
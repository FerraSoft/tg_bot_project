"""
Сервис для отправки уведомлений пользователям о платежах.
"""

import logging
import asyncio
import time
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import TelegramError, NetworkError, TimedOut, RetryAfter


class NotificationService:
    """
    Сервис для отправки уведомлений пользователям.

    Отвечает за:
    - Уведомления об успешных платежах
    - Уведомления о неудачных платежах
    - Уведомления администраторам о проблемах
    """

    def __init__(self, bot_token: str, admin_chat_ids: Optional[list] = None):
        """
        Инициализация сервиса уведомлений.

        Args:
            bot_token: Токен Telegram бота
            admin_chat_ids: Список ID чатов администраторов
        """
        self.bot = Bot(token=bot_token)
        self.admin_chat_ids = admin_chat_ids or []
        self.logger = logging.getLogger(__name__)

        # Статистика отправки уведомлений
        self.stats = {
            'successful_sends': 0,
            'failed_sends': 0,
            'network_errors': 0,
            'timeout_errors': 0,
            'rate_limit_errors': 0,
            'other_errors': 0
        }

        # Настройки повторных попыток
        self.max_retries = 3
        self.base_retry_delay = 1.0  # секунды
        self.max_retry_delay = 30.0  # секунды

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # минимум 100ms между запросами

    async def notify_payment_success(self, user_id: int, amount: float, currency: str = "RUB"):
        """
        Уведомление об успешном платеже.

        Args:
            user_id: ID пользователя
            amount: Сумма платежа
            currency: Валюта
        """
        try:
            message = (
                f"✅ <b>Спасибо за донат!</b>\n\n"
                f"💰 Сумма: <code>{amount:.2f} {currency}</code>\n"
                f"🎯 Средства успешно зачислены на ваш счет!\n\n"
                f"Вы помогаете развитию проекта и получаете бонусные очки за поддержку. "
                f"Посмотреть свою статистику можно командой /rank"
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )

            self.logger.info(f"Sent success notification to user {user_id} for amount {amount}")

        except TelegramError as e:
            self.logger.error(f"Failed to send success notification to user {user_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending success notification: {e}")

    async def notify_payment_failed(self, user_id: int, reason: str = "Неизвестная ошибка"):
        """
        Уведомление о неудачном платеже.

        Args:
            user_id: ID пользователя
            reason: Причина неудачи
        """
        try:
            message = (
                f"❌ <b>Платеж не прошел</b>\n\n"
                f"💡 Причина: <code>{reason}</code>\n\n"
                f"Попробуйте еще раз или обратитесь в поддержку, "
                f"если проблема сохраняется."
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )

            self.logger.info(f"Sent failure notification to user {user_id}: {reason}")

        except TelegramError as e:
            self.logger.error(f"Failed to send failure notification to user {user_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending failure notification: {e}")

    async def notify_payment_cancelled(self, user_id: int):
        """
        Уведомление об отмене платежа.

        Args:
            user_id: ID пользователя
        """
        try:
            message = (
                f"🚫 <b>Платеж отменен</b>\n\n"
                f"Если это было сделано по ошибке, попробуйте создать новый платеж."
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )

            self.logger.info(f"Sent cancellation notification to user {user_id}")

        except TelegramError as e:
            self.logger.error(f"Failed to send cancellation notification to user {user_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending cancellation notification: {e}")

    async def notify_payment_pending(self, user_id: int, payment_url: str, amount: float):
        """
        Уведомление о том, что платеж находится в обработке.

        Args:
            user_id: ID пользователя
            payment_url: URL для оплаты
            amount: Сумма платежа
        """
        try:
            message = (
                f"⏳ <b>Платеж в обработке</b>\n\n"
                f"💰 Сумма: <code>{amount:.2f} RUB</code>\n"
                f"🔗 <a href=\"{payment_url}\">Завершить оплату</a>\n\n"
                f"Пожалуйста, завершите оплату по ссылке выше."
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            self.logger.info(f"Sent pending notification to user {user_id}")

        except TelegramError as e:
            self.logger.error(f"Failed to send pending notification to user {user_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending pending notification: {e}")

    async def notify_admin_payment_issue(self, payment_id: str, error: str, user_id: Optional[int] = None):
        """
        Уведомление администраторов о проблеме с платежом.

        Args:
            payment_id: ID платежа
            error: Описание проблемы
            user_id: ID пользователя (опционально)
        """
        try:
            user_info = f" (Пользователь: {user_id})" if user_id else ""
            message = (
                f"🚨 <b>Проблема с платежом</b>\n\n"
                f"🆔 ID платежа: <code>{payment_id}</code>{user_info}\n"
                f"❌ Ошибка: <code>{error}</code>\n\n"
                f"Требуется ручная проверка."
            )

            for admin_chat_id in self.admin_chat_ids:
                try:
                    await self.bot.send_message(
                        chat_id=admin_chat_id,
                        text=message,
                        parse_mode='HTML'
                    )
                except TelegramError as e:
                    self.logger.error(f"Failed to send admin notification to {admin_chat_id}: {e}")

            self.logger.warning(f"Sent admin notification for payment {payment_id}: {error}")

        except Exception as e:
            self.logger.error(f"Unexpected error sending admin notification: {e}")

    async def notify_admin_system_error(self, error_type: str, error_message: str, details: Optional[str] = None):
        """
        Уведомление администраторов о системной ошибке.

        Args:
            error_type: Тип ошибки
            error_message: Сообщение об ошибке
            details: Дополнительные детали
        """
        try:
            message = (
                f"🔥 <b>Системная ошибка платежей</b>\n\n"
                f"⚠️ Тип: <code>{error_type}</code>\n"
                f"📝 Ошибка: <code>{error_message}</code>\n"
            )

            if details:
                message += f"📋 Детали: <code>{details[:500]}</code>\n\n"

            message += "Требуется немедленное вмешательство!"

            for admin_chat_id in self.admin_chat_ids:
                try:
                    await self.bot.send_message(
                        chat_id=admin_chat_id,
                        text=message,
                        parse_mode='HTML'
                    )
                except TelegramError as e:
                    self.logger.error(f"Failed to send system error notification to {admin_chat_id}: {e}")

            self.logger.critical(f"Sent system error notification: {error_type} - {error_message}")

        except Exception as e:
            self.logger.error(f"Unexpected error sending system error notification: {e}")

    async def notify_admin_payment_stats(self, stats: dict):
        """
        Уведомление администраторов о статистике платежей.

        Args:
            stats: Статистика платежей
        """
        try:
            message = (
                f"📊 <b>Статистика платежей</b>\n\n"
                f"💰 Всего платежей: <code>{stats.get('total_payments', 0)}</code>\n"
                f"✅ Успешных: <code>{stats.get('successful_payments', 0)}</code>\n"
                f"❌ Неудачных: <code>{stats.get('failed_payments', 0)}</code>\n"
                f"⏳ Ожидающих: <code>{stats.get('pending_payments', 0)}</code>\n"
                f"📈 Общая сумма: <code>{stats.get('total_amount', 0):.2f} RUB</code>\n"
            )

            for admin_chat_id in self.admin_chat_ids:
                try:
                    await self.bot.send_message(
                        chat_id=admin_chat_id,
                        text=message,
                        parse_mode='HTML'
                    )
                except TelegramError as e:
                    self.logger.error(f"Failed to send stats notification to {admin_chat_id}: {e}")

            self.logger.info("Sent payment statistics notification to admins")

        except Exception as e:
            self.logger.error(f"Unexpected error sending stats notification: {e}")

    async def send_custom_notification(self, user_id: int, message: str, parse_mode: str = 'HTML'):
        """
        Отправка произвольного уведомления пользователю.

        Args:
            user_id: ID пользователя
            message: Текст сообщения
            parse_mode: Режим парсинга ('HTML', 'Markdown', None)
        """
        await self._send_with_retry(user_id, message, parse_mode)

    async def _send_with_retry(self, user_id: int, message: str, parse_mode: str = 'HTML', attempt: int = 1):
        """
        Отправка сообщения с механизмом повторных попыток и rate limiting.

        Args:
            user_id: ID пользователя
            message: Текст сообщения
            parse_mode: Режим парсинга
            attempt: Номер текущей попытки
        """
        # Rate limiting
        await self._apply_rate_limit()

        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode if parse_mode != 'HTML' else None,
                disable_web_page_preview=True
            )

            self.stats['successful_sends'] += 1
            self.logger.info(f"Sent notification to user {user_id} (attempt {attempt})")

        except RetryAfter as e:
            # Rate limit от Telegram API
            self.stats['rate_limit_errors'] += 1
            self.logger.warning(f"Rate limit hit for user {user_id}, retry after {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            await self._send_with_retry(user_id, message, parse_mode, attempt)

        except TimedOut as e:
            # Таймаут сети
            self.stats['timeout_errors'] += 1
            self.logger.warning(f"Timeout sending notification to user {user_id} (attempt {attempt})")
            await self._handle_retry(user_id, message, parse_mode, attempt, "timeout")

        except NetworkError as e:
            # Сетевая ошибка
            self.stats['network_errors'] += 1
            self.logger.warning(f"Network error sending notification to user {user_id} (attempt {attempt}): {e}")
            await self._handle_retry(user_id, message, parse_mode, attempt, "network")

        except TelegramError as e:
            # Другие ошибки Telegram
            self.stats['other_errors'] += 1
            self.logger.error(f"Telegram error sending notification to user {user_id} (attempt {attempt}): {e}")
            self.stats['failed_sends'] += 1

        except Exception as e:
            # Неожиданные ошибки
            self.stats['other_errors'] += 1
            self.logger.error(f"Unexpected error sending notification to user {user_id} (attempt {attempt}): {e}")
            self.stats['failed_sends'] += 1

    async def _apply_rate_limit(self):
        """Применение rate limiting между запросами."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)

        self.last_request_time = time.time()

    async def _handle_retry(self, user_id: int, message: str, parse_mode: str, attempt: int, error_type: str):
        """
        Обработка повторных попыток отправки.

        Args:
            user_id: ID пользователя
            message: Текст сообщения
            parse_mode: Режим парсинга
            attempt: Текущий номер попытки
            error_type: Тип ошибки
        """
        if attempt >= self.max_retries:
            self.stats['failed_sends'] += 1
            self.logger.error(f"Max retries ({self.max_retries}) exceeded for user {user_id}, giving up")
            return

        # Экспоненциальная задержка
        delay = min(self.base_retry_delay * (2 ** (attempt - 1)), self.max_retry_delay)
        self.logger.info(f"Retrying notification to user {user_id} in {delay}s (attempt {attempt + 1}/{self.max_retries})")
        await asyncio.sleep(delay)

        await self._send_with_retry(user_id, message, parse_mode, attempt + 1)

    def get_notification_stats(self) -> Dict[str, Any]:
        """
        Получение статистики отправки уведомлений.

        Returns:
            Dict с статистикой отправки
        """
        total_attempts = (
            self.stats['successful_sends'] +
            self.stats['failed_sends'] +
            self.stats['network_errors'] +
            self.stats['timeout_errors'] +
            self.stats['rate_limit_errors'] +
            self.stats['other_errors']
        )

        return {
            **self.stats,
            'total_attempts': total_attempts,
            'success_rate': (self.stats['successful_sends'] / total_attempts * 100) if total_attempts > 0 else 0.0
        }

    def reset_stats(self):
        """Сброс статистики отправки уведомлений."""
        self.stats = {
            'successful_sends': 0,
            'failed_sends': 0,
            'network_errors': 0,
            'timeout_errors': 0,
            'rate_limit_errors': 0,
            'other_errors': 0
        }
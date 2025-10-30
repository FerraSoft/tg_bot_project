"""
Обработчики для платежных операций и webhook уведомлений.
"""

import json
import logging
from typing import Dict, Any, Optional
from flask import Request, jsonify, Response
from telegram import Update
from telegram.ext import ContextTypes

from services.donation_service import DonationService
from core.payment_exceptions import PaymentError, PaymentSecurityError, PaymentProviderError


class PaymentHandler:
    """
    Обработчик платежных операций для Telegram бота.

    Отвечает за:
    - Создание платежей через команды бота
    - Обработку webhook уведомлений от платежных провайдеров
    - Управление статусом платежей
    """

    def __init__(self, donation_service: DonationService):
        """
        Инициализация обработчика платежей.

        Args:
            donation_service: Сервис для обработки донатов
        """
        self.donation_service = donation_service
        self.logger = logging.getLogger(__name__)

    async def handle_donate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка команды /donate.

        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        try:
            user = update.effective_user
            args = context.args or []

            if not args:
                await self._show_donation_menu(update)
                return

            # Парсинг суммы
            try:
                amount = float(args[0])
            except (ValueError, IndexError):
                await update.message.reply_text(
                    "❌ Неверный формат суммы. Используйте: /donate 100"
                )
                return

            # Определение провайдера (по умолчанию stripe)
            provider = args[1] if len(args) > 1 else 'stripe'

            # Создание доната
            donation_response = await self.donation_service.create_donation(
                user_id=user.id,
                amount=amount,
                provider_name=provider
            )

            # Формирование сообщения с платежной ссылкой
            message = (
                f"💰 <b>Донат {amount:.2f} ₽</b>\n\n"
                f"🔗 <a href=\"{donation_response.payment_url}\">Оплатить</a>\n\n"
                f"После оплаты средства будут автоматически зачислены на ваш счет."
            )

            await update.message.reply_html(
                message,
                disable_web_page_preview=True
            )

        except PaymentError as e:
            self.logger.warning(f"Payment error for user {user.id}: {e}")
            await update.message.reply_text(f"❌ Ошибка платежа: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in donate command: {e}", exc_info=True)
            await update.message.reply_text("❌ Произошла неожиданная ошибка. Попробуйте позже.")

    async def handle_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка команды /payment_status <payment_id>.

        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        try:
            user = update.effective_user
            args = context.args or []

            if not args:
                await update.message.reply_text(
                    "❌ Укажите ID платежа: /payment_status 123"
                )
                return

            try:
                payment_id = int(args[0])
            except ValueError:
                await update.message.reply_text("❌ Неверный ID платежа")
                return

            # Получение статуса платежа
            payment = self.donation_service.get_payment_status(payment_id)

            if not payment:
                await update.message.reply_text("❌ Платеж не найден")
                return

            # Проверка прав доступа
            if payment['user_id'] != user.id:
                await update.message.reply_text("❌ Доступ запрещен")
                return

            # Формирование сообщения о статусе
            status_emoji = {
                'pending': '⏳',
                'processing': '🔄',
                'succeeded': '✅',
                'failed': '❌',
                'cancelled': '🚫',
                'refunded': '↩️'
            }

            message = (
                f"{status_emoji.get(payment['status'], '❓')} <b>Статус платежа #{payment_id}</b>\n\n"
                f"💰 Сумма: {payment['amount']:.2f} {payment['currency']}\n"
                f"🔧 Провайдер: {payment['provider']}\n"
                f"📅 Создан: {payment['created_at'][:19]}\n"
                f"📊 Статус: <code>{payment['status']}</code>\n"
            )

            if payment.get('processed_at'):
                message += f"✅ Обработан: {payment['processed_at'][:19]}\n"

            if payment.get('error_message'):
                message += f"❌ Ошибка: {payment['error_message']}\n"

            await update.message.reply_html(message)

        except Exception as e:
            self.logger.error(f"Error in payment status command: {e}", exc_info=True)
            await update.message.reply_text("❌ Ошибка при получении статуса платежа")

    async def handle_my_payments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка команды /my_payments.

        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        try:
            user = update.effective_user

            # Получение платежей пользователя
            payments = self.donation_service.get_user_payments(user.id, limit=10)

            if not payments:
                await update.message.reply_text("📭 У вас пока нет платежей")
                return

            # Формирование списка платежей
            message = "<b>💳 Ваши платежи</b>\n\n"

            for payment in payments:
                status_emoji = {
                    'pending': '⏳',
                    'processing': '🔄',
                    'succeeded': '✅',
                    'failed': '❌',
                    'cancelled': '🚫',
                    'refunded': '↩️'
                }

                message += (
                    f"{status_emoji.get(payment['status'], '❓')} #{payment['id']} - "
                    f"{payment['amount']:.2f} {payment['currency']} "
                    f"({payment['created_at'][:10]}) - <code>{payment['status']}</code>\n"
                )

            message += "\nДля детальной информации: /payment_status <ID>"

            await update.message.reply_html(message)

        except Exception as e:
            self.logger.error(f"Error in my payments command: {e}", exc_info=True)
            await update.message.reply_text("❌ Ошибка при получении списка платежей")

    async def handle_cancel_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка команды /cancel_payment <payment_id>.

        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        try:
            user = update.effective_user
            args = context.args or []

            if not args:
                await update.message.reply_text(
                    "❌ Укажите ID платежа: /cancel_payment 123"
                )
                return

            try:
                payment_id = int(args[0])
            except ValueError:
                await update.message.reply_text("❌ Неверный ID платежа")
                return

            # Попытка отмены платежа
            success = self.donation_service.cancel_payment(payment_id, user.id)

            if success:
                await update.message.reply_text("✅ Платеж успешно отменен")
            else:
                await update.message.reply_text("❌ Невозможно отменить платеж (уже обработан или не найден)")

        except Exception as e:
            self.logger.error(f"Error in cancel payment command: {e}", exc_info=True)
            await update.message.reply_text("❌ Ошибка при отмене платежа")

    async def _show_donation_menu(self, update: Update) -> None:
        """
        Показать меню донатов.

        Args:
            update: Объект обновления Telegram
        """
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = [
            [
                InlineKeyboardButton("💰 100 ₽", callback_data="donate_100"),
                InlineKeyboardButton("💎 500 ₽", callback_data="donate_500"),
            ],
            [
                InlineKeyboardButton("🏆 1000 ₽", callback_data="donate_1000"),
                InlineKeyboardButton("👑 2500 ₽", callback_data="donate_2500"),
            ],
            [
                InlineKeyboardButton("🎯 Другая сумма", callback_data="donate_custom"),
            ]
        ]

        message = (
            "🎁 <b>Поддержать проект</b>\n\n"
            "Выберите сумму доната или введите свою:\n"
            "<code>/donate 500</code>\n\n"
            "После оплаты вы получите бонусные очки и поможете развитию проекта! 🚀"
        )

        await update.message.reply_html(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


class WebhookHandler:
    """
    Обработчик webhook уведомлений от платежных провайдеров.
    """

    def __init__(self, donation_service: DonationService):
        """
        Инициализация обработчика webhook.

        Args:
            donation_service: Сервис для обработки донатов
        """
        self.donation_service = donation_service
        self.logger = logging.getLogger(__name__)

    async def handle_stripe_webhook(self, request: Request) -> Response:
        """
        Обработка webhook от Stripe.

        Args:
            request: HTTP запрос

        Returns:
            Response: HTTP ответ
        """
        try:
            # Получение тела запроса и подписи
            payload = await request.get_data()
            signature = request.headers.get('Stripe-Signature', '')

            # Парсинг JSON
            try:
                webhook_data = json.loads(payload)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON'}), 400

            # Обработка webhook через donation service
            await self.donation_service.process_payment_webhook(
                provider_name='stripe',
                webhook_data=webhook_data,
                signature=signature
            )

            return jsonify({'status': 'ok'}), 200

        except PaymentSecurityError:
            self.logger.warning("Invalid Stripe webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
        except PaymentProviderError as e:
            self.logger.error(f"Stripe webhook processing error: {e}")
            return jsonify({'error': 'Processing error'}), 500
        except Exception as e:
            self.logger.error(f"Unexpected error in Stripe webhook: {e}", exc_info=True)
            return jsonify({'error': 'Internal error'}), 500

    async def handle_yookassa_webhook(self, request: Request) -> Response:
        """
        Обработка webhook от YooKassa.

        Args:
            request: HTTP запрос

        Returns:
            Response: HTTP ответ
        """
        try:
            # Получение тела запроса и подписи
            payload = await request.get_data()
            signature = request.headers.get('Authorization', '')

            # Парсинг JSON
            try:
                webhook_data = json.loads(payload)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON'}), 400

            # Обработка webhook через donation service
            await self.donation_service.process_payment_webhook(
                provider_name='yookassa',
                webhook_data=webhook_data,
                signature=signature
            )

            return jsonify({'status': 'ok'}), 200

        except PaymentSecurityError:
            self.logger.warning("Invalid YooKassa webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
        except PaymentProviderError as e:
            self.logger.error(f"YooKassa webhook processing error: {e}")
            return jsonify({'error': 'Processing error'}), 500
        except Exception as e:
            self.logger.error(f"Unexpected error in YooKassa webhook: {e}", exc_info=True)
            return jsonify({'error': 'Internal error'}), 500

    async def handle_sbp_webhook(self, request: Request) -> Response:
        """
        Обработка webhook от СБП.

        Args:
            request: HTTP запрос

        Returns:
            Response: HTTP ответ
        """
        try:
            # Получение тела запроса и подписи
            payload = await request.get_data()
            signature = request.headers.get('X-SBP-Signature', '')

            # Парсинг JSON
            try:
                webhook_data = json.loads(payload)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON'}), 400

            # Обработка webhook через donation service
            await self.donation_service.process_payment_webhook(
                provider_name='sbp',
                webhook_data=webhook_data,
                signature=signature
            )

            return jsonify({'status': 'ok'}), 200

        except PaymentSecurityError:
            self.logger.warning("Invalid SBP webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
        except PaymentProviderError as e:
            self.logger.error(f"SBP webhook processing error: {e}")
            return jsonify({'error': 'Processing error'}), 500
        except Exception as e:
            self.logger.error(f"Unexpected error in SBP webhook: {e}", exc_info=True)
            return jsonify({'error': 'Internal error'}), 500
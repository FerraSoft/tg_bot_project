"""
Сервис для обработки донатов через различные платежные системы.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from core.payment_models import (
    PaymentIntent, PaymentEvent, PaymentStatus, TransactionType,
    DonationResponse, PaymentValidationResult
)
from core.payment_exceptions import (
    PaymentError, PaymentProviderError, PaymentValidationError,
    PaymentSecurityError, PaymentDuplicateError, PaymentNotFoundError
)
from services.payment_provider import (
    PaymentProvider, StripePaymentProvider, YooKassaPaymentProvider, SBPaymentProvider
)
from database.payment_repository import PaymentRepository, TransactionRepository
from services.user_service import UserService
from services.notification_service import NotificationService


@dataclass
class PaymentConfig:
    """Конфигурация платежного провайдера"""
    enabled: bool
    api_key: Optional[str] = None
    webhook_secret: Optional[str] = None
    shop_id: Optional[str] = None
    secret_key: Optional[str] = None
    bank_id: Optional[str] = None


class DonationService:
    """
    Основной сервис для обработки донатов.

    Отвечает за:
    - Создание платежей через различные провайдеры
    - Валидацию платежных данных
    - Обработку webhook уведомлений
    - Управление статусами платежей
    - Интеграцию с пользователями и уведомлениями
    """

    def __init__(self, payment_repo: PaymentRepository,
                 transaction_repo: TransactionRepository,
                 user_service: UserService,
                 notification_service: NotificationService,
                 payment_configs: Dict[str, PaymentConfig]):
        """
        Инициализация сервиса донатов.

        Args:
            payment_repo: Репозиторий платежей
            transaction_repo: Репозиторий транзакций
            user_service: Сервис пользователей
            notification_service: Сервис уведомлений
            payment_configs: Конфигурации платежных провайдеров
        """
        self.payment_repo = payment_repo
        self.transaction_repo = transaction_repo
        self.user_service = user_service
        self.notification_service = notification_service
        self.payment_configs = payment_configs

        self.logger = logging.getLogger(__name__)

        # Инициализация провайдеров
        self.providers: Dict[str, PaymentProvider] = {}
        self._initialize_providers()

        # Инициализация rate limiter для защиты от злоупотреблений
        from core.payment_security import PaymentRateLimiter
        self.rate_limiter = PaymentRateLimiter(
            max_payments_per_hour=10,  # Максимум 10 платежей в час на пользователя
            max_amount_per_hour=50000.0  # Максимум 50000 руб в час
        )

        # Настройки валидации
        self.min_amount = 10.0
        self.max_amount = 10000.0
        self.allowed_currencies = ['RUB', 'USD', 'EUR']

        # Настройки безопасности
        self.duplicate_check_window_minutes = 30

    def _initialize_providers(self):
        """Инициализация платежных провайдеров"""
        # Stripe
        stripe_config = self.payment_configs.get('stripe')
        if stripe_config and stripe_config.enabled:
            self.providers['stripe'] = StripePaymentProvider(
                api_key=stripe_config.api_key,
                webhook_secret=stripe_config.webhook_secret
            )

        # YooKassa
        yookassa_config = self.payment_configs.get('yookassa')
        if yookassa_config and yookassa_config.enabled:
            self.providers['yookassa'] = YooKassaPaymentProvider(
                shop_id=yookassa_config.shop_id,
                secret_key=yookassa_config.secret_key
            )

        # СБП (заглушка)
        sbp_config = self.payment_configs.get('sbp')
        if sbp_config and sbp_config.enabled:
            self.providers['sbp'] = SBPaymentProvider(
                api_key=sbp_config.api_key,
                bank_id=sbp_config.bank_id,
                webhook_secret=sbp_config.webhook_secret
            )

    async def create_donation(self, user_id: int, amount: float,
                            provider_name: str = 'stripe',
                            metadata: Optional[Dict[str, Any]] = None) -> DonationResponse:
        """
        Создание доната.

        Args:
            user_id: ID пользователя
            amount: Сумма доната
            provider_name: Название провайдера
            metadata: Дополнительные данные

        Returns:
            DonationResponse: Ответ с URL оплаты и ID платежа

        Raises:
            PaymentValidationError: Ошибка валидации
            PaymentProviderError: Ошибка провайдера
        """
        try:
            self.logger.info(f"Creating donation: user_id={user_id}, amount={amount}, provider={provider_name}")

            # Валидация входных данных
            validation_result = self._validate_donation_data(user_id, amount, provider_name)
            if not validation_result.is_valid:
                raise PaymentValidationError(f"Validation failed: {', '.join(validation_result.errors)}")

            # Проверка rate limit
            rate_limit_result = self.rate_limiter.check_rate_limit(user_id, amount)
            if not rate_limit_result['allowed']:
                raise PaymentValidationError(
                    f"Rate limit exceeded. Try again after {rate_limit_result['reset_time']}"
                )

            # Проверка на дубликаты
            if self._check_duplicate_donation(user_id, amount):
                raise PaymentDuplicateError("Duplicate donation detected")

            # Получение провайдера
            provider = self._get_provider(provider_name)

            # Подготовка метаданных
            if metadata is None:
                metadata = {}
            metadata.update({
                'user_id': str(user_id),
                'created_at': datetime.now().isoformat(),
                'service': 'telegram_bot_donation'
            })

            # Создание платежа через провайдера
            payment_intent = provider.create_payment(amount, 'RUB', user_id, metadata)

            # Сохранение платежа в БД
            payment_record = self.payment_repo.create_payment({
                'user_id': user_id,
                'amount': amount,
                'currency': 'RUB',
                'provider': provider_name,
                'external_id': payment_intent.id,
                'status': 'pending',
                'metadata': metadata,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })

            self.logger.info(f"Donation created: payment_id={payment_record['id']}, external_id={payment_intent.id}")

            # Создание транзакции
            self.transaction_repo.create_transaction({
                'payment_id': payment_record['id'],
                'type': 'payment',
                'amount': amount,
                'status': 'pending',
                'created_at': datetime.now()
            })

            # Регистрация платежа в rate limiter для учета лимитов
            self.rate_limiter.record_payment(user_id, amount)

            return DonationResponse(
                payment_url=payment_intent.url,
                payment_id=payment_record['id'],
                provider=provider_name,
                amount=amount,
                currency='RUB'
            )

        except (PaymentValidationError, PaymentDuplicateError, PaymentProviderError):
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error creating donation: {e}", exc_info=True)
            raise PaymentError(f"Failed to create donation: {e}")

    async def process_payment_webhook(self, provider_name: str, webhook_data: Dict[str, Any],
                                    signature: str) -> bool:
        """
        Обработка webhook уведомления от платежного провайдера.

        Args:
            provider_name: Название провайдера
            webhook_data: Данные webhook
            signature: Подпись для валидации

        Returns:
            bool: Успешно ли обработано

        Raises:
            PaymentSecurityError: Ошибка безопасности
            PaymentProviderError: Ошибка провайдера
        """
        try:
            self.logger.info(f"Processing webhook: provider={provider_name}")

            # Получение провайдера
            provider = self._get_provider(provider_name)

            # Валидация подписи
            if not provider.validate_webhook(webhook_data, signature):
                raise PaymentSecurityError("Invalid webhook signature")

            # Обработка события платежа
            payment_event = provider.process_webhook(webhook_data)

            # Обработка события
            await self._handle_payment_event(payment_event)

            return True

        except (PaymentSecurityError, PaymentProviderError):
            raise
        except Exception as e:
            self.logger.error(f"Error processing webhook: {e}", exc_info=True)
            raise PaymentProviderError(f"Webhook processing failed: {e}")

    async def _handle_payment_event(self, event: PaymentEvent):
        """
        Обработка события платежа.

        Args:
            event: Событие платежа
        """
        try:
            self.logger.info(f"Handling payment event: {event.type} for payment {event.payment_id}")

            # Определение типа события
            if event.type == 'payment.succeeded':
                await self._process_successful_payment(event)
            elif event.type == 'payment.failed':
                await self._process_failed_payment(event)
            elif event.type == 'payment.cancelled':
                await self._process_cancelled_payment(event)
            elif event.type == 'payment.pending':
                await self._process_pending_payment(event)
            else:
                self.logger.warning(f"Unknown payment event type: {event.type}")

        except Exception as e:
            self.logger.error(f"Error handling payment event: {e}", exc_info=True)
            # Не прерываем обработку, логируем ошибку

    async def _process_successful_payment(self, event: PaymentEvent):
        """Обработка успешного платежа"""
        try:
            # Обновление статуса платежа
            success = self.payment_repo.update_payment_status_by_external_id(
                event.payment_id, 'succeeded',
                processed_at=datetime.now()
            )

            if not success:
                self.logger.error(f"Failed to update payment status for {event.payment_id}")
                return

            # Получение данных платежа
            payment = self.payment_repo.get_payment_by_external_id(event.payment_id)
            if not payment:
                self.logger.error(f"Payment not found: {event.payment_id}")
                return

            # Обновление баланса пользователя
            await self._update_user_balance(payment['user_id'], event.amount)

            # Обновление транзакции
            transactions = self.transaction_repo.get_transactions_by_payment(payment['id'])
            if transactions:
                self.transaction_repo.update_transaction_status(
                    transactions[0]['id'], 'succeeded'
                )

            # Уведомление пользователя
            if self.notification_service:
                await self.notification_service.notify_payment_success(
                    payment['user_id'], event.amount
                )

            self.logger.info(f"Successfully processed payment: {event.payment_id}, amount: {event.amount}")

        except Exception as e:
            self.logger.error(f"Error processing successful payment: {e}", exc_info=True)

    async def _process_failed_payment(self, event: PaymentEvent):
        """Обработка неудачного платежа"""
        try:
            # Обновление статуса платежа
            self.payment_repo.update_payment_status_by_external_id(
                event.payment_id, 'failed',
                processed_at=datetime.now(),
                error_message=event.metadata.get('error', 'Payment failed')
            )

            # Получение данных платежа
            payment = self.payment_repo.get_payment_by_external_id(event.payment_id)
            if payment and self.notification_service:
                await self.notification_service.notify_payment_failed(
                    payment['user_id'],
                    event.metadata.get('error', 'Unknown error')
                )

            self.logger.info(f"Processed failed payment: {event.payment_id}")

        except Exception as e:
            self.logger.error(f"Error processing failed payment: {e}", exc_info=True)

    async def _process_cancelled_payment(self, event: PaymentEvent):
        """Обработка отмененного платежа"""
        try:
            # Обновление статуса платежа
            self.payment_repo.update_payment_status_by_external_id(
                event.payment_id, 'cancelled',
                processed_at=datetime.now()
            )

            self.logger.info(f"Processed cancelled payment: {event.payment_id}")

        except Exception as e:
            self.logger.error(f"Error processing cancelled payment: {e}", exc_info=True)

    async def _process_pending_payment(self, event: PaymentEvent):
        """Обработка платежа в ожидании"""
        try:
            # Обновление статуса платежа
            self.payment_repo.update_payment_status_by_external_id(
                event.payment_id, 'processing'
            )

            self.logger.info(f"Processed pending payment: {event.payment_id}")

        except Exception as e:
            self.logger.error(f"Error processing pending payment: {e}", exc_info=True)

    async def _update_user_balance(self, user_id: int, amount: float):
        """Обновление баланса пользователя после успешного платежа"""
        try:
            # Добавление доната в систему пользователей
            await self.user_service.add_donation(user_id, amount)

            self.logger.info(f"Updated user balance: user_id={user_id}, amount={amount}")

        except Exception as e:
            self.logger.error(f"Error updating user balance: {e}", exc_info=True)

    def _validate_donation_data(self, user_id: int, amount: float, provider_name: str) -> PaymentValidationResult:
        """Валидация данных доната"""
        errors = []
        warnings = []

        # Проверка user_id
        if not isinstance(user_id, int) or user_id <= 0:
            errors.append("Invalid user ID")

        # Проверка суммы
        if not isinstance(amount, (int, float)) or amount <= 0:
            errors.append("Amount must be positive number")
        elif amount < self.min_amount:
            errors.append(f"Minimum amount is {self.min_amount}")
        elif amount > self.max_amount:
            errors.append(f"Maximum amount is {self.max_amount}")

        # Проверка провайдера
        if provider_name not in self.providers:
            errors.append(f"Unsupported provider: {provider_name}")
        elif not self.payment_configs.get(provider_name, PaymentConfig(False)).enabled:
            errors.append(f"Provider {provider_name} is disabled")

        return PaymentValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _check_duplicate_donation(self, user_id: int, amount: float) -> bool:
        """Проверка на дубликат доната"""
        return self.payment_repo.check_duplicate_payment(
            "", amount, user_id, self.duplicate_check_window_minutes
        )

    def _get_provider(self, provider_name: str) -> PaymentProvider:
        """Получение провайдера по имени"""
        if provider_name not in self.providers:
            raise PaymentProviderError(f"Provider {provider_name} not found")
        return self.providers[provider_name]

    def get_payment_status(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Получение статуса платежа"""
        return self.payment_repo.get_payment_by_id(payment_id)

    def get_user_payments(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение платежей пользователя"""
        return self.payment_repo.get_payments_by_user(user_id, limit)

    def get_payment_statistics(self, date_from: Optional[datetime] = None,
                             date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """Получение статистики платежей"""
        return self.payment_repo.get_payment_statistics(date_from, date_to)

    def cancel_payment(self, payment_id: int, user_id: int) -> bool:
        """Отмена платежа"""
        try:
            # Получение данных платежа
            payment = self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                raise PaymentNotFoundError(f"Payment {payment_id} not found")

            if payment['user_id'] != user_id:
                raise PaymentSecurityError("Unauthorized payment cancellation")

            if payment['status'] not in ['pending', 'processing']:
                return False  # Нельзя отменить завершенный платеж

            # Получение провайдера и отмена платежа
            provider = self._get_provider(payment['provider'])
            success = provider.cancel_payment(payment['external_id'])

            if success:
                self.payment_repo.update_payment_status(payment_id, 'cancelled')
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error cancelling payment: {e}", exc_info=True)
            return False
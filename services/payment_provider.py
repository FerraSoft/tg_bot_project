"""
Интерфейсы и реализации платежных провайдеров.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from core.payment_models import PaymentIntent, PaymentEvent, PaymentProvider as ProviderEnum
from core.payment_exceptions import PaymentProviderError, PaymentSecurityError


class PaymentProvider(ABC):
    """Абстрактный интерфейс для платежных провайдеров"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def create_payment(self, amount: float, currency: str, user_id: int, metadata: Dict[str, Any]) -> PaymentIntent:
        """
        Создание платежа

        Args:
            amount: Сумма платежа
            currency: Валюта
            user_id: ID пользователя
            metadata: Дополнительные данные

        Returns:
            PaymentIntent: Интент платежа
        """
        pass

    @abstractmethod
    def confirm_payment(self, payment_id: str) -> bool:
        """
        Подтверждение платежа

        Args:
            payment_id: ID платежа у провайдера

        Returns:
            bool: Успешно ли подтвержден
        """
        pass

    @abstractmethod
    def cancel_payment(self, payment_id: str) -> bool:
        """
        Отмена платежа

        Args:
            payment_id: ID платежа у провайдера

        Returns:
            bool: Успешно ли отменен
        """
        pass

    @abstractmethod
    def get_payment_status(self, payment_id: str) -> str:
        """
        Получение статуса платежа

        Args:
            payment_id: ID платежа у провайдера

        Returns:
            str: Статус платежа
        """
        pass

    @abstractmethod
    def validate_webhook(self, request_data: Dict, signature: str) -> bool:
        """
        Валидация webhook подписи

        Args:
            request_data: Данные запроса
            signature: Подпись

        Returns:
            bool: Валидна ли подпись
        """
        pass

    @abstractmethod
    def process_webhook(self, webhook_data: Dict) -> PaymentEvent:
        """
        Обработка webhook события

        Args:
            webhook_data: Данные webhook

        Returns:
            PaymentEvent: Событие платежа
        """
        pass


class StripePaymentProvider(PaymentProvider):
    """Интеграция с Stripe"""

    def __init__(self, api_key: str, webhook_secret: str):
        super().__init__("stripe")
        try:
            import stripe
            stripe.api_key = api_key
            self.stripe = stripe
        except ImportError:
            raise PaymentProviderError("Stripe library not installed")
        self.webhook_secret = webhook_secret

    def create_payment(self, amount: float, currency: str, user_id: int, metadata: Dict[str, Any]) -> PaymentIntent:
        """Создание платежа в Stripe"""
        try:
            self.logger.info(f"Creating Stripe payment: amount={amount}, currency={currency}, user_id={user_id}")

            # Создаем PaymentIntent
            intent = self.stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe работает с копейками
                currency=currency.lower(),
                metadata={
                    'user_id': str(user_id),
                    'created_at': datetime.now().isoformat(),
                    **metadata
                },
                payment_method_types=['card'],
                confirmation_method='automatic',
                capture_method='automatic'
            )

            self.logger.info(f"Stripe payment created: {intent.id}")
            return PaymentIntent(
                id=intent.id,
                url=f"https://checkout.stripe.com/pay/{intent.client_secret}",
                client_secret=intent.client_secret,
                status=intent.status
            )

        except self.stripe.error.StripeError as e:
            self.logger.error(f"Stripe API error: {e}")
            raise PaymentProviderError(f"Stripe error: {e}")

    def confirm_payment(self, payment_id: str) -> bool:
        """Подтверждение платежа в Stripe"""
        try:
            intent = self.stripe.PaymentIntent.retrieve(payment_id)
            if intent.status == 'requires_confirmation':
                intent.confirm()
            return intent.status in ['succeeded', 'processing']
        except self.stripe.error.StripeError as e:
            raise PaymentProviderError(f"Stripe confirm error: {e}")

    def cancel_payment(self, payment_id: str) -> bool:
        """Отмена платежа в Stripe"""
        try:
            intent = self.stripe.PaymentIntent.retrieve(payment_id)
            intent.cancel()
            return True
        except self.stripe.error.StripeError as e:
            raise PaymentProviderError(f"Stripe cancel error: {e}")

    def get_payment_status(self, payment_id: str) -> str:
        """Получение статуса платежа из Stripe"""
        try:
            intent = self.stripe.PaymentIntent.retrieve(payment_id)
            return intent.status
        except self.stripe.error.StripeError as e:
            raise PaymentProviderError(f"Stripe status error: {e}")

    def validate_webhook(self, request_data: Dict, signature: str) -> bool:
        """Валидация Stripe webhook подписи"""
        try:
            self.stripe.Webhook.construct_event(
                request_data,
                signature,
                self.webhook_secret
            )
            return True
        except ValueError:
            return False

    def process_webhook(self, webhook_data: Dict) -> PaymentEvent:
        """Обработка Stripe webhook"""
        event = webhook_data
        event_type = event.get('type', '')
        data = event.get('data', {}).get('object', {})

        # Извлекаем payment_intent
        payment_intent = data
        if 'payment_intent' in data:
            payment_intent = data['payment_intent']

        amount = payment_intent.get('amount', 0) / 100  # Конвертируем из копеек
        metadata = payment_intent.get('metadata', {})

        return PaymentEvent(
            type=f"payment.{event_type.split('.')[1]}",
            payment_id=payment_intent.get('id'),
            amount=amount,
            currency=payment_intent.get('currency', 'usd').upper(),
            user_id=int(metadata.get('user_id')) if metadata.get('user_id') else None,
            metadata=metadata
        )


class YooKassaPaymentProvider(PaymentProvider):
    """Интеграция с YooKassa"""

    def __init__(self, shop_id: str, secret_key: str):
        super().__init__("yookassa")
        try:
            from yookassa import Client, Payment
            self.client = Client(shop_id=shop_id, secret_key=secret_key)
            self.Payment = Payment
        except ImportError:
            raise PaymentProviderError("YooKassa library not installed")
        self.secret_key = secret_key

    def create_payment(self, amount: float, currency: str, user_id: int, metadata: Dict[str, Any]) -> PaymentIntent:
        """Создание платежа в YooKassa"""
        try:
            self.logger.info(f"Creating YooKassa payment: amount={amount}, currency={currency}, user_id={user_id}")

            payment = self.Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": currency.upper()
                },
                "metadata": {
                    'user_id': str(user_id),
                    'created_at': datetime.now().isoformat(),
                    **metadata
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/bot"  # URL возврата в бот
                },
                "capture": True,
                "description": f"Донат пользователю {user_id}"
            }, self.client.id)

            self.logger.info(f"YooKassa payment created: {payment.id}")
            return PaymentIntent(
                id=payment.id,
                url=payment.confirmation.confirmation_url,
                status=payment.status
            )

        except Exception as e:
            self.logger.error(f"YooKassa API error: {e}")
            raise PaymentProviderError(f"YooKassa error: {e}")

    def confirm_payment(self, payment_id: str) -> bool:
        """Подтверждение платежа в YooKassa"""
        try:
            payment = self.Payment.find_one(payment_id, self.client.id)
            return payment.status == 'succeeded'
        except Exception as e:
            raise PaymentProviderError(f"YooKassa confirm error: {e}")

    def cancel_payment(self, payment_id: str) -> bool:
        """Отмена платежа в YooKassa"""
        try:
            payment = self.Payment.find_one(payment_id, self.client.id)
            if payment.status == 'pending':
                payment.cancel()
                return True
            return False
        except Exception as e:
            raise PaymentProviderError(f"YooKassa cancel error: {e}")

    def get_payment_status(self, payment_id: str) -> str:
        """Получение статуса платежа из YooKassa"""
        try:
            payment = self.Payment.find_one(payment_id, self.client.id)
            return payment.status
        except Exception as e:
            raise PaymentProviderError(f"YooKassa status error: {e}")

    def validate_webhook(self, request_data: Dict, signature: str) -> bool:
        """Валидация YooKassa webhook подписи"""
        try:
            # Реализация проверки подписи YooKassa
            import hashlib
            import hmac

            body = request_data
            if isinstance(request_data, dict):
                import json
                body = json.dumps(request_data, separators=(',', ':'))

            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            self.logger.error(f"YooKassa webhook validation error: {e}")
            return False

    def process_webhook(self, webhook_data: Dict) -> PaymentEvent:
        """Обработка YooKassa webhook"""
        event = webhook_data
        payment = event.get('object', {})

        amount_value = float(payment.get('amount', {}).get('value', 0))
        currency = payment.get('amount', {}).get('currency', 'RUB')
        metadata = payment.get('metadata', {})

        return PaymentEvent(
            type=f"payment.{payment.get('status', 'unknown')}",
            payment_id=payment.get('id'),
            amount=amount_value,
            currency=currency,
            user_id=int(metadata.get('user_id')) if metadata.get('user_id') else None,
            metadata=metadata
        )


class SBPaymentProvider(PaymentProvider):
    """Интеграция с Системой Быстрых Платежей (СБП)"""

    def __init__(self, api_key: str, bank_id: str, webhook_secret: str, base_url: str = "https://api.sbp.ru"):
        super().__init__("sbp")
        self.api_key = api_key
        self.bank_id = bank_id
        self.webhook_secret = webhook_secret
        self.base_url = base_url
        self.session = None

        # Импорт aiohttp для асинхронных HTTP запросов
        try:
            import aiohttp
            self.aiohttp = aiohttp
        except ImportError:
            raise PaymentProviderError("aiohttp library not installed (required for SBP)")

    async def _ensure_session(self):
        """Инициализация HTTP сессии"""
        if self.session is None:
            self.session = self.aiohttp.ClientSession()

    async def close(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            self.session = None

    def create_payment(self, amount: float, currency: str, user_id: int, metadata: Dict[str, Any]) -> PaymentIntent:
        """Создание платежа через СБП"""
        # Для СБП создание платежа обычно происходит асинхронно
        # Возвращаем intent с URL для перенаправления на платежную форму
        try:
            payment_id = f"sbp_{user_id}_{int(datetime.now().timestamp())}"

            # СБП обычно использует QR-код или перенаправление на банковское приложение
            payment_url = f"{self.base_url}/pay/{payment_id}"

            return PaymentIntent(
                id=payment_id,
                url=payment_url,
                status="pending"
            )

        except Exception as e:
            self.logger.error(f"SBP payment creation error: {e}")
            raise PaymentProviderError(f"SBP payment creation failed: {e}")

    async def create_payment_async(self, amount: float, currency: str, user_id: int, metadata: Dict[str, Any]) -> PaymentIntent:
        """Асинхронное создание платежа через СБП"""
        await self._ensure_session()

        try:
            payment_data = {
                "amount": amount,
                "currency": currency,
                "user_id": user_id,
                "bank_id": self.bank_id,
                "metadata": metadata
            }

            async with self.session.post(
                f"{self.base_url}/payments",
                json=payment_data,
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    return PaymentIntent(
                        id=data["payment_id"],
                        url=data["payment_url"],
                        status="pending"
                    )
                else:
                    error_data = await response.text()
                    raise PaymentProviderError(f"SBP API error: {response.status} - {error_data}")

        except self.aiohttp.ClientError as e:
            raise PaymentProviderError(f"SBP network error: {e}")

    def confirm_payment(self, payment_id: str) -> bool:
        """Подтверждение платежа через СБП"""
        # Для СБП подтверждение обычно происходит через webhook
        # Этот метод можно использовать для ручного подтверждения
        self.logger.warning(f"SBP manual confirmation not supported for {payment_id}")
        return False

    async def confirm_payment_async(self, payment_id: str) -> bool:
        """Асинхронное подтверждение платежа через СБП"""
        await self._ensure_session()

        try:
            async with self.session.post(
                f"{self.base_url}/payments/{payment_id}/confirm",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                return response.status == 200

        except self.aiohttp.ClientError as e:
            self.logger.error(f"SBP confirm error: {e}")
            return False

    def cancel_payment(self, payment_id: str) -> bool:
        """Отмена платежа через СБП"""
        self.logger.warning(f"SBP cancel not supported for {payment_id}")
        return False

    async def cancel_payment_async(self, payment_id: str) -> bool:
        """Асинхронная отмена платежа через СБП"""
        await self._ensure_session()

        try:
            async with self.session.post(
                f"{self.base_url}/payments/{payment_id}/cancel",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                return response.status == 200

        except self.aiohttp.ClientError as e:
            self.logger.error(f"SBP cancel error: {e}")
            return False

    def get_payment_status(self, payment_id: str) -> str:
        """Получение статуса платежа через СБП"""
        # Синхронная версия для совместимости
        import asyncio
        try:
            return asyncio.run(self.get_payment_status_async(payment_id))
        except:
            return "unknown"

    async def get_payment_status_async(self, payment_id: str) -> str:
        """Асинхронное получение статуса платежа через СБП"""
        await self._ensure_session()

        try:
            async with self.session.get(
                f"{self.base_url}/payments/{payment_id}/status",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("status", "unknown")
                else:
                    return "unknown"

        except self.aiohttp.ClientError as e:
            self.logger.error(f"SBP status error: {e}")
            return "unknown"

    def validate_webhook(self, request_data: Dict, signature: str) -> bool:
        """Валидация webhook подписи для СБП"""
        try:
            # СБП webhook валидация основана на HMAC-SHA256
            import base64
            import json

            # Сериализуем данные в JSON
            body = json.dumps(request_data, separators=(',', ':'))

            # Вычисляем ожидаемую подпись
            expected_hmac = hmac.new(
                self.webhook_secret.encode('utf-8'),
                body.encode('utf-8'),
                hashlib.sha256
            )
            expected_signature = base64.b64encode(expected_hmac.digest()).decode('utf-8')

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            self.logger.error(f"SBP webhook validation error: {e}")
            return False

    def process_webhook(self, webhook_data: Dict) -> PaymentEvent:
        """Обработка webhook события от СБП"""
        try:
            event_type = webhook_data.get("event_type", "payment.unknown")
            payment_data = webhook_data.get("payment", {})

            amount = float(payment_data.get("amount", 0))
            metadata = payment_data.get("metadata", {})

            return PaymentEvent(
                type=f"payment.{event_type.split('.')[-1]}",
                payment_id=payment_data.get("id"),
                amount=amount,
                currency=payment_data.get("currency", "RUB"),
                user_id=int(metadata.get("user_id")) if metadata.get("user_id") else None,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"SBP webhook processing error: {e}")
            raise PaymentProviderError(f"SBP webhook processing failed: {e}")
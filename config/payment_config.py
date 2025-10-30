"""
Конфигурация платежных систем.
"""

import os
from typing import Dict, Any, Optional
from services.donation_service import PaymentConfig


class PaymentConfiguration:
    """
    Конфигурация для всех платежных провайдеров.

    Управляет настройками Stripe, YooKassa, СБП и других провайдеров.
    """

    def __init__(self):
        """Инициализация конфигурации"""
        self.providers = self._load_provider_configs()

    def _load_provider_configs(self) -> Dict[str, PaymentConfig]:
        """
        Загрузка конфигураций всех провайдеров.

        Returns:
            Dict[str, PaymentConfig]: Конфигурации провайдеров
        """
        return {
            'stripe': PaymentConfig(
                enabled=self._get_bool_env('PAYMENT_STRIPE_ENABLED', True),
                api_key=os.getenv('STRIPE_API_KEY'),
                webhook_secret=os.getenv('STRIPE_WEBHOOK_SECRET')
            ),

            'yookassa': PaymentConfig(
                enabled=self._get_bool_env('PAYMENT_YOOKASSA_ENABLED', False),
                shop_id=os.getenv('YOOKASSA_SHOP_ID'),
                secret_key=os.getenv('YOOKASSA_SECRET_KEY')
            ),

            'sbp': PaymentConfig(
                enabled=self._get_bool_env('PAYMENT_SBP_ENABLED', False),
                api_key=os.getenv('SBP_API_KEY'),
                bank_id=os.getenv('SBP_BANK_ID'),
                webhook_secret=os.getenv('SBP_WEBHOOK_SECRET')
            )
        }

    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """
        Получение булевого значения из переменной окружения.

        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию

        Returns:
            bool: Булево значение
        """
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

    def get_provider_config(self, provider_name: str) -> Optional[PaymentConfig]:
        """
        Получение конфигурации провайдера.

        Args:
            provider_name: Название провайдера

        Returns:
            Optional[PaymentConfig]: Конфигурация провайдера или None
        """
        return self.providers.get(provider_name)

    def get_enabled_providers(self) -> Dict[str, PaymentConfig]:
        """
        Получение всех включенных провайдеров.

        Returns:
            Dict[str, PaymentConfig]: Включенные провайдеры
        """
        return {name: config for name, config in self.providers.items() if config.enabled}

    def validate_configs(self) -> Dict[str, Any]:
        """
        Валидация всех конфигураций.

        Returns:
            Dict[str, Any]: Результаты валидации
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        for provider_name, config in self.providers.items():
            if not config.enabled:
                continue

            # Проверка обязательных полей
            if provider_name == 'stripe':
                if not config.api_key:
                    results['errors'].append(f"STRIPE_API_KEY required for {provider_name}")
                if not config.webhook_secret:
                    results['errors'].append(f"STRIPE_WEBHOOK_SECRET required for {provider_name}")

            elif provider_name == 'yookassa':
                if not config.shop_id:
                    results['errors'].append(f"YOOKASSA_SHOP_ID required for {provider_name}")
                if not config.secret_key:
                    results['errors'].append(f"YOOKASSA_SECRET_KEY required for {provider_name}")

            elif provider_name == 'sbp':
                # Для СБП конфигурация пока не обязательна (заглушка)
                if not config.api_key:
                    results['warnings'].append(f"SBP_API_KEY not set for {provider_name}")

        results['valid'] = len(results['errors']) == 0
        return results

    def get_payment_limits(self) -> Dict[str, Any]:
        """
        Получение лимитов платежей.

        Returns:
            Dict[str, Any]: Лимиты платежей
        """
        return {
            'min_amount': float(os.getenv('PAYMENT_MIN_AMOUNT', '10.0')),
            'max_amount': float(os.getenv('PAYMENT_MAX_AMOUNT', '10000.0')),
            'allowed_currencies': ['RUB', 'USD', 'EUR'],
            'rate_limits': {
                'max_payments_per_hour': int(os.getenv('PAYMENT_MAX_PER_HOUR', '10')),
                'max_amount_per_hour': float(os.getenv('PAYMENT_MAX_AMOUNT_PER_HOUR', '50000.0'))
            }
        }

    def get_notification_settings(self) -> Dict[str, Any]:
        """
        Получение настроек уведомлений.

        Returns:
            Dict[str, Any]: Настройки уведомлений
        """
        return {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'admin_chat_ids': self._parse_admin_chat_ids(os.getenv('PAYMENT_ADMIN_CHAT_IDS', '')),
            'notify_success': self._get_bool_env('PAYMENT_NOTIFY_SUCCESS', True),
            'notify_failure': self._get_bool_env('PAYMENT_NOTIFY_FAILURE', True),
            'notify_admin_errors': self._get_bool_env('PAYMENT_NOTIFY_ADMIN_ERRORS', True)
        }

    def _parse_admin_chat_ids(self, chat_ids_str: str) -> list:
        """
        Парсинг списка ID чатов администраторов.

        Args:
            chat_ids_str: Строка с ID чатов через запятую

        Returns:
            list: Список ID чатов
        """
        if not chat_ids_str:
            return []

        try:
            return [int(chat_id.strip()) for chat_id in chat_ids_str.split(',') if chat_id.strip()]
        except ValueError:
            return []


# Глобальная конфигурация
payment_config = PaymentConfiguration()


def get_payment_config() -> PaymentConfiguration:
    """Получение глобальной конфигурации платежей"""
    return payment_config


# Функции для быстрого доступа
def get_provider_config(provider_name: str) -> Optional[PaymentConfig]:
    """Получение конфигурации провайдера"""
    return payment_config.get_provider_config(provider_name)


def get_enabled_providers() -> Dict[str, PaymentConfig]:
    """Получение включенных провайдеров"""
    return payment_config.get_enabled_providers()


def validate_payment_configs() -> Dict[str, Any]:
    """Валидация конфигураций"""
    return payment_config.validate_configs()
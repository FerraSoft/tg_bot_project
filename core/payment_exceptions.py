"""
Исключения для системы платежей.
"""

from core.exceptions import BotException


class PaymentError(BotException):
    """Базовое исключение для платежей"""
    pass


class PaymentProviderError(PaymentError):
    """Ошибка платежного провайдера"""
    pass


class PaymentValidationError(PaymentError):
    """Ошибка валидации платежа"""
    pass


class PaymentSecurityError(PaymentError):
    """Ошибка безопасности платежа"""
    pass


class PaymentTimeoutError(PaymentError):
    """Таймаут платежа"""
    pass


class PaymentDuplicateError(PaymentError):
    """Дубликат платежа"""
    pass


class PaymentNotFoundError(PaymentError):
    """Платеж не найден"""
    pass
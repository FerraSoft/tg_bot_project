"""
Модели данных для платежной системы.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class PaymentStatus(Enum):
    """Статусы платежа"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentProvider(Enum):
    """Платежные провайдеры"""
    STRIPE = "stripe"
    YOOKASSA = "yookassa"


class TransactionType(Enum):
    """Типы транзакций"""
    PAYMENT = "payment"
    REFUND = "refund"
    CHARGEBACK = "chargeback"


@dataclass
class PaymentIntent:
    """Интент платежа от провайдера"""
    id: str
    url: str
    client_secret: Optional[str] = None
    status: str = "pending"


@dataclass
class PaymentEvent:
    """Событие платежа"""
    type: str  # 'payment.succeeded', 'payment.failed', etc.
    payment_id: str
    amount: float
    currency: str = "RUB"
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Payment:
    """Модель платежа"""
    id: int
    user_id: int
    amount: float
    currency: str
    provider: str  # PaymentProvider.value
    external_id: str  # ID платежа у провайдера
    status: str  # PaymentStatus.value
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at.replace('Z', '+00:00'))
        if self.processed_at and isinstance(self.processed_at, str):
            self.processed_at = datetime.fromisoformat(self.processed_at.replace('Z', '+00:00'))


@dataclass
class Transaction:
    """Модель транзакции"""
    id: int
    payment_id: int
    type: str  # TransactionType.value
    amount: float
    status: str
    created_at: datetime
    external_transaction_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))


@dataclass
class DonationResponse:
    """Ответ на создание доната"""
    payment_url: str
    payment_id: int
    provider: str
    amount: float
    currency: str


@dataclass
class PaymentValidationResult:
    """Результат валидации платежа"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]

    def __post_init__(self):
        if not self.errors:
            self.errors = []
        if not self.warnings:
            self.warnings = []
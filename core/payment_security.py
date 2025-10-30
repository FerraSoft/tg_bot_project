"""
Модуль безопасности для платежных операций.
"""

import hmac
import hashlib
import logging
import re
import subprocess
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class PaymentSecurity:
    """
    Класс для обеспечения безопасности платежных операций.

    Отвечает за:
    - Валидацию webhook подписей
    - Предотвращение дублирования платежей
    - Защиту от фрода
    - Шифрование чувствительных данных
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def validate_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
        """
        Валидация подписи Stripe webhook.

        Args:
            payload: Тело запроса
            signature: Подпись из заголовка
            secret: Секретный ключ webhook

        Returns:
            bool: Валидна ли подпись
        """
        try:
            # Stripe отправляет подпись в формате t=123456,v1=abc123
            timestamp = None
            signatures = []

            for part in signature.split(','):
                key, value = part.split('=', 1)
                if key == 't':
                    timestamp = value
                elif key.startswith('v1'):
                    signatures.append(value)

            if not timestamp or not signatures:
                return False

            # Создание ожидаемой подписи
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Проверка соответствия
            for sig in signatures:
                if hmac.compare_digest(sig, expected_signature):
                    return True

            return False

        except Exception as e:
            logging.getLogger(__name__).error(f"Stripe signature validation error: {e}")
            return False

    @staticmethod
    def validate_yookassa_signature(request_body: str, signature: str, secret: str) -> bool:
        """
        Валидация подписи YooKassa webhook.

        Args:
            request_body: Тело запроса как строка
            signature: Подпись из заголовка
            secret: Секретный ключ

        Returns:
            bool: Валидна ли подпись
        """
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                request_body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logging.getLogger(__name__).error(f"YooKassa signature validation error: {e}")
            return False

    @staticmethod
    def validate_sbp_signature(request_body: str, signature: str, secret: str) -> bool:
        """
        Валидация подписи СБП webhook согласно спецификации СБП.

        СБП использует HMAC-SHA256 с телом запроса и секретным ключом.
        Формат подписи: base64-encoded HMAC-SHA256 hash.

        Args:
            request_body: Тело запроса как строка (JSON)
            signature: Подпись из заголовка (base64)
            secret: Секретный ключ СБП

        Returns:
            bool: Валидна ли подпись
        """
        try:
            # СБП передает подпись в base64 формате
            # Вычисляем ожидаемую подпись
            expected_hmac = hmac.new(
                secret.encode('utf-8'),
                request_body.encode('utf-8'),
                hashlib.sha256
            )

            # Кодируем в base64 как ожидает СБП
            import base64
            expected_signature = base64.b64encode(expected_hmac.digest()).decode('utf-8')

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logging.getLogger(__name__).error(f"SBP signature validation error: {e}")
            return False

    @staticmethod
    def generate_idempotency_key(payment_data: Dict[str, Any]) -> str:
        """
        Генерация ключа идемпотентности для предотвращения дубликатов.

        Args:
            payment_data: Данные платежа

        Returns:
            str: Ключ идемпотентности
        """
        # Создание уникального ключа на основе user_id, amount и timestamp
        key_data = f"{payment_data['user_id']}:{payment_data['amount']}:{int(datetime.now().timestamp())}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    @staticmethod
    def check_idempotency_key(key: str, ttl_seconds: int = 3600) -> bool:
        """
        Проверка ключа идемпотентности в кэше.

        Args:
            key: Ключ идемпотентности
            ttl_seconds: Время жизни ключа

        Returns:
            bool: True если ключ уже использовался
        """
        # В реальной реализации здесь был бы Redis или другой кэш
        # Пока просто логируем
        logger = logging.getLogger(__name__)
        logger.debug(f"Checking idempotency key: {key}")
        return False  # Для тестирования всегда возвращаем False

    @staticmethod
    def sanitize_payment_data(payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Очистка платежных данных от чувствительной информации.

        Args:
            payment_data: Исходные данные платежа

        Returns:
            Dict[str, Any]: Очищенные данные
        """
        sanitized = payment_data.copy()

        # Список полей для удаления
        sensitive_fields = [
            'card_number', 'cvv', 'cardholder_name',
            'password', 'secret_key', 'api_key',
            'webhook_secret', 'private_key'
        ]

        # Удаление чувствительных полей
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = '***'

        # Маскировка частичных данных
        if 'card_number' in payment_data:
            card = payment_data['card_number']
            if len(card) > 4:
                sanitized['card_number'] = f"**** **** **** {card[-4:]}"

        return sanitized

    @staticmethod
    def validate_amount_range(amount: float, min_amount: float = 1.0,
                            max_amount: float = 100000.0) -> bool:
        """
        Проверка суммы платежа на допустимый диапазон.

        Args:
            amount: Сумма платежа
            min_amount: Минимальная сумма
            max_amount: Максимальная сумма

        Returns:
            bool: Входит ли сумма в допустимый диапазон
        """
        return min_amount <= amount <= max_amount

    @staticmethod
    def validate_currency(currency: str, allowed_currencies: list = None) -> bool:
        """
        Проверка валюты платежа.

        Args:
            currency: Код валюты
            allowed_currencies: Список разрешенных валют

        Returns:
            bool: Разрешена ли валюта
        """
        if allowed_currencies is None:
            allowed_currencies = ['RUB', 'USD', 'EUR']

        return currency.upper() in allowed_currencies

    @staticmethod
    def detect_suspicious_activity(payment_data: Dict[str, Any],
                                 recent_payments: list) -> Dict[str, Any]:
        """
        Обнаружение подозрительной активности.

        Args:
            payment_data: Данные текущего платежа
            recent_payments: Список недавних платежей пользователя

        Returns:
            Dict[str, Any]: Результаты анализа
        """
        result = {
            'is_suspicious': False,
            'risk_level': 'low',
            'reasons': []
        }

        # Проверка на слишком частые платежи
        recent_count = len([p for p in recent_payments
                          if (datetime.now() - datetime.fromisoformat(p['created_at'])).seconds < 300])
        if recent_count > 5:
            result['is_suspicious'] = True
            result['risk_level'] = 'medium'
            result['reasons'].append('too_many_recent_payments')

        # Проверка на необычно большую сумму
        amount = payment_data['amount']
        avg_amount = sum(p['amount'] for p in recent_payments) / len(recent_payments) if recent_payments else 0
        if amount > avg_amount * 10 and avg_amount > 0:
            result['is_suspicious'] = True
            result['risk_level'] = 'high'
            result['reasons'].append('unusually_large_amount')

        # Проверка на круглые суммы (часто используется в тестах фрода)
        if amount in [1000, 5000, 10000, 50000]:
            result['is_suspicious'] = True
            result['risk_level'] = 'low'
            result['reasons'].append('round_amount_suspicious')

        return result

    @staticmethod
    def encrypt_sensitive_data(data: str, key: str) -> str:
        """
        Шифрование чувствительных данных с использованием Fernet (AES 128).

        Args:
            data: Данные для шифрования
            key: Ключ шифрования (должен быть 32 байта для Fernet)

        Returns:
            str: Зашифрованные данные (base64)

        Raises:
            PaymentSecurityError: Ошибка шифрования
        """
        try:
            from cryptography.fernet import Fernet, InvalidToken
            import base64

            # Создаем ключ подходящего размера если необходимо
            if len(key) != 32:
                # Используем SHA256 для генерации 32-байтового ключа
                key = hashlib.sha256(key.encode('utf-8')).digest()

            # Создаем Fernet ключ (base64-encoded 32-byte key)
            fernet_key = base64.urlsafe_b64encode(key)
            fernet = Fernet(fernet_key)

            # Шифруем данные
            encrypted = fernet.encrypt(data.encode('utf-8'))
            return encrypted.decode('utf-8')

        except ImportError:
            from core.payment_exceptions import PaymentSecurityError
            logger = logging.getLogger(__name__)
            logger.error("cryptography library not installed, encryption unavailable")
            raise PaymentSecurityError("Encryption library not available")
        except Exception as e:
            from core.payment_exceptions import PaymentSecurityError
            logger = logging.getLogger(__name__)
            logger.error(f"Encryption error: {e}")
            raise PaymentSecurityError(f"Failed to encrypt data: {e}")

    @staticmethod
    def decrypt_sensitive_data(encrypted_data: str, key: str) -> str:
        """
        Расшифровка чувствительных данных с использованием Fernet (AES 128).

        Args:
            encrypted_data: Зашифрованные данные (base64)
            key: Ключ шифрования

        Returns:
            str: Расшифрованные данные

        Raises:
            PaymentSecurityError: Ошибка расшифровки
        """
        try:
            from cryptography.fernet import Fernet, InvalidToken
            import base64

            # Создаем ключ подходящего размера если необходимо
            if len(key) != 32:
                # Используем SHA256 для генерации 32-байтового ключа
                key = hashlib.sha256(key.encode('utf-8')).digest()

            # Создаем Fernet ключ (base64-encoded 32-byte key)
            fernet_key = base64.urlsafe_b64encode(key)
            fernet = Fernet(fernet_key)

            # Расшифровываем данные
            decrypted = fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted.decode('utf-8')

        except ImportError:
            logger = logging.getLogger(__name__)
            logger.error("cryptography library not installed, decryption unavailable")
            raise PaymentSecurityError("Decryption library not available")
        except InvalidToken:
            from core.payment_exceptions import PaymentSecurityError
            logger = logging.getLogger(__name__)
            logger.error("Invalid encryption token or key")
            raise PaymentSecurityError("Invalid encryption token")
        except Exception as e:
            from core.payment_exceptions import PaymentSecurityError
            logger = logging.getLogger(__name__)
            logger.error(f"Decryption error: {e}")
            raise PaymentSecurityError(f"Failed to decrypt data: {e}")

    @staticmethod
    def validate_ffmpeg_command(command: list) -> bool:
        """
        Проверка безопасности команды ffmpeg с дополнительными мерами защиты.

        Args:
            command: Список аргументов команды ffmpeg

        Returns:
            bool: Безопасна ли команда
        """
        if not command or command[0] != 'ffmpeg':
            return False

        # Запрещенные опции и паттерны
        dangerous_patterns = [
            r'-f\s+srt',  # SRT формат может быть опасным
            r'-i\s+.*\.\.',  # Path traversal
            r'-i\s+.*\|',  # Command injection
            r'-i\s+.*;',  # Command injection
            r'-i\s+.*\$',  # Shell variables
            r'-i\s+.*`',  # Command substitution
            r'-y\s+.*\.\.',  # Path traversal в output
            r'-y\s+.*\|',  # Command injection в output
            r'-y\s+.*;',  # Command injection в output
            r'-y\s+.*\$',  # Shell variables в output
            r'-y\s+.*`',  # Command substitution в output
            r'-i\s+.*\.\.',  # Path traversal в input
            r'-i\s+.*\|',  # Command injection в input
            r'-i\s+.*;',  # Command injection в input
            r'-i\s+.*\$',  # Shell variables в input
            r'-i\s+.*`',  # Command substitution в input
            r'-vf\s+.*\|',  # Command injection в video filters
            r'-vf\s+.*;',  # Command injection в video filters
            r'-af\s+.*\|',  # Command injection в audio filters
            r'-af\s+.*;',  # Command injection в audio filters
            r'-filter_complex\s+.*\|',  # Command injection в complex filters
            r'-filter_complex\s+.*;',  # Command injection в complex filters
        ]

        command_str = ' '.join(command)

        for pattern in dangerous_patterns:
            if re.search(pattern, command_str, re.IGNORECASE):
                logging.getLogger(__name__).warning(f"Dangerous ffmpeg pattern detected: {pattern}")
                return False

        # Проверка на допустимые входные форматы
        allowed_input_formats = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv', 'mpg', 'mpeg', 'mp3', 'wav', 'aac']
        input_files = [arg for arg in command if not arg.startswith('-') and '.' in arg and not arg.endswith('/')]

        for file in input_files:
            ext = file.split('.')[-1].lower()
            if ext not in allowed_input_formats:
                logging.getLogger(__name__).warning(f"Unsupported input format: {ext}")
                return False

        # Проверка на допустимые выходные форматы
        allowed_output_formats = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'gif', 'jpg', 'png', 'mp3', 'wav', 'aac']
        if '-f' in command:
            format_idx = command.index('-f') + 1
            if format_idx < len(command):
                output_format = command[format_idx].lower()
                if output_format not in allowed_output_formats:
                    logging.getLogger(__name__).warning(f"Unsupported output format: {output_format}")
                    return False

        # Проверка на наличие выходного файла
        if '-y' not in command:
            logging.getLogger(__name__).warning("Output file not specified with -y flag")
            return False

        # Проверка на разумные ограничения
        if len(command) > 50:  # Слишком много аргументов
            logging.getLogger(__name__).warning("Too many ffmpeg arguments")
            return False

        # Проверка на запрещенные кодеки и фильтры
        dangerous_codecs = ['libx264', 'libx265', 'h264', 'hevc']  # Требуют проверки
        for arg in command:
            if any(codec in arg for codec in dangerous_codecs):
                logging.getLogger(__name__).warning(f"Potentially dangerous codec: {arg}")
                # Пока разрешаем, но логируем для мониторинга

        return True

    @staticmethod
    def sanitize_ffmpeg_output_path(output_path: str) -> Optional[str]:
        """
        Санитизация пути вывода ffmpeg.

        Args:
            output_path: Исходный путь вывода

        Returns:
            Optional[str]: Санитизированный путь или None если небезопасный
        """
        # Проверка на path traversal
        if '..' in output_path or output_path.startswith('/'):
            logging.getLogger(__name__).warning(f"Potentially dangerous output path: {output_path}")
            return None

        # Проверка на специальные символы
        if any(char in output_path for char in ['|', ';', '$', '`', '&', '<', '>']):
            logging.getLogger(__name__).warning(f"Special characters in output path: {output_path}")
            return None

        # Ограничение на допустимые расширения
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.gif', '.jpg', '.png']
        if not any(output_path.endswith(ext) for ext in allowed_extensions):
            logging.getLogger(__name__).warning(f"Unsupported output extension: {output_path}")
            return None

        return output_path

    @staticmethod
    def secure_ffmpeg_execute(command: list, timeout_seconds: int = 300) -> tuple[bool, str]:
        """
        Безопасное выполнение команды ffmpeg с дополнительными проверками.

        Args:
            command: Список аргументов команды ffmpeg
            timeout_seconds: Максимальное время выполнения

        Returns:
            tuple[bool, str]: (успешно ли выполнено, сообщение об ошибке или пустая строка)
        """
        logger = logging.getLogger(__name__)

        # Валидация команды
        if not PaymentSecurity.validate_ffmpeg_command(command):
            return False, "Command validation failed"

        try:
            # Дополнительная валидация пути вывода
            if '-y' in command:
                output_idx = command.index('-y') + 1
                if output_idx < len(command):
                    output_path = command[output_idx]
                    sanitized_path = PaymentSecurity.sanitize_ffmpeg_output_path(output_path)
                    if sanitized_path is None:
                        return False, "Output path validation failed"
                    command[output_idx] = sanitized_path

            # Выполнение с таймаутом и ограничениями
            import subprocess

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                # Ограничения безопасности
                preexec_fn=None if subprocess.os.name == 'nt' else subprocess.os.setpgrp,
                env={
                    'PATH': subprocess.os.environ.get('PATH', ''),
                    # Убираем потенциально опасные переменные окружения
                    'LD_LIBRARY_PATH': '',
                    'LD_PRELOAD': '',
                }
            )

            if result.returncode == 0:
                logger.info(f"FFmpeg command executed successfully")
                return True, ""
            else:
                error_msg = f"FFmpeg failed with code {result.returncode}: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = f"FFmpeg command timed out after {timeout_seconds} seconds"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"FFmpeg execution error: {e}"
            logger.error(error_msg)
            return False, error_msg


class PaymentRateLimiter:
    """
    Ограничитель частоты платежей для предотвращения злоупотреблений.
    """

    def __init__(self, max_payments_per_hour: int = 10, max_amount_per_hour: float = 50000):
        """
        Инициализация ограничителя.

        Args:
            max_payments_per_hour: Максимальное количество платежей в час
            max_amount_per_hour: Максимальная сумма платежей в час
        """
        self.max_payments_per_hour = max_payments_per_hour
        self.max_amount_per_hour = max_amount_per_hour
        self.logger = logging.getLogger(__name__)

        # В реальной реализации здесь был бы Redis для хранения счетчиков
        # Пока используем in-memory словарь для демонстрации
        self._counters = {}  # user_id -> {'payments': [], 'amounts': []}

    def check_rate_limit(self, user_id: int, amount: float) -> Dict[str, Any]:
        """
        Проверка ограничений частоты платежей.

        Args:
            user_id: ID пользователя
            amount: Сумма платежа

        Returns:
            Dict[str, Any]: Результат проверки
        """
        current_time = time.time()
        window_start = current_time - 3600  # 1 час в секундах

        if user_id not in self._counters:
            self._counters[user_id] = {'payments': [], 'amounts': []}

        user_counters = self._counters[user_id]

        # Очистка старых записей
        user_counters['payments'] = [t for t in user_counters['payments'] if t > window_start]
        user_counters['amounts'] = [(t, a) for t, a in user_counters['amounts'] if t > window_start]

        # Подсчет текущих значений
        current_payments = len(user_counters['payments'])
        current_amount = sum(a for _, a in user_counters['amounts'])

        # Проверка лимитов
        payments_allowed = current_payments < self.max_payments_per_hour
        amount_allowed = (current_amount + amount) <= self.max_amount_per_hour
        allowed = payments_allowed and amount_allowed

        remaining_payments = max(0, self.max_payments_per_hour - current_payments)
        remaining_amount = max(0, self.max_amount_per_hour - current_amount - amount)

        if not allowed:
            self.logger.warning(f"Rate limit exceeded for user {user_id}: "
                              f"payments {current_payments}/{self.max_payments_per_hour}, "
                              f"amount {current_amount:.2f}/{self.max_amount_per_hour}")

        return {
            'allowed': allowed,
            'remaining_payments': remaining_payments,
            'remaining_amount': remaining_amount,
            'reset_time': datetime.fromtimestamp(current_time + 3600)
        }

    def record_payment(self, user_id: int, amount: float):
        """
        Запись платежа для учета в ограничениях.

        Args:
            user_id: ID пользователя
            amount: Сумма платежа
        """
        current_time = time.time()

        if user_id not in self._counters:
            self._counters[user_id] = {'payments': [], 'amounts': []}

        user_counters = self._counters[user_id]

        # Добавление новой записи
        user_counters['payments'].append(current_time)
        user_counters['amounts'].append((current_time, amount))

        # Очистка записей старше 1 часа
        window_start = current_time - 3600
        user_counters['payments'] = [t for t in user_counters['payments'] if t > window_start]
        user_counters['amounts'] = [(t, a) for t, a in user_counters['amounts'] if t > window_start]

        self.logger.debug(f"Recorded payment for user {user_id}: amount {amount}")
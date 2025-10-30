"""
Тесты для модуля безопасности платежей.
"""

import pytest
import hmac
import hashlib
import subprocess
from unittest.mock import patch

from core.payment_security import PaymentSecurity, PaymentRateLimiter


class TestPaymentSecurity:
    """Тесты для класса PaymentSecurity."""

    def test_validate_stripe_signature_valid(self):
        """Тест валидной подписи Stripe."""
        payload = b'test_payload'
        secret = 'test_secret'
        timestamp = '1234567890'

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        signature = f"t={timestamp},v1={expected_signature}"

        assert PaymentSecurity.validate_stripe_signature(payload, signature, secret)

    def test_validate_stripe_signature_invalid(self):
        """Тест невалидной подписи Stripe."""
        payload = b'test_payload'
        secret = 'test_secret'
        signature = "t=123456,v1=invalid_signature"

        assert not PaymentSecurity.validate_stripe_signature(payload, signature, secret)

    def test_validate_yookassa_signature_valid(self):
        """Тест валидной подписи YooKassa."""
        request_body = 'test_body'
        secret = 'test_secret'

        expected_signature = hmac.new(
            secret.encode('utf-8'),
            request_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        assert PaymentSecurity.validate_yookassa_signature(request_body, expected_signature, secret)

    def test_validate_yookassa_signature_invalid(self):
        """Тест невалидной подписи YooKassa."""
        request_body = 'test_body'
        secret = 'test_secret'
        signature = 'invalid_signature'

        assert not PaymentSecurity.validate_yookassa_signature(request_body, signature, secret)

    def test_validate_sbp_signature_valid(self):
        """Тест валидной подписи СБП."""
        request_body = 'test_body'
        secret = 'test_secret'

        # СБП использует base64-encoded HMAC-SHA256
        expected_hmac = hmac.new(
            secret.encode('utf-8'),
            request_body.encode('utf-8'),
            hashlib.sha256
        )
        import base64
        expected_signature = base64.b64encode(expected_hmac.digest()).decode('utf-8')

        assert PaymentSecurity.validate_sbp_signature(request_body, expected_signature, secret)

    def test_validate_sbp_signature_invalid(self):
        """Тест невалидной подписи СБП."""
        request_body = 'test_body'
        secret = 'test_secret'
        signature = 'invalid_signature'

        assert not PaymentSecurity.validate_sbp_signature(request_body, signature, secret)

    @patch('core.payment_security.datetime')
    def test_generate_idempotency_key(self, mock_datetime):
        """Тест генерации ключа идемпотентности."""
        # Мокаем datetime для предсказуемого результата
        mock_datetime.now.return_value.timestamp.return_value = 1234567890.0

        payment_data = {
            'user_id': 123,
            'amount': 100.0
        }

        key1 = PaymentSecurity.generate_idempotency_key(payment_data)

        # Изменяем timestamp
        mock_datetime.now.return_value.timestamp.return_value = 1234567891.0
        key2 = PaymentSecurity.generate_idempotency_key(payment_data)

        # Ключи должны быть разными из-за timestamp
        assert key1 != key2
        assert len(key1) == 16
        assert len(key2) == 16

    def test_sanitize_payment_data(self):
        """Тест очистки платежных данных."""
        payment_data = {
            'user_id': 123,
            'amount': 100.0,
            'card_number': '1234567890123456',
            'cvv': '123',
            'cardholder_name': 'John Doe',
            'api_key': 'secret_key',
            'normal_field': 'normal_value'
        }

        sanitized = PaymentSecurity.sanitize_payment_data(payment_data)

        assert sanitized['card_number'] == '**** **** **** 3456'
        assert sanitized['cvv'] == '***'
        assert sanitized['cardholder_name'] == '***'
        assert sanitized['api_key'] == '***'
        assert sanitized['user_id'] == 123
        assert sanitized['amount'] == 100.0
        assert sanitized['normal_field'] == 'normal_value'

    def test_validate_amount_range(self):
        """Тест проверки диапазона суммы."""
        assert PaymentSecurity.validate_amount_range(100.0)
        assert PaymentSecurity.validate_amount_range(1.0)
        assert PaymentSecurity.validate_amount_range(100000.0)
        assert not PaymentSecurity.validate_amount_range(0.5)
        assert not PaymentSecurity.validate_amount_range(200000.0)

    def test_validate_currency(self):
        """Тест проверки валюты."""
        assert PaymentSecurity.validate_currency('RUB')
        assert PaymentSecurity.validate_currency('USD')
        assert PaymentSecurity.validate_currency('EUR')
        assert not PaymentSecurity.validate_currency('BTC')
        assert PaymentSecurity.validate_currency('rub', ['RUB', 'USD'])

    def test_detect_suspicious_activity(self):
        """Тест обнаружения подозрительной активности."""
        payment_data = {'amount': 100.0}
        recent_payments = []

        result = PaymentSecurity.detect_suspicious_activity(payment_data, recent_payments)
        assert not result['is_suspicious']

        # Тест с круглой суммой
        payment_data_round = {'amount': 5000.0}
        result_round = PaymentSecurity.detect_suspicious_activity(payment_data_round, recent_payments)
        assert result_round['is_suspicious']
        assert 'round_amount_suspicious' in result_round['reasons']

    def test_encrypt_sensitive_data_success(self):
        """Тест успешного шифрования данных."""
        data = 'test_sensitive_data'
        key = 'test_encryption_key_32_chars_long'

        encrypted = PaymentSecurity.encrypt_sensitive_data(data, key)
        assert encrypted != data
        assert isinstance(encrypted, str)

        # Проверяем, что можем расшифровать обратно
        decrypted = PaymentSecurity.decrypt_sensitive_data(encrypted, key)
        assert decrypted == data

    def test_decrypt_sensitive_data_success(self):
        """Тест успешной расшифровки данных."""
        original_data = 'another_test_data'
        key = 'another_test_key_32_chars_long'

        # Шифруем и расшифровываем
        encrypted = PaymentSecurity.encrypt_sensitive_data(original_data, key)
        decrypted = PaymentSecurity.decrypt_sensitive_data(encrypted, key)

        assert decrypted == original_data

    def test_encrypt_decrypt_with_different_keys(self):
        """Тест шифрования с разными ключами."""
        data = 'test_data'
        key1 = 'key_one_12345678901234567890123456789012'
        key2 = 'key_two_12345678901234567890123456789012'

        encrypted1 = PaymentSecurity.encrypt_sensitive_data(data, key1)
        encrypted2 = PaymentSecurity.encrypt_sensitive_data(data, key2)

        # Шифртексты должны быть разными
        assert encrypted1 != encrypted2

        # Расшифровка с правильными ключами
        assert PaymentSecurity.decrypt_sensitive_data(encrypted1, key1) == data
        assert PaymentSecurity.decrypt_sensitive_data(encrypted2, key2) == data

    def test_encrypt_with_short_key(self):
        """Тест шифрования с коротким ключом (должен работать через SHA256)."""
        data = 'test_data'
        short_key = 'short_key'

        encrypted = PaymentSecurity.encrypt_sensitive_data(data, short_key)
        decrypted = PaymentSecurity.decrypt_sensitive_data(encrypted, short_key)

        assert decrypted == data

    @patch('core.payment_security.Fernet')
    def test_encrypt_without_cryptography(self, mock_fernet):
        """Тест поведения при отсутствии библиотеки cryptography."""
        # Имитируем отсутствие библиотеки
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == 'cryptography.fernet':
                raise ImportError("No module named 'cryptography'")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            data = 'test_data'
            key = 'test_key'

            with pytest.raises(Exception):  # PaymentSecurityError
                PaymentSecurity.encrypt_sensitive_data(data, key)


class TestFFmpegSecurity:
    """Тесты для проверок безопасности ffmpeg."""

    def test_validate_ffmpeg_command_valid(self):
        """Тест валидной команды ffmpeg."""
        command = ['ffmpeg', '-i', 'input.mp4', '-c:v', 'libx264', '-y', 'output.mp4']
        assert PaymentSecurity.validate_ffmpeg_command(command)

    def test_validate_ffmpeg_command_invalid_not_ffmpeg(self):
        """Тест команды не начинающейся с ffmpeg."""
        command = ['convert', '-i', 'input.mp4', 'output.mp4']
        assert not PaymentSecurity.validate_ffmpeg_command(command)

    def test_validate_ffmpeg_command_dangerous_patterns(self):
        """Тест обнаружения опасных паттернов."""
        dangerous_commands = [
            ['ffmpeg', '-i', '../../etc/passwd', 'output.mp4'],
            ['ffmpeg', '-i', 'input.mp4', '-y', '| rm -rf /'],
            ['ffmpeg', '-i', 'input.mp4; rm -rf /', 'output.mp4'],
            ['ffmpeg', '-i', 'input.mp4', '-f', 'srt', 'output.srt'],
        ]

        for command in dangerous_commands:
            assert not PaymentSecurity.validate_ffmpeg_command(command)

    def test_validate_ffmpeg_command_unsupported_format(self):
        """Тест неподдерживаемого формата файла."""
        command = ['ffmpeg', '-i', 'input.exe', 'output.mp4']
        assert not PaymentSecurity.validate_ffmpeg_command(command)

    def test_sanitize_ffmpeg_output_path_valid(self):
        """Тест санитизации валидного пути."""
        path = 'output.mp4'
        assert PaymentSecurity.sanitize_ffmpeg_output_path(path) == path

    def test_sanitize_ffmpeg_output_path_invalid(self):
        """Тест санитизации невалидного пути."""
        invalid_paths = [
            '../../etc/passwd',
            '/etc/passwd',
            'output.mp4|rm -rf /',
            'output.exe',
            'output; rm -rf /',
        ]

        for path in invalid_paths:
            assert PaymentSecurity.sanitize_ffmpeg_output_path(path) is None

    def test_secure_ffmpeg_execute_success(self):
        """Тест успешного выполнения безопасной команды ffmpeg."""
        # Мокаем subprocess.run для тестирования
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = type('MockResult', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

            command = ['ffmpeg', '-i', 'input.mp4', '-c:v', 'libx264', '-y', 'output.mp4']
            success, error = PaymentSecurity.secure_ffmpeg_execute(command)

            assert success
            assert error == ""
            mock_run.assert_called_once()

    def test_secure_ffmpeg_execute_validation_failure(self):
        """Тест выполнения с проваленной валидацией."""
        command = ['not_ffmpeg', 'bad_command']  # Не пройдет валидацию
        success, error = PaymentSecurity.secure_ffmpeg_execute(command)

        assert not success
        assert "validation failed" in error.lower()

    def test_secure_ffmpeg_execute_subprocess_error(self):
        """Тест выполнения с ошибкой subprocess."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=['ffmpeg'], timeout=300)

            command = ['ffmpeg', '-i', 'input.mp4', '-y', 'output.mp4']
            success, error = PaymentSecurity.secure_ffmpeg_execute(command, timeout_seconds=300)

            assert not success
            assert "timed out" in error.lower()


class TestPaymentRateLimiter:
    """Тесты для ограничителя частоты платежей."""

    def test_init(self):
        """Тест инициализации ограничителя."""
        limiter = PaymentRateLimiter(max_payments_per_hour=5, max_amount_per_hour=10000)
        assert limiter.max_payments_per_hour == 5
        assert limiter.max_amount_per_hour == 10000

    def test_check_rate_limit_allowed(self):
        """Тест проверки лимита для разрешенного платежа."""
        limiter = PaymentRateLimiter(max_payments_per_hour=2, max_amount_per_hour=1000)
        user_id = 123
        amount = 100.0

        result = limiter.check_rate_limit(user_id, amount)
        assert result['allowed']
        assert result['remaining_payments'] == 2
        assert result['remaining_amount'] == 900.0

    def test_check_rate_limit_exceeded_payments(self):
        """Тест превышения лимита по количеству платежей."""
        limiter = PaymentRateLimiter(max_payments_per_hour=2, max_amount_per_hour=1000)
        user_id = 123

        # Записываем первый платеж
        limiter.record_payment(user_id, 100.0)

        # Записываем второй платеж
        limiter.record_payment(user_id, 100.0)

        # Проверяем лимит для третьего платежа - должен быть превышен
        result = limiter.check_rate_limit(user_id, 100.0)
        assert not result['allowed']

    def test_check_rate_limit_exceeded_amount(self):
        """Тест превышения лимита по сумме."""
        limiter = PaymentRateLimiter(max_payments_per_hour=10, max_amount_per_hour=500)
        user_id = 123

        # Большой платеж
        result = limiter.check_rate_limit(user_id, 600.0)
        assert not result['allowed']

    def test_record_payment(self):
        """Тест записи платежа."""
        limiter = PaymentRateLimiter()
        user_id = 123
        amount = 100.0

        limiter.record_payment(user_id, amount)

        assert user_id in limiter._counters
        assert len(limiter._counters[user_id]['payments']) == 1
        assert len(limiter._counters[user_id]['amounts']) == 1
        assert limiter._counters[user_id]['amounts'][0][1] == amount
"""
Система валидации данных для телеграм-бота.
Обеспечивает безопасность и корректность входящих данных.
"""

import re
from typing import Optional, Union, List


class ValidationError(Exception):
    """Исключение валидации данных"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


class Validator:
    """Базовый класс для валидаторов"""

    @staticmethod
    def validate_string_length(text: str, min_length: int = 0, max_length: int = 1000) -> bool:
        """Валидация длины строки"""
        if not isinstance(text, str):
            return False
        return min_length <= len(text) <= max_length

    @staticmethod
    def validate_numeric_range(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> bool:
        """Валидация числового диапазона"""
        try:
            numeric_value = float(value)
            return min_val <= numeric_value <= max_val
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_user_id(user_id: Union[int, str]) -> bool:
        """Валидация ID пользователя Telegram"""
        try:
            uid = int(user_id)
            return 1 <= uid <= 2147483647  # Диапазон Telegram user ID
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_chat_id(chat_id: Union[int, str]) -> bool:
        """Валидация ID чата Telegram"""
        try:
            cid = int(chat_id)
            return -2147483648 <= cid <= 2147483647  # Диапазон Telegram chat ID
        except (ValueError, TypeError):
            return False


class InputValidator:
    """Валидатор пользовательского ввода"""

    # Регулярные выражения для валидации
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$|^[a-zA-Z0-9._%+-]+@localhost$')
    PHONE_PATTERN = re.compile(r'^\+?[\d\s\-\(\)]{10,}$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Валидация email адреса"""
        return bool(cls.EMAIL_PATTERN.match(email)) if email else False

    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Валидация номера телефона"""
        return bool(cls.PHONE_PATTERN.match(phone)) if phone else False

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Валидация URL"""
        return bool(cls.URL_PATTERN.match(url)) if url else False

    @classmethod
    def validate_city_name(cls, city: str, max_length: int = 50) -> bool:
        """Валидация названия города"""
        if not city or not isinstance(city, str):
            return False

        # Проверка длины
        if len(city) < 2 or len(city) > max_length:
            return False

        # Проверка на наличие только допустимых символов (буквы, пробелы, дефисы)
        return bool(re.match(r'^[a-zA-Zа-яА-Я\s\-]+$', city))

    @classmethod
    def validate_username(cls, username: str) -> bool:
        """Валидация username Telegram"""
        if not username or not isinstance(username, str):
            return False

        # Username должен начинаться с буквы, содержать только буквы, цифры и подчеркивания
        # Длина от 5 до 32 символов
        if not (5 <= len(username) <= 32):
            return False

        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username))

    @classmethod
    def validate_text_content(cls, text: str, max_length: int = 4000) -> bool:
        """Валидация текстового контента"""
        if not text or not isinstance(text, str):
            return False

        # Проверка длины
        if len(text) > max_length:
            return False

        # Проверка на наличие потенциально опасных символов
        dangerous_chars = ['<', '>', '"', "'", '&']
        return not any(char in text for char in dangerous_chars)

    @classmethod
    def validate_donation_amount(cls, amount: Union[str, float]) -> bool:
        """Валидация суммы доната"""
        try:
            amount_float = float(amount)
            return 1.0 <= amount_float <= 100000.0  # От 1 рубля до 100k рублей
        except (ValueError, TypeError):
            return False

    @classmethod
    def validate_time_format(cls, time_str: str) -> bool:
        """Валидация формата времени"""
        if not time_str or not isinstance(time_str, str):
            return False

        # Проверяем форматы: YYYY-MM-DD HH:MM:SS, YYYY-MM-DD HH:MM, +30m, +2h, +1d
        patterns = [
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$',  # Абсолютное время
            r'^\+(\d+)[mhd]$'  # Относительное время
        ]

        return any(re.match(pattern, time_str) for pattern in patterns)

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Очистка имени файла от опасных символов"""
        if not filename:
            return "unnamed_file"

        # Оставляем только безопасные символы
        safe_chars = re.sub(r'[^\w\.\-\s]', '', filename)
        return safe_chars.strip() or "unnamed_file"

    @classmethod
    def validate_csv_filename(cls, filename: str) -> bool:
        """Валидация имени CSV файла"""
        if not filename or not isinstance(filename, str):
            return False

        # Проверка длины
        if len(filename) > 255:
            return False

        # Проверка на наличие только безопасных символов
        return bool(re.match(r'^[a-zA-Z0-9._\-/\s]+$', filename))

    @classmethod
    def validate_error_type(cls, error_type: str) -> bool:
        """Валидация типа ошибки"""
        if not error_type or not isinstance(error_type, str):
            return False
        valid_types = ['bug', 'feature', 'crash', 'ui', 'security', 'improvement', 'other']
        return error_type.lower() in valid_types

    @classmethod
    def validate_priority(cls, priority: str) -> bool:
        """Валидация приоритета"""
        valid_priorities = ['low', 'medium', 'high', 'critical']
        return priority.lower() in valid_priorities
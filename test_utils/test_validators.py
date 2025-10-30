"""
Тесты для модуля валидации данных.
Проверяет корректность работы всех функций валидации.
"""

import pytest
from utils.validators import Validator, InputValidator
from core.exceptions import ValidationError


class TestValidator:
    """Тесты базового класса Validator"""

    def test_validate_string_length_valid(self):
        """Тест валидации корректной длины строки"""
        assert Validator.validate_string_length("test", 1, 10) is True
        assert Validator.validate_string_length("", 0, 10) is True
        assert Validator.validate_string_length("a" * 1000, 0, 1000) is True

    def test_validate_string_length_invalid(self):
        """Тест валидации некорректной длины строки"""
        assert Validator.validate_string_length("", 1, 10) is False
        assert Validator.validate_string_length("test", 10, 1) is False
        assert Validator.validate_string_length("a" * 1001, 0, 1000) is False
        assert Validator.validate_string_length(None, 0, 10) is False

    def test_validate_numeric_range_valid(self):
        """Тест валидации корректного числового диапазона"""
        assert Validator.validate_numeric_range(5, 1, 10) is True
        assert Validator.validate_numeric_range(1, 1, 10) is True
        assert Validator.validate_numeric_range(10, 1, 10) is True
        assert Validator.validate_numeric_range(5.5, 1.0, 10.0) is True

    def test_validate_numeric_range_invalid(self):
        """Тест валидации некорректного числового диапазона"""
        assert Validator.validate_numeric_range(0, 1, 10) is False
        assert Validator.validate_numeric_range(15, 1, 10) is False
        assert Validator.validate_numeric_range("not_a_number", 1, 10) is False
        assert Validator.validate_numeric_range(None, 1, 10) is False

    def test_validate_user_id_valid(self):
        """Тест валидации корректного ID пользователя"""
        assert Validator.validate_user_id(123456789) is True
        assert Validator.validate_user_id("123456789") is True
        assert Validator.validate_user_id(1) is True
        assert Validator.validate_user_id(2147483647) is True

    def test_validate_user_id_invalid(self):
        """Тест валидации некорректного ID пользователя"""
        assert Validator.validate_user_id(0) is False
        assert Validator.validate_user_id(-1) is False
        assert Validator.validate_user_id(2147483648) is False
        assert Validator.validate_user_id("not_a_number") is False
        assert Validator.validate_user_id(None) is False


class TestInputValidator:
    """Тесты класса InputValidator"""

    def test_validate_email_valid(self):
        """Тест валидации корректных email адресов"""
        assert InputValidator.validate_email("test@example.com") is True
        assert InputValidator.validate_email("user.name+tag@domain.co.uk") is True
        assert InputValidator.validate_email("admin@localhost") is True

    def test_validate_email_invalid(self):
        """Тест валидации некорректных email адресов"""
        assert InputValidator.validate_email("") is False
        assert InputValidator.validate_email("invalid-email") is False
        assert InputValidator.validate_email("@example.com") is False
        assert InputValidator.validate_email("test@") is False
        assert InputValidator.validate_email("test.example.com") is False

    def test_validate_phone_valid(self):
        """Тест валидации корректных номеров телефона"""
        assert InputValidator.validate_phone("+7 999 123-45-67") is True
        assert InputValidator.validate_phone("8(999)1234567") is True
        assert InputValidator.validate_phone("+1234567890") is True
        assert InputValidator.validate_phone("1234567890") is True

    def test_validate_phone_invalid(self):
        """Тест валидации некорректных номеров телефона"""
        assert InputValidator.validate_phone("") is False
        assert InputValidator.validate_phone("123") is False
        assert InputValidator.validate_phone("phone") is False
        assert InputValidator.validate_phone("+123") is False

    def test_validate_url_valid(self):
        """Тест валидации корректных URL"""
        assert InputValidator.validate_url("https://example.com") is True
        assert InputValidator.validate_url("http://localhost:8080") is True
        assert InputValidator.validate_url("https://sub.domain.org/path") is True

    def test_validate_url_invalid(self):
        """Тест валидации некорректных URL"""
        assert InputValidator.validate_url("") is False
        assert InputValidator.validate_url("not-a-url") is False
        assert InputValidator.validate_url("ftp://example.com") is False
        assert InputValidator.validate_url("https://") is False

    def test_validate_city_name_valid(self):
        """Тест валидации корректных названий городов"""
        assert InputValidator.validate_city_name("Москва") is True
        assert InputValidator.validate_city_name("New York") is True
        assert InputValidator.validate_city_name("Санкт-Петербург") is True
        assert InputValidator.validate_city_name("Saint-Petersburg") is True

    def test_validate_city_name_invalid(self):
        """Тест валидации некорректных названий городов"""
        assert InputValidator.validate_city_name("") is False
        assert InputValidator.validate_city_name("A") is False
        assert InputValidator.validate_city_name("A" * 51) is False
        assert InputValidator.validate_city_name("City123") is False
        assert InputValidator.validate_city_name("City@Name") is False

    def test_validate_username_valid(self):
        """Тест валидации корректных username"""
        assert InputValidator.validate_username("user123") is True
        assert InputValidator.validate_username("test_user") is True
        assert InputValidator.validate_username("a" + "b" * 28) is True  # 30 символов

    def test_validate_username_invalid(self):
        """Тест валидации некорректных username"""
        assert InputValidator.validate_username("") is False
        assert InputValidator.validate_username("ab") is False  # слишком короткий
        assert InputValidator.validate_username("A" * 33) is False  # слишком длинный
        assert InputValidator.validate_username("user-name") is False  # дефис запрещен
        assert InputValidator.validate_username("user.name") is False  # точка запрещена
        assert InputValidator.validate_username("123user") is False  # не начинается с буквы

    def test_validate_text_content_valid(self):
        """Тест валидации корректного текстового контента"""
        assert InputValidator.validate_text_content("Привет мир!") is True
        assert InputValidator.validate_text_content("Текст с цифрами 123") is True
        assert InputValidator.validate_text_content("A" * 4000) is True

    def test_validate_text_content_invalid(self):
        """Тест валидации некорректного текстового контента"""
        assert InputValidator.validate_text_content("") is False
        assert InputValidator.validate_text_content("A" * 4001) is False
        assert InputValidator.validate_text_content("Текст с <script>") is False
        assert InputValidator.validate_text_content('Текст с "кавычками"') is False

    def test_validate_donation_amount_valid(self):
        """Тест валидации корректных сумм донатов"""
        assert InputValidator.validate_donation_amount(100.0) is True
        assert InputValidator.validate_donation_amount("100.5") is True
        assert InputValidator.validate_donation_amount(1.0) is True
        assert InputValidator.validate_donation_amount(100000.0) is True

    def test_validate_donation_amount_invalid(self):
        """Тест валидации некорректных сумм донатов"""
        assert InputValidator.validate_donation_amount(0) is False
        assert InputValidator.validate_donation_amount(-100) is False
        assert InputValidator.validate_donation_amount(100001) is False
        assert InputValidator.validate_donation_amount("not_a_number") is False

    def test_validate_time_format_valid(self):
        """Тест валидации корректных форматов времени"""
        assert InputValidator.validate_time_format("2024-01-15 14:30:00") is True
        assert InputValidator.validate_time_format("2024-01-15 14:30") is True
        assert InputValidator.validate_time_format("+30m") is True
        assert InputValidator.validate_time_format("+2h") is True
        assert InputValidator.validate_time_format("+1d") is True

    def test_validate_time_format_invalid(self):
        """Тест валидации некорректных форматов времени"""
        assert InputValidator.validate_time_format("") is False
        assert InputValidator.validate_time_format("invalid") is False
        assert InputValidator.validate_time_format("15-01-2024 14:30") is False
        assert InputValidator.validate_time_format("+30x") is False

    def test_sanitize_filename(self):
        """Тест очистки имени файла"""
        assert InputValidator.sanitize_filename("test.txt") == "test.txt"
        assert InputValidator.sanitize_filename("file with spaces.txt") == "file with spaces.txt"
        assert InputValidator.sanitize_filename("file/with/path.txt") == "filewithpath.txt"
        assert InputValidator.sanitize_filename("file<>:|?.txt") == "file.txt"
        assert InputValidator.sanitize_filename("") == "unnamed_file"

    def test_validate_csv_filename_valid(self):
        """Тест валидации корректных имен CSV файлов"""
        assert InputValidator.validate_csv_filename("data.csv") is True
        assert InputValidator.validate_csv_filename("backup_data_2024.csv") is True
        assert InputValidator.validate_csv_filename("path/to/file.csv") is True

    def test_validate_csv_filename_invalid(self):
        """Тест валидации некорректных имен CSV файлов"""
        assert InputValidator.validate_csv_filename("") is False
        assert InputValidator.validate_csv_filename("A" * 256) is False
        assert InputValidator.validate_csv_filename("file<name>.csv") is False
        assert InputValidator.validate_csv_filename("file*.csv") is False

    def test_validate_error_type_valid(self):
        """Тест валидации корректных типов ошибок"""
        assert InputValidator.validate_error_type("bug") is True
        assert InputValidator.validate_error_type("Bug") is True  # регистронезависимый
        assert InputValidator.validate_error_type("feature") is True
        assert InputValidator.validate_error_type("crash") is True

    def test_validate_error_type_invalid(self):
        """Тест валидации некорректных типов ошибок"""
        assert InputValidator.validate_error_type("invalid") is False
        assert InputValidator.validate_error_type("") is False
        assert InputValidator.validate_error_type(None) is False
        assert InputValidator.validate_error_type("not_valid") is False

    def test_validate_priority_valid(self):
        """Тест валидации корректных приоритетов"""
        assert InputValidator.validate_priority("low") is True
        assert InputValidator.validate_priority("High") is True  # регистронезависимый
        assert InputValidator.validate_priority("CRITICAL") is True

    def test_validate_priority_invalid(self):
        """Тест валидации некорректных приоритетов"""
        assert InputValidator.validate_priority("invalid") is False
        assert InputValidator.validate_priority("") is False
        assert InputValidator.validate_priority("medium") is True  # medium валиден
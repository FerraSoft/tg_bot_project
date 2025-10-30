"""
Тесты для системы исключений.
Проверяет корректность создания и обработки кастомных исключений.
"""

import pytest
from core.exceptions import (
    BotException, DatabaseError, ValidationError,
    ConfigurationError, APIError, GameError,
    ModerationError, PermissionError
)


class TestBotException:
    """Тесты базового исключения BotException"""

    def test_bot_exception_creation(self):
        """Тест создания базового исключения"""
        exception = BotException("Тестовая ошибка", "TEST_ERROR")

        assert str(exception) == "Тестовая ошибка"
        assert exception.error_code == "TEST_ERROR"
        assert exception.message == "Тестовая ошибка"

    def test_bot_exception_default_code(self):
        """Тест базового исключения с кодом по умолчанию"""
        exception = BotException("Тестовая ошибка")

        assert exception.error_code is None
        assert str(exception) == "Тестовая ошибка"


class TestDatabaseError:
    """Тесты исключения базы данных"""

    def test_database_error_creation(self):
        """Тест создания исключения базы данных"""
        original_error = ValueError("Connection failed")
        exception = DatabaseError("Ошибка подключения", original_error)

        assert str(exception) == "Ошибка подключения"
        assert exception.error_code == "DATABASE_ERROR"
        assert exception.original_error == original_error

    def test_database_error_without_original(self):
        """Тест исключения базы данных без оригинальной ошибки"""
        exception = DatabaseError("Ошибка запроса")

        assert exception.original_error is None
        assert exception.error_code == "DATABASE_ERROR"


class TestValidationError:
    """Тесты исключения валидации"""

    def test_validation_error_creation(self):
        """Тест создания исключения валидации"""
        exception = ValidationError("Неверное значение", "email")

        assert str(exception) == "Неверное значение"
        assert exception.error_code == "VALIDATION_ERROR"
        assert exception.field == "email"

    def test_validation_error_without_field(self):
        """Тест исключения валидации без указания поля"""
        exception = ValidationError("Общая ошибка валидации")

        assert exception.field is None


class TestConfigurationError:
    """Тесты исключения конфигурации"""

    def test_configuration_error_creation(self):
        """Тест создания исключения конфигурации"""
        exception = ConfigurationError("Не найден токен", "BOT_TOKEN")

        assert str(exception) == "Не найден токен"
        assert exception.error_code == "CONFIG_ERROR"
        assert exception.config_key == "BOT_TOKEN"


class TestAPIError:
    """Тесты исключения API"""

    def test_api_error_creation(self):
        """Тест создания исключения API"""
        exception = APIError("Превышен лимит", "openweather", 429)

        assert str(exception) == "Превышен лимит"
        assert exception.error_code == "API_ERROR"
        assert exception.api_name == "openweather"
        assert exception.status_code == 429

    def test_api_error_minimal(self):
        """Тест минимального исключения API"""
        exception = APIError("Ошибка API")

        assert exception.api_name is None
        assert exception.status_code is None


class TestGameError:
    """Тесты исключения игр"""

    def test_game_error_creation(self):
        """Тест создания исключения игры"""
        exception = GameError("Неверный ход", "tictactoe")

        assert str(exception) == "Неверный ход"
        assert exception.error_code == "GAME_ERROR"
        assert exception.game_name == "tictactoe"


class TestModerationError:
    """Тесты исключения модерации"""

    def test_moderation_error_creation(self):
        """Тест создания исключения модерации"""
        exception = ModerationError("Недостаточно прав", "ban")

        assert str(exception) == "Недостаточно прав"
        assert exception.error_code == "MODERATION_ERROR"
        assert exception.action == "ban"


class TestPermissionError:
    """Тесты исключения прав доступа"""

    def test_permission_error_creation(self):
        """Тест создания исключения прав доступа"""
        exception = PermissionError("Доступ запрещен", "admin")

        assert str(exception) == "Доступ запрещен"
        assert exception.error_code == "PERMISSION_ERROR"
        assert exception.required_permission == "admin"


class TestExceptionHierarchy:
    """Тесты иерархии исключений"""

    def test_exception_inheritance(self):
        """Тест наследования исключений"""
        # Все исключения должны наследоваться от BotException
        assert issubclass(DatabaseError, BotException)
        assert issubclass(ValidationError, BotException)
        assert issubclass(ConfigurationError, BotException)
        assert issubclass(APIError, BotException)
        assert issubclass(GameError, BotException)
        assert issubclass(ModerationError, BotException)
        assert issubclass(PermissionError, BotException)

    def test_base_exception_inheritance(self):
        """Тест наследования от базового Exception"""
        # BotException должен наследоваться от Exception
        assert issubclass(BotException, Exception)

        # Все остальные исключения тоже должны наследоваться от Exception
        assert issubclass(DatabaseError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(ConfigurationError, Exception)
        assert issubclass(APIError, Exception)
        assert issubclass(GameError, Exception)
        assert issubclass(ModerationError, Exception)
        assert issubclass(PermissionError, Exception)


class TestExceptionUsage:
    """Тесты использования исключений"""

    def test_exception_with_message_only(self):
        """Тест исключения только с сообщением"""
        exception = ValidationError("Ошибка валидации")
        assert str(exception) == "Ошибка валидации"
        assert exception.field is None

    def test_exception_with_all_fields(self):
        """Тест исключения со всеми полями"""
        exception = APIError("Ошибка API", "telegram", 500)

        assert exception.message == "Ошибка API"
        assert exception.api_name == "telegram"
        assert exception.status_code == 500
        assert exception.error_code == "API_ERROR"

    def test_exception_error_codes(self):
        """Тест кодов ошибок всех типов исключений"""
        exceptions = [
            (DatabaseError("DB Error"), "DATABASE_ERROR"),
            (ValidationError("Validation Error"), "VALIDATION_ERROR"),
            (ConfigurationError("Config Error"), "CONFIG_ERROR"),
            (APIError("API Error"), "API_ERROR"),
            (GameError("Game Error"), "GAME_ERROR"),
            (ModerationError("Moderation Error"), "MODERATION_ERROR"),
            (PermissionError("Permission Error"), "PERMISSION_ERROR")
        ]

        for exception, expected_code in exceptions:
            assert exception.error_code == expected_code
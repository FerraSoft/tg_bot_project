"""
Кастомные исключения для телеграм-бота.
Обеспечивают единообразную обработку ошибок во всем приложении.
"""


class BotException(Exception):
    """Базовое исключение для всех ошибок бота"""

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class DatabaseError(BotException):
    """Ошибки работы с базой данных"""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, "DATABASE_ERROR")
        self.original_error = original_error


class ValidationError(BotException):
    """Ошибки валидации данных"""

    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class ConfigurationError(BotException):
    """Ошибки конфигурации"""

    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key


class APIError(BotException):
    """Ошибки внешних API"""

    def __init__(self, message: str, api_name: str = None, status_code: int = None):
        super().__init__(message, "API_ERROR")
        self.api_name = api_name
        self.status_code = status_code


class GameError(BotException):
    """Ошибки игровых механик"""

    def __init__(self, message: str, game_name: str = None):
        super().__init__(message, "GAME_ERROR")
        self.game_name = game_name


class ModerationError(BotException):
    """Ошибки системы модерации"""

    def __init__(self, message: str, action: str = None):
        super().__init__(message, "MODERATION_ERROR")
        self.action = action


class PermissionError(BotException):
    """Ошибки доступа и прав"""

    def __init__(self, message: str, required_permission: str = None):
        super().__init__(message, "PERMISSION_ERROR")
        self.required_permission = required_permission
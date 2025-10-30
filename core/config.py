"""
Система управления конфигурацией телеграм-бота.
Поддерживает загрузку из переменных окружения и файлов конфигурации.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .exceptions import ConfigurationError


@dataclass
class APIKeys:
    """Ключи внешних API"""
    openweather: Optional[str] = None
    news: Optional[str] = None
    openai: Optional[str] = None

    def is_configured(self, service: str) -> bool:
        """Проверяет, настроен ли сервис"""
        return getattr(self, service.lower()) is not None


@dataclass
class BotConfig:
    """Основная конфигурация бота"""
    token: str
    admin_ids: list[int]
    moderator_ids: list[int] = None
    super_admin_ids: list[int] = None
    developer_chat_id: Optional[int] = None
    enable_ai_processing: bool = False
    enable_developer_notifications: bool = False
    enable_sentry: bool = False
    sentry_dsn: Optional[str] = None
    prometheus_port: int = 8000

    def __post_init__(self):
        if self.moderator_ids is None:
            self.moderator_ids = []
        if self.super_admin_ids is None:
            self.super_admin_ids = []


class Config:
    """
    Централизованная система конфигурации.

    Поддерживает:
    - Переменные окружения
    - JSON файлы конфигурации
    - Валидацию обязательных параметров
    - Безопасное хранение чувствительных данных
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация конфигурации.

        Args:
            config_path: Путь к файлу конфигурации (опционально)
        """
        self.config_path = config_path or "telegram_bot/config_local.py"
        self._config = {}
        self._load_configuration()

    def _load_configuration(self):
        """Загрузка конфигурации из всех источников"""
        # Загружаем переменные окружения
        self._load_from_environment()

        # Загружаем из файла конфигурации
        self._load_from_file()

        # Валидируем обязательные параметры
        self._validate_required_config()

    def _load_from_environment(self):
        """Загрузка конфигурации из переменных окружения"""
        # Базовые настройки бота
        if token := os.getenv('BOT_TOKEN'):
            self._config['bot_token'] = token

        if admin_ids := os.getenv('ADMIN_IDS'):
            try:
                self._config['admin_ids'] = [
                    int(id_str.strip()) for id_str in admin_ids.split(',')
                ]
            except ValueError as e:
                raise ConfigurationError(f"Неверный формат ADMIN_IDS: {e}")

        if moderator_ids := os.getenv('MODERATOR_IDS'):
            try:
                self._config['moderator_ids'] = [
                    int(id_str.strip()) for id_str in moderator_ids.split(',')
                ]
            except ValueError as e:
                raise ConfigurationError(f"Неверный формат MODERATOR_IDS: {e}")

        if super_admin_ids := os.getenv('SUPER_ADMIN_IDS'):
            try:
                self._config['super_admin_ids'] = [
                    int(id_str.strip()) for id_str in super_admin_ids.split(',')
                ]
            except ValueError as e:
                raise ConfigurationError(f"Неверный формат SUPER_ADMIN_IDS: {e}")

        if dev_id := os.getenv('DEVELOPER_CHAT_ID'):
            try:
                self._config['developer_chat_id'] = int(dev_id)
            except ValueError as e:
                raise ConfigurationError(f"Неверный формат DEVELOPER_CHAT_ID: {e}")

        # Флаги функций
        self._config['enable_developer_notifications'] = self._str_to_bool(
            os.getenv('ENABLE_DEVELOPER_NOTIFICATIONS', 'false')
        )
        self._config['enable_ai_error_processing'] = self._str_to_bool(
            os.getenv('ENABLE_AI_ERROR_PROCESSING', 'false')
        )
        self._config['enable_sentry'] = self._str_to_bool(
            os.getenv('ENABLE_SENTRY', 'false')
        )
        self._config['sentry_dsn'] = os.getenv('SENTRY_DSN')
        self._config['prometheus_port'] = int(os.getenv('PROMETHEUS_PORT', '8000'))

        # API ключи
        self._config['api_keys'] = {
            'openweather': os.getenv('OPENWEATHER_API_KEY'),
            'news': os.getenv('NEWS_API_KEY'),
            'openai': os.getenv('OPENAI_API_KEY')
        }

    def _load_from_file(self):
        """Загрузка конфигурации из Python файла"""
        if not os.path.exists(self.config_path):
            return

        try:
            # Используем importlib для безопасной загрузки модуля
            import importlib.util

            spec = importlib.util.spec_from_file_location("config", self.config_path)
            if spec and spec.loader:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)

                # Извлекаем переменные из модуля
                if hasattr(config_module, 'BOT_TOKEN'):
                    self._config['bot_token'] = config_module.BOT_TOKEN

                if hasattr(config_module, 'ADMIN_IDS'):
                    admin_ids = config_module.ADMIN_IDS
                    print(f"[DEBUG] Loading ADMIN_IDS from file: {admin_ids}")
                    if isinstance(admin_ids, list):
                        self._config['admin_ids'] = admin_ids
                    elif isinstance(admin_ids, str):
                        self._config['admin_ids'] = [int(x.strip()) for x in admin_ids.split(',')]
                    print(f"[DEBUG] Set _config['admin_ids'] = {self._config.get('admin_ids')}")

                if hasattr(config_module, 'MODERATOR_IDS'):
                    moderator_ids = config_module.MODERATOR_IDS
                    if isinstance(moderator_ids, list):
                        self._config['moderator_ids'] = moderator_ids
                    elif isinstance(moderator_ids, str):
                        self._config['moderator_ids'] = [int(x.strip()) for x in moderator_ids.split(',')]

                if hasattr(config_module, 'SUPER_ADMIN_IDS'):
                    super_admin_ids = config_module.SUPER_ADMIN_IDS
                    print(f"[DEBUG] Loading SUPER_ADMIN_IDS from file: {super_admin_ids}")
                    if isinstance(super_admin_ids, list):
                        self._config['super_admin_ids'] = super_admin_ids
                    elif isinstance(super_admin_ids, str):
                        self._config['super_admin_ids'] = [int(x.strip()) for x in super_admin_ids.split(',')]
                    print(f"[DEBUG] Set _config['super_admin_ids'] = {self._config.get('super_admin_ids')}")

                if hasattr(config_module, 'DEVELOPER_CHAT_ID'):
                    self._config['developer_chat_id'] = config_module.DEVELOPER_CHAT_ID

                if hasattr(config_module, 'ENABLE_DEVELOPER_NOTIFICATIONS'):
                    self._config['enable_developer_notifications'] = config_module.ENABLE_DEVELOPER_NOTIFICATIONS

                if hasattr(config_module, 'OPENAI_API_KEY'):
                    self._config['api_keys']['openai'] = config_module.OPENAI_API_KEY

                if hasattr(config_module, 'ENABLE_AI_ERROR_PROCESSING'):
                    self._config['enable_ai_error_processing'] = config_module.ENABLE_AI_ERROR_PROCESSING

                if hasattr(config_module, 'ENABLE_SENTRY'):
                    self._config['enable_sentry'] = config_module.ENABLE_SENTRY

                if hasattr(config_module, 'SENTRY_DSN'):
                    self._config['sentry_dsn'] = config_module.SENTRY_DSN

                if hasattr(config_module, 'PROMETHEUS_PORT'):
                    self._config['prometheus_port'] = config_module.PROMETHEUS_PORT

                if hasattr(config_module, 'AI_MODEL'):
                    self._config['ai_model'] = config_module.AI_MODEL

        except Exception as e:
            raise ConfigurationError(f"Ошибка загрузки файла конфигурации: {e}")

    def _validate_required_config(self):
        """Валидация обязательных параметров конфигурации"""
        if not self._config.get('bot_token'):
            raise ConfigurationError("BOT_TOKEN обязателен для работы бота")

        # ADMIN_IDS обязателен только если нет SUPER_ADMIN_IDS
        if not self._config.get('admin_ids') and not self._config.get('super_admin_ids'):
            raise ConfigurationError("ADMIN_IDS или SUPER_ADMIN_IDS обязателен для работы бота")

    def _str_to_bool(self, value: str) -> bool:
        """Преобразование строки в булево значение"""
        return value.lower() in ('true', '1', 'yes', 'on')

    @property
    def bot_config(self) -> BotConfig:
        """Получение конфигурации бота"""
        return BotConfig(
            token=self._config['bot_token'],
            admin_ids=self._config.get('admin_ids', []),
            moderator_ids=self._config.get('moderator_ids', []),
            super_admin_ids=self._config.get('super_admin_ids', []),
            developer_chat_id=self._config.get('developer_chat_id'),
            enable_ai_processing=self._config.get('enable_ai_error_processing', False),
            enable_developer_notifications=self._config.get('enable_developer_notifications', False),
            enable_sentry=self._config.get('enable_sentry', False),
            sentry_dsn=self._config.get('sentry_dsn'),
            prometheus_port=self._config.get('prometheus_port', 8000)
        )

    @property
    def api_keys(self) -> APIKeys:
        """Получение ключей API"""
        keys = self._config.get('api_keys', {})
        return APIKeys(
            openweather=keys.get('openweather'),
            news=keys.get('news'),
            openai=keys.get('openai')
        )

    @property
    def ai_model(self) -> str:
        """Модель ИИ для обработки ошибок"""
        return self._config.get('ai_model', 'gpt-3.5-turbo')

    def get(self, key: str, default: Any = None) -> Any:
        """Получение значения конфигурации по ключу"""
        return self._config.get(key, default)

    def is_development(self) -> bool:
        """Проверка режима разработки"""
        return self._str_to_bool(os.getenv('DEVELOPMENT_MODE', 'false'))

    def is_production(self) -> bool:
        """Проверка продакшн режима"""
        return not self.is_development()

    def get_database_url(self) -> str:
        """Получение URL базы данных"""
        return os.getenv('DATABASE_URL', 'telegram_bot.db')

    def get_log_level(self) -> str:
        """Получение уровня логирования"""
        # Устанавливаем DEBUG уровень для детальной записи ошибок
        return os.getenv('LOG_LEVEL', 'DEBUG')

    def __repr__(self) -> str:
        """Строковое представление конфигурации"""
        return f"Config(bot_token={'***' if self._config.get('bot_token') else None}, admin_count={len(self._config.get('admin_ids', []))})"
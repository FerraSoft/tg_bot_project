"""
Основной класс приложения телеграм-бота.

Application - центральный компонент системы, отвечающий за:
- Инициализацию всех компонентов (сервисы, репозитории, маршрутизаторы)
- Настройку обработчиков команд, сообщений и callback'ов
- Управление жизненным циклом бота (запуск/остановка)
- Обработку ошибок и мониторинг
- Интеграцию с платежными сервисами и уведомлениями
# Глобальная переменная для доступа к экземпляру приложения
app_instance = None

Класс поддерживает гибкую настройку логирования через параметр log_level:
- ERROR: только критические ошибки
- WARNING: ошибки + предупреждения
- INFO: ошибки + предупреждения + информационные сообщения (по умолчанию)

Пример использования:
    app = Application(log_level='WARNING')
    app.run()
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application as TelegramApplication, ContextTypes
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Основные импорты
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any

# Импорты Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application as TelegramApplication, ContextTypes
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Импорты из текущего пакета
from .config import Config
from .exceptions import BotException, ConfigurationError
from metrics.monitoring import MetricsCollector, structured_logger, measure_time, error_handler
from metrics.alerts import AlertManager
from .single_instance import check_single_instance

# Репозитории
from database.repository import UserRepository, ScoreRepository, ErrorRepository

# Сервисы
from services.welcome_service import WelcomeService


class Application:
    """
    Основной класс приложения телеграм-бота.

    Архитектура:
    - Использует композицию для управления зависимостями (сервисы, репозитории)
    - Поддерживает две системы маршрутизации: старую и новую (unified_router)
    - Обеспечивает graceful shutdown и очистку ресурсов
    - Интегрируется с системами мониторинга и алертинга

    Атрибуты:
        config: Конфигурация приложения
        logger: Логгер с настраиваемым уровнем логирования
        user_service: Сервис управления пользователями
        game_service: Сервис игровых механик
        donation_service: Сервис платежей (опционально)
        telegram_app: Экземпляр Telegram Application
        unified_router: Новая система маршрутизации (опционально)

    Методы:
        run(): Запуск бота с polling
        stop(): Остановка бота
        get_status(): Получение статуса приложения
    """

    def __init__(self, config_path: Optional[str] = None, log_level: Optional[str] = None):
        """
        Инициализация приложения.

        Args:
            config_path: Путь к файлу конфигурации
            log_level: Уровень логирования (ERROR, WARNING, INFO, DEBUG). Если None, используется из конфигурации
        """
        self.config = Config(config_path)
        # Устанавливаем уровень логирования
        self.log_level = log_level or self.config.get_log_level()
        self.logger = structured_logger(__name__, self.config)
        # Настраиваем уровень логирования через стандартный механизм
        self.logger.setLevel(self._get_log_level_value())
        self.logger.info("Logger level set to: %s", self.log_level)

        # Инициализируем мониторинг
        self.metrics = MetricsCollector(self.config)
        self.logger.info("Monitoring system initialized")

        # Инициализируем систему алертов
        self.alert_manager = AlertManager(self.config, self.metrics)
        self.logger.info("Alert system initialized")

        # Инициализируем репозитории
        self.user_repo = UserRepository(self.config.get_database_url())
        self.score_repo = ScoreRepository(self.config.get_database_url())
        self.error_repo = ErrorRepository(self.config.get_database_url())

        # Импорт сервисов локально для избежания циклических импортов
        from services import UserService, GameService, ModerationService

        # Инициализируем сервисы
        # Создаем RoleService для управления ролями
        from services.role_service import RoleService
        self.role_service = RoleService(self.config.get_database_url())

        self.user_service = UserService(self.user_repo, self.score_repo, self.role_service)
        self.game_service = GameService(self.user_repo, self.score_repo)
        self.moderation_service = ModerationService(self.user_repo, self.score_repo)
        self.welcome_service = WelcomeService()

        # Инициализируем платежные сервисы (отключены для совместимости)
        # self._initialize_payment_services()
        self.donation_service = None
        self.notification_service = None
        self.trigger_service = None

        # Инициализируем новую систему маршрутизации
        self.logger.debug("Initializing unified_router...")
        self._initialize_unified_router()
        self.logger.debug(f"Unified router initialized: hasattr={hasattr(self, 'unified_router')}, value={getattr(self, 'unified_router', 'NOT_SET')}")

        # Убеждаемся что unified_router создан
        if not hasattr(self, 'unified_router') or self.unified_router is None:
            self.logger.warning("unified_router не инициализирован, создаем fallback")
            self.unified_router = None  # fallback to None for safety

        # Инициализируем обработчики (для обратной совместимости)
        self.handlers = self._initialize_handlers()

        # Сохраняем ссылку на экземпляр для доступа из других модулей
        global app_instance
        app_instance = self

        # Создаем Telegram Application
        self.telegram_app = TelegramApplication.builder().token(
            self.config.bot_config.token
        ).build()

        # Настраиваем обработчики
        self._setup_handlers()

        # Настраиваем новую систему маршрутизации
        self._setup_unified_router()

        # Запускаем сервер метрик
        self.metrics.start_metrics_server()

        self.logger.info("Приложение успешно инициализировано")
        self.logger.info("Новая система маршрутизации инициализирована")

    def _get_log_level_value(self) -> int:
        """Получение числового значения уровня логирования"""
        log_level_map = {
            'ERROR': logging.ERROR,
            'WARNING': logging.WARNING,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG
        }
        return log_level_map.get(self.log_level.upper(), logging.INFO)

    def _initialize_handlers(self) -> Dict[str, 'BaseHandler']:
        """Инициализация всех обработчиков"""
        handlers = {}

        # Импорт обработчиков локально для избежания циклических импортов
        from handlers import BaseHandler, UserHandlers, GameHandlers, AdminHandlers, ModerationHandlers
        self.logger.debug("_initialize_handlers - imports successful")

        try:
            handlers['user'] = UserHandlers(self.config, self.metrics, self.user_service, self.error_repo)
            handlers['game'] = GameHandlers(self.config, self.metrics, self.game_service)
            handlers['moderation'] = ModerationHandlers(self.config, self.metrics, self.user_service, self.moderation_service)
            handlers['admin'] = AdminHandlers(self.config, self.metrics, self.user_service, self.moderation_service)

            # Инициализируем PaymentHandler если доступны сервисы платежей
            if hasattr(self, 'donation_service') and self.donation_service:
                from handlers import PaymentHandler
                handlers['payment'] = PaymentHandler(self.donation_service)
                self.logger.info("PaymentHandler инициализирован")

            self.logger.info(f"Инициализировано {len(handlers)} обработчиков")
            return handlers

        except Exception as e:
            self.logger.error(f"Ошибка инициализации обработчиков: {e}")
            raise ConfigurationError(f"Не удалось инициализировать обработчики: {e}")

    def _initialize_unified_router(self):
        """Инициализация новой системы маршрутизации"""
        try:
            from .command_router import create_command_router
            from .message_router import create_message_router
            from .menu_manager import create_menu_manager
            from .permissions import permission_manager
            from utils.formatters import KeyboardFormatter

            # Создаем компоненты новой системы
            self.command_router = create_command_router(self.config, self.metrics)
            self.message_router = create_message_router()
            self.menu_manager = create_menu_manager(
                permission_manager, KeyboardFormatter()
            )

            # Создаем объединенный маршрутизатор
            from .unified_router import create_unified_router
            self.unified_router = create_unified_router(
                self.command_router, self.message_router, self.menu_manager
            )

        except NameError as e:
            if 'permission_manager' in str(e):
                self.logger.error("Ошибка импорта permission_manager. Проверьте permissions.py")
                raise ConfigurationError("permission_manager не найден. Проверьте импорты в permissions.py")
            else:
                raise
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации компонентов маршрутизации: {e}")
            # Продолжаем без новой системы маршрутизации
            self.command_router = None
            self.message_router = None
            self.menu_manager = None
            self.unified_router = None
            # Не вызываем raise, чтобы инициализация продолжилась
            self.logger.warning("Продолжаем инициализацию без новой системы маршрутизации")
            return

        except Exception as e:
            self.logger.error(f"Ошибка инициализации новой системы маршрутизации: {e}")
            # Продолжаем без unified_router, но создаем его как None для совместимости
            self.unified_router = None
            # Не вызываем raise, чтобы инициализация продолжилась
            self.logger.warning("Продолжаем инициализацию без unified_router")
            return

    def _setup_unified_router(self):
        """Настройка обработчиков новой системы маршрутизации"""
        if not self.command_router:
            self.logger.info("CommandRouter не инициализирован, пропускаем настройку unified router")
            return

        try:
            # Регистрируем обработчики команд через CommandRouter
            self._register_command_handlers()

            # Регистрируем обработчики сообщений через MessageTypeRouter
            self._register_message_handlers()

            # Регистрируем обработчики callback'ов
            self._register_callback_handlers()

            self.logger.info("Новая система маршрутизации настроена")

        except Exception as e:
            self.logger.error(f"Ошибка настройки новой системы маршрутизации: {e}")
            raise

    def _register_command_handlers(self):
        """Регистрация обработчиков команд"""
        if not self.command_router:
            return

        try:
            self.logger.debug("_register_command_handlers - imports successful")

            # Список типов обработчиков для регистрации
            handler_types = [
                ('user', 'UserHandlers', [self.config, self.metrics, self.user_service, self.error_repo]),
                ('game', 'GameHandlers', [self.config, self.metrics, self.game_service]),
                ('moderation', 'ModerationHandlers', [self.config, self.metrics, self.user_service, self.moderation_service]),
                ('admin', 'AdminHandlers', [self.config, self.metrics, self.user_service, self.moderation_service])
            ]

            for handler_name, class_name, init_args in handler_types:
                try:
                    # Импортируем класс обработчика
                    from handlers import UserHandlers, GameHandlers, AdminHandlers, ModerationHandlers
                    handler_class = locals()[class_name]

                    # Создаем экземпляр обработчика
                    handler_instance = handler_class(*init_args)

                    # Регистрируем все команды обработчика
                    for cmd, handler_func in handler_instance.get_command_handlers().items():
                        self.command_router.register_command_handler(cmd, handler_func)

                    self.logger.debug(f"Зарегистрированы команды {handler_name}: {len(handler_instance.get_command_handlers())}")

                except ImportError as e:
                    self.logger.warning(f"Не удалось импортировать {class_name}: {e}")
                except Exception as e:
                    self.logger.error(f"Ошибка при регистрации команд {handler_name}: {e}")

        except Exception as e:
            self.logger.error(f"Ошибка при регистрации командных обработчиков: {e}")
            raise

    def _register_message_handlers(self):
        """Регистрация обработчиков сообщений"""
        if not self.message_router:
            return

        try:
            self.logger.debug("_register_message_handlers - imports successful")

            # Создаем обработчик пользователей для сообщений
            from handlers import UserHandlers
            user_handlers = UserHandlers(self.config, self.metrics, self.user_service, self.error_repo)
            message_handlers = user_handlers.get_message_handlers()

            # Регистрируем обработчики по типам сообщений
            handler_mappings = {
                'text': lambda h: self.message_router.register_text_handler(
                    r'.*', h, priority=0, description='Обработка текстовых сообщений'
                ),
                'voice': lambda h: self.message_router.register_media_handler(
                    'voice', h, description='Обработка голосовых сообщений'
                )
            }

            for msg_type, handler in message_handlers.items():
                if msg_type in handler_mappings:
                    handler_mappings[msg_type](handler)
                    self.logger.debug(f"Зарегистрирован обработчик для {msg_type}")

        except ImportError as e:
            self.logger.error(f"Ошибка импорта обработчиков сообщений: {e}")
            raise ConfigurationError("Обработчики сообщений не найдены")
        except Exception as e:
            self.logger.error(f"Ошибка при регистрации обработчиков сообщений: {e}")
            raise

    def _register_callback_handlers(self):
        """Регистрация обработчиков callback'ов"""
        if not self.command_router:
            return

        try:
            self.logger.debug("_register_callback_handlers - imports successful")

            # Список обработчиков для callback'ов
            callback_handler_types = [
                ('user', 'UserHandlers', [self.config, self.metrics, self.user_service, self.error_repo]),
                ('game', 'GameHandlers', [self.config, self.metrics, self.game_service]),
                ('admin', 'AdminHandlers', [self.config, self.metrics, self.user_service, self.moderation_service])
            ]

            for handler_name, class_name, init_args in callback_handler_types:
                try:
                    # Импортируем класс обработчика
                    from handlers import UserHandlers, GameHandlers, AdminHandlers
                    handler_class = locals()[class_name]

                    # Создаем экземпляр обработчика
                    handler_instance = handler_class(*init_args)

                    # Регистрируем все callback'и обработчика
                    for callback, handler_func in handler_instance.get_callback_handlers().items():
                        self.command_router.register_callback_handler(callback, handler_func)

                    self.logger.debug(f"Зарегистрированы callback'и {handler_name}: {len(handler_instance.get_callback_handlers())}")

                except ImportError as e:
                    self.logger.warning(f"Не удалось импортировать {class_name}: {e}")
                except Exception as e:
                    self.logger.error(f"Ошибка при регистрации callback'ов {handler_name}: {e}")

        except Exception as e:
            self.logger.error(f"Ошибка при регистрации обработчиков callback'ов: {e}")
            raise

    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений (старая система для совместимости)"""

        # Получаем все обработчики из модулей
        all_command_handlers = {}
        all_callback_handlers = {}
        all_message_handlers = {}

        for handler_name, handler in self.handlers.items():
            try:
                # Получаем обработчики команд
                command_handlers = handler.get_command_handlers()
                all_command_handlers.update(command_handlers)

                # Получаем обработчики callback запросов
                callback_handlers = handler.get_callback_handlers()
                all_callback_handlers.update(callback_handlers)

                # Получаем обработчики сообщений
                message_handlers = handler.get_message_handlers()
                all_message_handlers.update(message_handlers)

                self.logger.info(f"Обработчик {handler_name}: команд - {len(command_handlers)}, "
                                f"callback - {len(callback_handlers)}, сообщений - {len(message_handlers)}")

            except Exception as e:
                self.logger.error(f"Ошибка настройки обработчика {handler_name}: {e}")
                raise

        # Регистрируем обработчики команд через новую систему
        for command, handler_func in all_command_handlers.items():
            # Команды обрабатываются через CommandRouter, но регистрируем fallback
            self.telegram_app.add_handler(CommandHandler(
                command,
                lambda update, context, cmd=command, h=handler_func: self._handle_command_fallback(update, context, cmd, h)
            ))

        # Регистрируем обработчики callback через новую систему маршрутизации
        if all_callback_handlers:
            self.telegram_app.add_handler(CallbackQueryHandler(
                lambda update, context: self._handle_callback_via_unified_router(update, context)
            ))

    def _initialize_payment_services(self):
        """Инициализация платежных сервисов"""
        try:
            from services import DonationService, NotificationService, TriggerService

            # Инициализируем платежные репозитории
            try:
                from database.payment_repository import PaymentRepository, TransactionRepository
                payment_repo = PaymentRepository(self.config.get_database_url())
                transaction_repo = TransactionRepository(self.config.get_database_url())

                # Конфигурация платежных провайдеров (пока отключены)
                payment_configs = {
                    'stripe': {'enabled': False},  # Можно настроить через config
                    'yookassa': {'enabled': False},
                    'sbp': {'enabled': False}
                }

                # Создаем экземпляр DonationService с правильными параметрами
                self.donation_service = DonationService(
                    payment_repo=payment_repo,
                    transaction_repo=transaction_repo,
                    user_service=self.user_service,
                    notification_service=None,  # будет добавлен позже
                    payment_configs=payment_configs
                )
                self.notification_service = NotificationService(self.config, self.user_repo)
                self.trigger_service = TriggerService(self.config, self.user_repo, self.notification_service)

                # Обновляем donation_service с notification_service
                self.donation_service.notification_service = self.notification_service

                self.logger.info("Сервисы платежей и уведомлений инициализированы")

            except ImportError:
                self.logger.warning("Базы данных платежей не найдены, сервисы платежей отключены")
                self._disable_payment_services()

        except ImportError as e:
            self.logger.warning(f"Сервисы платежей не найдены: {e}")
            self._disable_payment_services()

    def _disable_payment_services(self):
        """Отключение платежных сервисов"""
        self.donation_service = None
        self.notification_service = None
    def _register_message_handlers_in_telegram(self, all_message_handlers: Dict[str, callable]):
        """Регистрация обработчиков сообщений в Telegram Application"""
        # Регистрируем обработчики сообщений через новую систему
        for message_type, handler_func in all_message_handlers.items():
            if message_type == 'text':
                self.telegram_app.add_handler(MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    lambda update, context: self._handle_message_via_unified_router(update, context)
                ))
            elif message_type == 'voice':
                self.telegram_app.add_handler(MessageHandler(
                    filters.VOICE,
                    lambda update, context: self._handle_voice_via_unified_router(update, context)
                ))
            elif message_type == 'audio':
                self.telegram_app.add_handler(MessageHandler(filters.AUDIO, handler_func))
            elif message_type == 'video':
                self.telegram_app.add_handler(MessageHandler(filters.VIDEO, handler_func))
        self.trigger_service = None
        # Регистрируем обработчики сообщений
        self._register_message_handlers_in_telegram(all_message_handlers)

        # Регистрируем обработчики callback запросов
        if all_callback_handlers:
            self.telegram_app.add_handler(CallbackQueryHandler(
                lambda update, context: self._handle_callback_via_unified_router(update, context)
            ))

        # Добавляем обработчик новых участников чата
        if hasattr(filters, 'CHAT_MEMBER'):
            # Используем более современный подход для обработки новых участников
            from telegram.ext import ChatMemberHandler
            self.telegram_app.add_handler(ChatMemberHandler(
                self._handle_new_chat_members, ChatMemberHandler.CHAT_MEMBER
            ))

        # Добавляем обработчик инлайновых запросов
        from telegram.ext import InlineQueryHandler
        self.telegram_app.add_handler(InlineQueryHandler(self._handle_inline_query))

        # Добавляем обработчик ошибок
        self.telegram_app.add_error_handler(self._error_handler)

    async def _handle_command_fallback(self, update, context, command, handler):
        """Обработка команд через новую систему маршрутизации"""
        try:
            if hasattr(self, 'unified_router') and self.unified_router:
                await self.unified_router.handle_update(update, context)
            else:
                # Fallback к старому обработчику если unified_router недоступен
                await handler(update, context)
        except AttributeError as e:
            if "'Application' object has no attribute 'unified_router'" in str(e):
                self.logger.debug(f"unified_router не инициализирован, используем fallback для команды /{command}")
                self.logger.warning(f"unified_router не инициализирован, используем fallback для команды /{command}")
                # Fallback к старому обработчику
                await handler(update, context)
            else:
                self.logger.error(f"Error in unified command handler for /{command}: {e}")
                # Fallback к старому обработчику
                await handler(update, context)
        except Exception as e:
            self.logger.error(f"Error in unified command handler for /{command}: {e}")
            # Fallback к старому обработчику
            await handler(update, context)

    async def _handle_callback_via_unified_router(self, update, context):
        """Обработка callback'ов через новую систему"""
        try:
            # Сначала пробуем через CommandRouter (новая система)
            await self.command_router.handle_callback(update, context)
        except Exception as e:
            self.logger.error(f"Error in unified callback handler: {e}")
            # Fallback к старому диспетчеру
            await self._create_callback_dispatcher({})(update, context)

    async def _handle_message_via_unified_router(self, update, context):
        """Обработка текстовых сообщений через новую систему"""
        try:
            if hasattr(self, 'unified_router') and self.unified_router:
                await self.unified_router.handle_update(update, context)
            else:
                self.logger.debug("Unified router not available, skipping message routing")
        except Exception as e:
            self.logger.error(f"Error in unified message handler: {e}")

    async def _handle_voice_via_unified_router(self, update, context):
        """Обработка голосовых сообщений через новую систему"""
        try:
            if hasattr(self, 'unified_router') and self.unified_router:
                await self.unified_router.handle_update(update, context)
            else:
                self.logger.debug("Unified router not available, skipping voice message routing")
        except Exception as e:
            self.logger.error(f"Error in unified voice handler: {e}")

        self.logger.info("Все обработчики успешно зарегистрированы (новая система активна)")

    def _create_callback_dispatcher(self, callback_handlers: Dict[str, callable]):
        """Создание диспетчера callback запросов"""
        async def dispatcher(update: Update, context: ContextTypes):
            query = update.callback_query

            if query and query.data:
                callback_data = query.data

                # Находим подходящий обработчик
                for pattern, handler_func in callback_handlers.items():
                    if callback_data.startswith(pattern):
                        try:
                            start_time = time.time()
                            await handler_func(update, context)
                            duration = time.time() - start_time
                            self.metrics.record_command(callback_data, "callback", duration)
                            return
                        except Exception as e:
                            self.logger.error(f"Ошибка в callback обработчике {pattern}: {e}", exc_info=True)
                            self.logger.debug(f"Полная трассировка ошибки в {pattern}:", exc_info=True)
                            self.metrics.record_error(e.__class__.__name__, "callback", e)
                            try:
                                await query.edit_message_text("Произошла ошибка. Попробуйте позже.")
                            except Exception as edit_error:
                                self.logger.error(f"Не удалось отправить сообщение об ошибке: {edit_error}", exc_info=True)
                            return

                # Если не нашли подходящий обработчик
                await query.edit_message_text("Неизвестная команда.")

        return dispatcher

    async def _handle_new_chat_members(self, update: Update, context: ContextTypes):
        """Обработка новых участников чата"""
        try:
            # Проверяем, что есть новые участники
            if not update.chat_member or not update.chat_member.new_chat_members:
                return

            chat_id = update.effective_chat.id

            # Создаем приветственное сообщение с правилами и кнопками донатов
            welcome_text = self._get_welcome_message_with_rules()

            # Создаем клавиатуру с кнопками донатов
            donation_keyboard = [
                [InlineKeyboardButton("💰 100 ₽", callback_data='donate_100')],
                [InlineKeyboardButton("💰 500 ₽", callback_data='donate_500')],
                [InlineKeyboardButton("💰 1000 ₽", callback_data='donate_1000')],
                [InlineKeyboardButton("🎯 Помощь", callback_data='cmd_help')]
            ]
            reply_markup = InlineKeyboardMarkup(donation_keyboard)

            # Отправляем приветственное сообщение
            message = await update.effective_chat.send_message(
                welcome_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )

            # Обрабатываем каждого нового участника
            for member in update.chat_member.new_chat_members:
                # Добавляем пользователя в базу данных
                await self.user_service.user_repo._create_user_if_not_exists(
                    member.id, member.username, member.first_name, member.last_name
                )

                # Начисляем очки за вступление в чат
                await self.user_service.score_repo.update_score(member.id, 10)

            # Записываем метрику
            self.metrics.total_messages.labels(message_type='new_member').inc(len(update.chat_member.new_chat_members))

        except Exception as e:
            self.logger.error(f"Ошибка при обработке новых участников чата: {e}", exc_info=True)
            self.metrics.record_error(e.__class__.__name__, "new_chat_members", e)

    def _get_welcome_message_with_rules(self) -> str:
        """Генерация приветственного сообщения с правилами группы"""
        welcome_text = """🎉 <b>Добро пожаловать в нашу группу!</b>

👋 Приветствуем всех новых участников!

📋 <b>Правила нашей группы:</b>
• Соблюдайте уважительное общение
• Не используйте нецензурную лексику
• Спам и реклама запрещены
• Уважайте мнение других участников
• Используйте /help для получения справки о командах бота

🎮 В группе работает система рейтингов и игр!
🏆 Используйте /rank для просмотра вашего рейтинга

💰 <b>Поддержите проект:</b>
Если вам нравится бот, вы можете поддержать его развитие!

Используйте кнопки ниже для доната или команду /help для получения дополнительной информации."""
        return welcome_text

    async def _handle_inline_query(self, update: Update, context: ContextTypes):
        """Обработка инлайновых запросов"""
        try:
            query = update.inline_query.query
            results = []

            if not query:
                results.append(self._create_help_result())
            elif query.startswith('weather'):
                results.append(await self._handle_weather_query(query))
            elif query.startswith('translate'):
                results.append(await self._handle_translate_query(query))
            else:
                results.append(self._create_usage_result())

            await update.inline_query.answer(results)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке инлайнового запроса: {e}", exc_info=True)
            await update.inline_query.answer([])

    def _create_help_result(self):
        """Создание результата помощи для пустого запроса"""
        from telegram import InlineQueryResultArticle, InputTextMessageContent
        self.metrics.total_messages.labels(message_type='inline_help').inc()
        return InlineQueryResultArticle(
            id='1',
            title="Использование бота",
            input_message_content=InputTextMessageContent(
                "Используйте бота для получения погоды и перевода текста.\n\n"
                "Примеры:\n"
                "@your_bot weather Moscow\n"
                "@your_bot translate Hello world en\n"
                "@your_bot news"
            )
        )

    async def _handle_weather_query(self, query):
        """Обработка запроса погоды"""
        from telegram import InlineQueryResultArticle, InputTextMessageContent

        city = query.split(' ', 1)[1] if len(query.split(' ', 1)) > 1 else 'Moscow'

        # Валидация города
        if len(city) < 2:
            return InlineQueryResultArticle(
                id='1',
                title="Ошибка",
                input_message_content=InputTextMessageContent("Название города должно содержать минимум 2 символа")
            )
        elif len(city) > 50:
            return InlineQueryResultArticle(
                id='1',
                title="Ошибка",
                input_message_content=InputTextMessageContent("Название города слишком длинное")
            )

        # Проверка API ключа
        if not self.config.api_keys.openweather:
            return InlineQueryResultArticle(
                id='1',
                title="API недоступен",
                input_message_content=InputTextMessageContent("API погоды не настроен")
            )

        try:
            import requests
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.config.api_keys.openweather}&units=metric&lang=ru"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('cod') == 200:
                    weather_text = self._format_weather_text(data)
                    return InlineQueryResultArticle(
                        id='1',
                        title=f"Погода в {city}",
                        input_message_content=InputTextMessageContent(weather_text)
                    )
                else:
                    return InlineQueryResultArticle(
                        id='1',
                        title="Город не найден",
                        input_message_content=InputTextMessageContent(f"Город '{city}' не найден")
                    )
            else:
                return InlineQueryResultArticle(
                    id='1',
                    title="Ошибка API",
                    input_message_content=InputTextMessageContent("Ошибка при получении погоды")
                )

        except Exception:
            return InlineQueryResultArticle(
                id='1',
                title="Ошибка сети",
                input_message_content=InputTextMessageContent("Ошибка подключения к серверу погоды")
            )

    def _format_weather_text(self, data):
        """Форматирование текста погоды"""
        return (
            f"🌤️ Погода в {data['name']}:\n"
            f"🌡️ Температура: {data['main']['temp']}°C\n"
            f"🌡️ Ощущается как: {data['main']['feels_like']}°C\n"
            f"💧 Влажность: {data['main']['humidity']}%\n"
            f"💬 Описание: {data['weather'][0]['description'].capitalize()}"
        )

    async def _handle_translate_query(self, query):
        """Обработка запроса перевода"""
        from telegram import InlineQueryResultArticle, InputTextMessageContent

        text_parts = query.split(' ', 2)
        if len(text_parts) < 3:
            return InlineQueryResultArticle(
                id='1',
                title="Использование",
                input_message_content=InputTextMessageContent("Использование: weather [город] или translate [текст] [язык]")
            )

        text = text_parts[1]
        lang = text_parts[2]

        if not (text and lang and len(text) <= 500 and len(lang) == 2):
            return InlineQueryResultArticle(
                id='1',
                title="Ошибка",
                input_message_content=InputTextMessageContent("Использование: текст для перевода")
            )

        translated = self._translate_text(text, lang)
        result_text = (
            f"🔄 Перевод текста:\n\n"
            f"📝 Оригинал: {text}\n"
            f"🌐 Язык: {lang}\n"
            f"📋 Перевод: {translated}"
        )

        return InlineQueryResultArticle(
            id='1',
            title=f"Перевод на {lang}",
            input_message_content=InputTextMessageContent(result_text)
        )

    def _translate_text(self, text, lang):
        """Простая имитация перевода"""
        if lang.lower() == 'en':
            translations = {
                'привет': "Hello",
                'мир': "World",
                'спасибо': "Thank you",
                'да': "Yes",
                'нет': "No"
            }
            return translations.get(text.lower(), f"[{lang.upper()}] {text}")
        return f"[{lang.upper()}] {text}"

    def _create_usage_result(self):
        """Создание результата с инструкцией использования"""
        from telegram import InlineQueryResultArticle, InputTextMessageContent
        return InlineQueryResultArticle(
            id='1',
            title="Использование",
            input_message_content=InputTextMessageContent("Использование: weather [город] или translate [текст] [язык]")
        )

    def run(self):
        """
        Запуск телеграм-бота.

        Выполняет следующие шаги:
        1. Проверка на единственный экземпляр
        2. Валидация конфигурации
        3. Запуск polling для получения обновлений
        4. Graceful shutdown при получении сигнала завершения

        Raises:
            ConfigurationError: При ошибках конфигурации
            Exception: При критических ошибках во время работы
        """
        try:
            # Проверяем, что это единственный экземпляр
            if not check_single_instance():
                self.logger.error("Другой экземпляр бота уже запущен. Завершение работы.")
                return

            self.logger.info("Запуск телеграм-бота...")
            self.metrics.set_bot_status(1)

            # Проверяем конфигурацию перед запуском
            self._validate_startup_config()

            # Запускаем приложение
            self.telegram_app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

        except KeyboardInterrupt:
            self.logger.info("Получен сигнал завершения")
        except Exception as e:
            self.logger.error(f"Критическая ошибка при запуске: {e}", exc_info=True)
            self.metrics.record_error("CriticalError", "Application", e)
            raise
        finally:
            self.metrics.set_bot_status(0)
            self._cleanup()

    def _validate_startup_config(self):
        """Валидация конфигурации перед запуском"""
        # Проверяем токен бота
        if not self.config.bot_config.token:
            raise ConfigurationError("Токен бота не настроен")

        # Проверяем подключение к базе данных
        try:
            # Тестовый запрос к базе данных
            test_result = self.user_repo._fetch_one("SELECT 1 as test", ())
            if test_result:
                self.logger.info("Подключение к базе данных успешно")
            else:
                raise ConfigurationError("Не удалось выполнить тестовый запрос к базе данных")

            # Инициализируем достижения
            self.user_repo.initialize_achievements()
            self.logger.info("Достижения инициализированы")

            # Инициализируем роли
            self.role_service.initialize_roles()
            self.logger.info("Роли инициализированы")

            # Инициализируем администраторов из конфигурации
            admin_ids = self.config.bot_config.admin_ids
            if admin_ids:
                self.role_service.initialize_admin_users(admin_ids)
                self.logger.info(f"Администраторы инициализированы: {admin_ids}")

        except Exception as e:
            raise ConfigurationError(f"Не удалось подключиться к базе данных: {e}")

        self.logger.info("Конфигурация проверена успешно")

    def _cleanup(self):
        """Очистка ресурсов при завершении"""
        try:
            # Закрываем соединения с базой данных
            if hasattr(self.user_repo, 'close'):
                self.user_repo.close()
            if hasattr(self.score_repo, 'close'):
                self.score_repo.close()
            if hasattr(self.error_repo, 'close'):
                self.error_repo.close()

            self.logger.info("Ресурсы освобождены")

        except Exception as e:
            self.logger.error(f"Ошибка при очистке ресурсов: {e}", exc_info=True)

    async def _error_handler(self, update: Update, context: ContextTypes):
        """Обработчик ошибок приложения"""
        try:
            error = context.error
            self.logger.error(f"Произошла ошибка в обработке обновления: {error}", exc_info=True)
            self.metrics.record_error(error.__class__.__name__, "Application", error)

            # Для сетевых ошибок, таких как NetworkError, логируем и игнорируем
            if 'NetworkError' in str(type(error)) or 'ReadError' in str(type(error)):
                self.logger.warning(f"Сетевая ошибка Telegram API: {error}. Бот продолжит работу.")
                return  # Не отправляем сообщение пользователю, так как это внутренняя ошибка

            # Для других ошибок, если есть update, отправляем сообщение
            if update and update.effective_chat:
                await update.effective_chat.send_message(
                    "Произошла внутренняя ошибка. Попробуйте позже."
                )

        except Exception as e:
            self.logger.error(f"Ошибка в обработчике ошибок: {e}", exc_info=True)

    def get_status(self) -> Dict[str, Any]:
        """
        Получение текущего статуса приложения.

        Returns:
            Dict содержащий информацию о:
            - Статусе приложения (running/stopped)
            - Конфигурации (токен, количество админов, флаги функций)
            - Количестве зарегистрированных обработчиков
            - Статусе сервисов (платежи, уведомления, rate limiting)
            - Статусе подключения к БД
            - Наличии unified_router
        """
        return {
            'status': 'running',
            'config': {
                'bot_token': '***' if self.config.bot_config.token else None,
                'admin_count': len(self.config.bot_config.admin_ids),
                'ai_enabled': self.config.bot_config.enable_ai_processing,
                'developer_notifications': self.config.bot_config.enable_developer_notifications
            },
            'handlers_count': len(self.handlers),
            'services': {
                'donation_service': self.donation_service is not None,
                'notification_service': self.notification_service is not None,
                'trigger_service': self.trigger_service is not None,
                'rate_limiter': hasattr(self, 'rate_limiter')
            },
            'database_connected': True,  # Здесь можно добавить реальную проверку
            'unified_router': self.unified_router is not None
        }

    async def stop(self):
        """Остановка приложения"""
        self.logger.info("Остановка приложения...")
        await self.telegram_app.stop()
        self._cleanup()
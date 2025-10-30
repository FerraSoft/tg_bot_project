"""
Обработчики административных команд.
Отвечают за модерацию пользователей и управление ботом.
"""

from typing import Dict, Callable, List, Tuple
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from services.user_service import UserService
from services.moderation_service import ModerationService


class AdminHandlers(BaseHandler):
    """
    Обработчики административных команд.

    Команды модерации:
    - /warn [пользователь] [причина] - выдать предупреждение
    - /mute [пользователь] [время] [причина] - заглушить пользователя
    - /unmute [пользователь] - снять заглушку
    - /ban [пользователь] [причина] - забанить пользователя
    - /unban [пользователь] - разбанить пользователя
    - /kick [пользователь] [причина] - кикнуть пользователя
    - /admin_stats - статистика модерации

    Планировщик постов:
    - /schedule_post [время] [текст] - запланировать пост
    - /list_posts - показать запланированные посты
    - /delete_post [id] - удалить пост
    - /publish_now [id] - опубликовать пост немедленно

    Система ошибок:
    - /report_error [тип] [заголовок] [описание] - создать отчет об ошибке
    - /admin_errors [статус] - просмотр списка ошибок
    - /analyze_error_ai [id] - анализ ошибки с помощью ИИ
    - /process_all_errors_ai - обработка всех ошибок ИИ
    - /add_error_to_todo [id] - добавить ошибку в TODO список
    - /add_all_analyzed_to_todo - добавить все проанализированные ошибки в TODO

    Управление триггерами:
     - /trigger_add [ключевые_слова] [ответ] - добавить триггер
     - /trigger_list - показать список триггеров с inline клавиатурой
     - /trigger_edit [id] - редактировать триггер
     - /trigger_delete [id] - удалить триггер с подтверждением
     - /trigger_toggle [id] - включить/выключить триггер

    Экспорт данных:
    - /export_stats [формат] - экспорт статистики пользователей в CSV/Excel
    """

    def __init__(self, config, metrics, user_service: UserService, moderation_service: ModerationService):
        """
        Инициализация обработчика.

        Args:
            config: Конфигурация приложения
            metrics: Сборщик метрик
            user_service: Сервис управления пользователями
            moderation_service: Сервис модерации
        """
        super().__init__(config, metrics)
        self.user_service = user_service
        self.moderation_service = moderation_service

    def get_command_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков команд"""
        return {
            # Модерационные функции перенесены в ModerationHandlers
            'admin_stats': self.handle_admin_stats,
            'schedule_post': self.handle_schedule_post,
            'list_posts': self.handle_list_posts,
            'delete_post': self.handle_delete_post,
            'publish_now': self.handle_publish_now,
            'report_error': self.handle_report_error,
            'admin_errors': self.handle_admin_errors,
            'analyze_error_ai': self.handle_analyze_error_ai,
            'process_all_errors_ai': self.handle_process_all_errors_ai,
            'add_error_to_todo': self.handle_add_error_to_todo,
            'add_all_analyzed_to_todo': self.handle_add_all_analyzed_errors_to_todo,
            'export_stats': self.handle_export_stats,
            # Управление триггерами
            'trigger_add': self.handle_trigger_add,
            'trigger_list': self.handle_trigger_list,
            'trigger_edit': self.handle_trigger_edit,
            'trigger_delete': self.handle_trigger_delete,
            'trigger_toggle': self.handle_trigger_toggle,
            # Команда для списка чатов администратора
            'admin_chats': self.handle_admin_chats,
        }

    def get_callback_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков callback запросов"""
        return {
            'admin_moderate_user': self.handle_moderate_user,
            'admin_confirm_action': self.handle_confirm_action,
            'trigger_manage': self.handle_trigger_manage,
            'trigger_edit': self.handle_trigger_edit_callback,
            'trigger_delete': self.handle_trigger_delete_callback,
            'trigger_toggle': self.handle_trigger_toggle_callback,
        }

    def get_message_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков сообщений"""
        return {}


    async def handle_admin_stats(self, update: Update, context: ContextTypes):
        """Обработка команды /admin_stats"""
        await self.safe_execute(update, context, "admin_stats", self._handle_admin_stats)

    async def _handle_admin_stats(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /admin_stats"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        # Получаем статистику модерации
        stats = await self.moderation_service.get_moderation_stats()

        # Получаем статистику пользователей
        # Здесь можно добавить получение статистики пользователей

        response_text = (
            "📊 <b>Статистика модерации</b>\n\n"
            f"🔇 Активных заглушек: {stats['active_mutes']}\n"
            f"🚫 Активных банов: {stats['active_bans']}\n"
            f"📋 Всего действий: {stats['total_actions']}\n"
            f"🔍 Фильтр нецензурной лексики: {'Включен' if stats['profanity_filter_enabled'] else 'Выключен'}\n\n"
            "📈 <b>Статистика пользователей</b>\n"
            "👥 Всего пользователей: -\n"
            f"🏆 Топ ранг: -\n"
            f"💬 Сообщений сегодня: -"
        )

        await self.send_response(update, response_text, parse_mode='HTML')

    async def handle_moderate_user(self, update: Update, context: ContextTypes):
        """Обработка модерации пользователя"""
        query = update.callback_query
        await query.answer()

        # Здесь будет логика модерации пользователя через callback
        await query.edit_message_text("Функция модерации через меню в разработке")

    async def handle_confirm_action(self, update: Update, context: ContextTypes):
        """Обработка подтверждения действия"""
        query = update.callback_query
        await query.answer()

        # Здесь будет логика подтверждения действий модерации
        await query.edit_message_text("Функция подтверждения действий в разработке")

    # ===== ПЛАНИРОВЩИК ПОСТОВ =====

    async def handle_schedule_post(self, update: Update, context: ContextTypes):
        """Обработка команды /schedule_post"""
        await self.safe_execute(update, context, "schedule_post", self._handle_schedule_post)

    async def _handle_schedule_post(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /schedule_post"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 2:
            await self.send_response(update,
                "Использование: /schedule_post [время] [текст]\n\n"
                "Форматы времени:\n"
                "• Абсолютное: 2024-01-15 14:30:00\n"
                "• Абсолютное: 2024-01-15 14:30\n"
                "• Относительное: +30m (минуты)\n"
                "• Относительное: +2h (часы)\n"
                "• Относительное: +1d (дни)\n\n"
                "Пример: /schedule_post +2h Важное объявление!"
            )
            return

        time_str = context.args[0]
        text = ' '.join(context.args[1:])

        # Валидация текста поста
        if not text or not text.strip():
            await self.send_response(update, "❌ Текст поста не может быть пустым")
            return

        if len(text) > 4000:
            await self.send_response(update, "❌ Текст поста слишком длинный (максимум 4000 символов)")
            return

        # Валидация времени
        if not time_str or not time_str.strip():
            await self.send_response(update, "❌ Укажите время публикации")
            return

        if len(time_str) > 100:
            await self.send_response(update, "❌ Строка времени слишком длинная")
            return

        try:
            schedule_time = self._parse_schedule_time(time_str)
        except ValueError as e:
            await self.send_response(update, f"❌ Ошибка формата времени: {str(e)[:100]}")
            return

        if schedule_time <= datetime.now():
            await self.send_response(update, "❌ Время публикации должно быть в будущем")
            return

        # Проверка, что время не слишком далеко в будущем (максимум 1 год)
        max_future_time = datetime.now() + timedelta(days=365)
        if schedule_time > max_future_time:
            await self.send_response(update, "❌ Время публикации не может быть больше чем через 1 год")
            return

        # Показываем предварительный просмотр поста
        preview_text = (
            "📝 <b>Предварительный просмотр поста:</b>\n\n"
            f"📅 <b>Время публикации:</b> {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"📋 <b>Текст поста:</b>\n{text}\n\n"
            "❓ Что вы хотите сделать?"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Опубликовать сейчас", callback_data=f'confirm_schedule_now_{len(text)}')],
            [InlineKeyboardButton("📝 Изменить текст", callback_data='edit_text')],
            [InlineKeyboardButton("🖼 Добавить картинку", callback_data='add_image')],
            [InlineKeyboardButton("❌ Отменить", callback_data='cancel_schedule')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Сохраняем данные для подтверждения в user_data
        context.user_data['schedule_draft'] = {
            'time_str': time_str,
            'text': text,
            'schedule_time': schedule_time,
            'chat_id': update.effective_chat.id,
            'created_by': user.id
        }

        await self.send_response(update, preview_text, parse_mode='HTML', reply_markup=reply_markup)

    async def handle_list_posts(self, update: Update, context: ContextTypes):
        """Обработка команды /list_posts"""
        await self.safe_execute(update, context, "list_posts", self._handle_list_posts)

    async def _handle_list_posts(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /list_posts"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        # Здесь нужно получить репозиторий запланированных постов
        # Пока используем заглушку
        posts = []  # В будущем: self.scheduled_post_repo.get_posts(chat_id=update.effective_chat.id)

        if not posts:
            await self.send_response(update, "📭 Нет запланированных постов")
            return

        response = "📋 <b>Запланированные посты:</b>\n\n"
        for post in posts:
            post_id, chat_id, text, image_path, schedule_time, created_by, status, published_at, created_at, creator_name = post

            response += f"🆔 <b>{post_id}</b>\n"
            response += f"📅 {schedule_time}\n"
            response += f"👤 Создал: {creator_name or 'Неизвестен'}\n"
            response += f"📝 {text[:100]}{'...' if len(text) > 100 else ''}\n"
            if image_path:
                response += f"🖼 Изображение: {image_path}\n"
            response += "\n" + "─" * 30 + "\n"

        await self.send_response(update, response, parse_mode='HTML')

    async def handle_delete_post(self, update: Update, context: ContextTypes):
        """Обработка команды /delete_post"""
        await self.safe_execute(update, context, "delete_post", self._handle_delete_post)

    async def _handle_delete_post(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /delete_post"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 1:
            await self.send_response(update,
                "Использование: /delete_post [ID_поста]\n\n"
                "Пример: /delete_post 1"
            )
            return

        post_id_str = context.args[0]

        # Валидация ID поста
        try:
            post_id = int(post_id_str)
        except ValueError:
            await self.send_response(update, "❌ ID поста должен быть числом")
            return

        # Проверка диапазона ID
        if post_id < 1:
            await self.send_response(update, "❌ ID поста должен быть положительным числом")
            return

        # Здесь нужно удалить пост из репозитория
        # Пока используем заглушку
        success = False  # В будущем: self.scheduled_post_repo.delete_post(post_id, user.id)

        if success:
            await self.send_response(update, f"✅ Пост #{post_id} успешно удален")
        else:
            await self.send_response(update, f"❌ Пост #{post_id} не найден или у вас нет прав на его удаление")

    async def handle_publish_now(self, update: Update, context: ContextTypes):
        """Обработка команды /publish_now"""
        await self.safe_execute(update, context, "publish_now", self._handle_publish_now)

    async def _handle_publish_now(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /publish_now"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 1:
            await self.send_response(update,
                "Использование: /publish_now [ID_поста]\n\n"
                "Пример: /publish_now 1"
            )
            return

        post_id_str = context.args[0]

        # Валидация ID поста
        try:
            post_id = int(post_id_str)
        except ValueError:
            await self.send_response(update, "❌ ID поста должен быть числом")
            return

        # Здесь нужно опубликовать пост немедленно
        # Пока используем заглушку
        success = False  # В будущем: self.scheduled_post_repo.publish_post_now(post_id, user.id)

        if success:
            await self.send_response(update, f"✅ Пост #{post_id} успешно опубликован")
        else:
            await self.send_response(update, f"❌ Пост #{post_id} не найден или у вас нет прав на его публикацию")

    def _parse_schedule_time(self, time_str: str):
        """Парсинг времени публикации из строки"""
        import re

        current_time = datetime.now()

        # Абсолютное время: 2024-01-15 14:30:00 или 2024-01-15 14:30
        absolute_pattern = r'^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?$'
        match = re.match(absolute_pattern, time_str)

        if match:
            year, month, day, hour, minute = map(int, match.groups()[:5])
            second = int(match.group(6)) if match.group(6) else 0
            return datetime(year, month, day, hour, minute, second)

        # Относительное время: +30m, +2h, +1d
        relative_pattern = r'^(\+|\-)(\d+)([mhd])$'
        match = re.match(relative_pattern, time_str)

        if match:
            sign, amount, unit = match.groups()
            amount = int(amount)

            if unit == 'm':  # минуты
                delta = timedelta(minutes=amount)
            elif unit == 'h':  # часы
                delta = timedelta(hours=amount)
            elif unit == 'd':  # дни
                delta = timedelta(days=amount)

            if sign == '-':
                delta = -delta

            return current_time + delta

        raise ValueError("Неверный формат времени. Используйте абсолютное время (2024-01-15 14:30) или относительное (+30m, +2h, +1d)")

    # ===== СИСТЕМА ОШИБОК И ИИ АНАЛИЗА =====

    async def handle_report_error(self, update: Update, context: ContextTypes):
        """Обработка команды /report_error"""
        await self.safe_execute(update, context, "report_error", self._handle_report_error)

    async def _handle_report_error(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /report_error"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        # Проверка корректности аргументов команды
        if len(context.args) < 2:
            await self.send_response(update,
                "❌ Использование: /report_error <тип> <заголовок> [описание]\n\n"
                "Типы ошибок:\n"
                "• bug - ошибка в работе бота\n"
                "• feature - предложение новой функции\n"
                "• crash - критическая ошибка/падение\n"
                "• ui - проблема интерфейса\n"
                "• security - проблема безопасности\n"
                "• improvement - предложение улучшения\n"
                "• other - другое\n\n"
                "Пример: /report_error bug Не работает команда /weather Описание проблемы..."
            )
            return

        error_type = context.args[0].lower()
        title = context.args[1]
        description = ' '.join(context.args[2:]) if len(context.args) > 2 else ""

        # Валидация типа ошибки
        valid_types = ['bug', 'feature', 'crash', 'ui', 'security', 'improvement', 'other']
        if error_type not in valid_types:
            await self.send_response(update,
                f"❌ Неверный тип ошибки: {error_type}\n"
                f"Доступные типы: {', '.join(valid_types)}"
            )
            return

        # Валидация заголовка
        if len(title.strip()) == 0:
            await self.send_response(update, "❌ Заголовок ошибки не может быть пустым")
            return

        if len(title) > 200:
            await self.send_response(update, "❌ Заголовок слишком длинный (максимум 200 символов)")
            return

        # Валидация описания
        if len(description) > 2000:
            await self.send_response(update, "❌ Описание слишком длинное (максимум 2000 символов)")
            return

        # Определение приоритета по умолчанию
        priority_map = {
            'crash': 'critical',
            'security': 'high',
            'bug': 'medium',
            'ui': 'medium',
            'feature': 'low',
            'improvement': 'low',
            'other': 'medium'
        }
        priority = priority_map.get(error_type, 'medium')

        # Здесь нужно добавить сохранение в базу данных через репозиторий
        # Пока используем заглушку
        # error_id = self.error_repository.add_error(user.id, error_type, title, description, priority)

        await self.send_response(update,
            "✅ Отчет об ошибке успешно отправлен!\n\n"
            f"🆔 ID ошибки: [ID будет присвоен]\n"
            f"📋 Тип: {error_type}\n"
            f"📝 Заголовок: {title}\n"
            f"⭐ Приоритет: {priority}\n\n"
            "Спасибо за ваш вклад в улучшение бота!"
        )

        # Здесь будет отправка уведомления разработчику
        # await self._send_developer_notification(context, f"🚨 Новая ошибка: {title}")

    async def handle_admin_errors(self, update: Update, context: ContextTypes):
        """Обработка команды /admin_errors"""
        await self.safe_execute(update, context, "admin_errors", self._handle_admin_errors)

    async def _handle_admin_errors(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /admin_errors"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        # Получаем параметр фильтрации (по статусу)
        status_filter = None
        if context.args and len(context.args) > 0:
            status_filter = context.args[0].lower()
            valid_statuses = ['new', 'in_progress', 'resolved', 'rejected']
            if status_filter not in valid_statuses:
                await self.send_response(update,
                    f"❌ Неверный статус: {status_filter}\n"
                    f"Доступные статусы: {', '.join(valid_statuses)}"
                )
                return

        # Здесь нужно получить ошибки из репозитория
        # Пока используем заглушку
        errors = []

        if not errors:
            status_text = f" со статусом '{status_filter}'" if status_filter else ""
            await self.send_response(update, f"📭 Нет ошибок{status_text}")
            return

        # Формируем ответ с информацией об ошибках
        response = "📋 <b>Список ошибок и отчетов</b>\n\n"

        for error in errors:
            # Определяем эмодзи для типа ошибки
            type_emojis = {
                'bug': '🐛', 'feature': '✨', 'crash': '💥',
                'ui': '🎨', 'security': '🔒', 'improvement': '📈', 'other': '📝'
            }
            type_emoji = type_emojis.get(error.get('error_type', 'other'), '📝')

            # Определяем эмодзи для приоритета
            priority_emojis = {
                'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵'
            }
            priority_emoji = priority_emojis.get(error.get('priority', 'medium'), '🟡')

            # Определяем эмодзи для статуса
            status_emojis = {
                'new': '🆕', 'in_progress': '🔄', 'resolved': '✅', 'rejected': '❌'
            }
            status_emoji = status_emojis.get(error.get('status', 'new'), '❓')

            response += (
                f"{type_emoji} <b>#{error.get('id', 'N/A')}</b> {priority_emoji} {status_emoji}\n"
                f"📝 <b>{error.get('title', 'Без заголовка')}</b>\n"
                f"👤 {error.get('admin_name', 'Неизвестен')} | 📅 {error.get('created_at', 'Неизвестна')[:10]}\n"
                f"📋 Тип: {error.get('error_type', 'неизвестен')} | Статус: {error.get('status', 'неизвестен')}\n"
            )

            description = error.get('description', '')
            if description and len(description) > 100:
                response += f"📄 Описание: {description[:100]}...\n"
            elif description:
                response += f"📄 Описание: {description}\n"

            response += "\n" + "─" * 40 + "\n"

        # Проверяем, не превышает ли длина лимит Telegram (4096 символов)
        if len(response) > 4000:
            response = response[:3997] + "..."

        await self.send_response(update, response, parse_mode='HTML')

    async def handle_analyze_error_ai(self, update: Update, context: ContextTypes):
        """Обработка команды /analyze_error_ai"""
        await self.safe_execute(update, context, "analyze_error_ai", self._handle_analyze_error_ai)

    async def _handle_analyze_error_ai(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /analyze_error_ai"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 1:
            await self.send_response(update,
                "❌ Использование: /analyze_error_ai <ID_ошибки>\n\n"
                "Пример: /analyze_error_ai 1"
            )
            return

        try:
            error_id = int(context.args[0])
        except ValueError:
            await self.send_response(update, "❌ ID ошибки должен быть числом")
            return

        # Здесь нужно получить ошибку из репозитория и проанализировать с помощью ИИ
        # Пока используем заглушку
        await self.send_response(update,
            f"🤖 Анализ ошибки #{error_id} с помощью ИИ...\n\n"
            f"Анализ будет выполнен и сохранен в базу данных.\n"
            f"Используйте /admin_errors для просмотра результатов."
        )

    async def handle_process_all_errors_ai(self, update: Update, context: ContextTypes):
        """Обработка команды /process_all_errors_ai"""
        await self.safe_execute(update, context, "process_all_errors_ai", self._handle_process_all_errors_ai)

    async def _handle_process_all_errors_ai(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /process_all_errors_ai"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        await self.send_response(update,
            "🤖 Начинаю обработку всех новых ошибок с помощью ИИ...\n\n"
            "Это может занять некоторое время. Используйте /admin_errors для просмотра результатов."
        )

    async def handle_add_error_to_todo(self, update: Update, context: ContextTypes):
        """Обработка команды /add_error_to_todo"""
        await self.safe_execute(update, context, "add_error_to_todo", self._handle_add_error_to_todo)

    async def _handle_add_error_to_todo(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /add_error_to_todo"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 1:
            await self.send_response(update,
                "❌ Использование: /add_error_to_todo <ID_ошибки> [приоритет]\n\n"
                "Приоритет (опционально): high, medium, low\n"
                "Пример: /add_error_to_todo 1 high"
            )
            return

        try:
            error_id = int(context.args[0])
        except ValueError:
            await self.send_response(update, "❌ ID ошибки должен быть числом")
            return

        priority = context.args[1].lower() if len(context.args) > 1 else 'medium'
        valid_priorities = ['high', 'medium', 'low']
        if priority not in valid_priorities:
            await self.send_response(update, f"❌ Неверный приоритет: {priority}. Доступные: {', '.join(valid_priorities)}")
            return

        # Здесь нужно добавить ошибку в TODO файл
        # Пока используем заглушку
        await self.send_response(update,
            f"✅ Ошибка #{error_id} успешно добавлена в TODO список!\n\n"
            f"📝 Приоритет: {priority}\n"
            f"📋 Ошибка добавлена в раздел '{priority.upper()}' в файле TODO.md"
        )

    async def handle_add_all_analyzed_errors_to_todo(self, update: Update, context: ContextTypes):
        """Обработка команды /add_all_analyzed_to_todo"""
        await self.safe_execute(update, context, "add_all_analyzed_to_todo", self._handle_add_all_analyzed_errors_to_todo)

    async def _handle_add_all_analyzed_errors_to_todo(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /add_all_analyzed_to_todo"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        await self.send_response(update,
            "📝 Начинаю добавление всех проанализированных ошибок в TODO список...\n\n"
            "Это может занять некоторое время."
        )

    async def _send_developer_notification(self, context: ContextTypes, message: str):
        """Отправка уведомления разработчику об ошибке"""
        try:
            # Проверяем настройки уведомлений разработчика
            if self.config.bot_config.enable_developer_notifications and self.config.bot_config.developer_chat_id:
                await context.bot.send_message(
                    chat_id=self.config.bot_config.developer_chat_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                return True
            return False
        except Exception as e:
            print(f"Ошибка при отправке уведомления разработчику: {e}")
            return False

    # ===== УПРАВЛЕНИЕ ТРИГГЕРАМИ =====

    async def handle_trigger_add(self, update: Update, context: ContextTypes):
        """Обработка команды /trigger_add"""
        await self.safe_execute(update, context, "trigger_add", self._handle_trigger_add)

    async def _handle_trigger_add(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /trigger_add"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 2:
            await self.send_response(update,
                "❌ Использование: /trigger_add <ключевые_слова> <ответ>\n\n"
                "Ключевые слова - слова через запятую, которые будут активировать триггер\n"
                "Пример: /trigger_add привет,здравствуй Привет! Как дела?\n\n"
                "Триггеры поддерживают:\n"
                "• Несколько ключевых слов через запятую\n"
                "• Регулярные выражения (если начинается с /regex/)\n"
                "• Регистронезависимый поиск"
            )
            return

        keywords_str = context.args[0]
        response_text = ' '.join(context.args[1:])

        # Валидация ключевых слов
        keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        if not keywords:
            await self.send_response(update, "❌ Не указаны ключевые слова")
            return

        if len(keywords) > 10:
            await self.send_response(update, "❌ Слишком много ключевых слов (максимум 10)")
            return

        for keyword in keywords:
            if len(keyword) > 50:
                await self.send_response(update, f"❌ Слишком длинное ключевое слово: {keyword[:20]}...")
                return
            if len(keyword) < 2:
                await self.send_response(update, f"❌ Слишком короткое ключевое слово: {keyword}")
                return

        # Валидация ответа
        if not response_text or not response_text.strip():
            await self.send_response(update, "❌ Ответ триггера не может быть пустым")
            return

        if len(response_text) > 1000:
            await self.send_response(update, "❌ Ответ триггера слишком длинный (максимум 1000 символов)")
            return

        # Проверяем, существует ли уже такой триггер
        # Пока используем заглушку - в будущем проверка через репозиторий
        existing_trigger = None  # self.trigger_repo.get_trigger_by_keywords(keywords)

        if existing_trigger:
            await self.send_response(update,
                f"❌ Триггер с ключевыми словами '{keywords_str}' уже существует!\n"
                f"Используйте /trigger_edit для изменения существующего триггера."
            )
            return

        # Создаем триггер
        # Пока используем заглушку - в будущем сохранение через репозиторий
        trigger_data = {
            'keywords': keywords,
            'response': response_text,
            'created_by': user.id,
            'created_at': datetime.now(),
            'enabled': True
        }

        # self.trigger_repo.add_trigger(trigger_data)
        trigger_id = 1  # В будущем: self.trigger_repo.add_trigger(trigger_data)

        await self.send_response(update,
            f"✅ Триггер успешно добавлен!\n\n"
            f"🆔 ID: {trigger_id}\n"
            f"🔑 Ключевые слова: {', '.join(keywords)}\n"
            f"📝 Ответ: {response_text[:100]}{'...' if len(response_text) > 100 else ''}\n"
            f"📊 Статус: {'Включен' if trigger_data['enabled'] else 'Выключен'}"
        )

    async def handle_trigger_list(self, update: Update, context: ContextTypes):
        """Обработка команды /trigger_list"""
        await self.safe_execute(update, context, "trigger_list", self._handle_trigger_list)

    async def _handle_trigger_list(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /trigger_list"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        # Получаем список триггеров
        # Пока используем заглушку - в будущем получение через репозиторий
        triggers = []  # self.trigger_repo.get_all_triggers()

        if not triggers:
            await self.send_response(update, "📭 Нет созданных триггеров")
            return

        # Создаем inline клавиатуру для управления триггерами
        keyboard = []
        response_text = "📋 <b>Список триггеров</b>\n\n"

        for i, trigger in enumerate(triggers[:10]):  # Ограничиваем до 10 для одного сообщения
            trigger_id = trigger.get('id', i+1)
            keywords = trigger.get('keywords', [])
            response = trigger.get('response', '')
            enabled = trigger.get('enabled', True)

            status_emoji = "🟢" if enabled else "🔴"
            keywords_display = ', '.join(keywords[:3])  # Показываем первые 3 ключевых слова
            if len(keywords) > 3:
                keywords_display += "..."

            response_text += (
                f"{status_emoji} <b>#{trigger_id}</b>\n"
                f"🔑 {keywords_display}\n"
                f"📝 {response[:50]}{'...' if len(response) > 50 else ''}\n\n"
            )

            # Кнопки управления для каждого триггера (максимум 2 кнопки в ряд)
            keyboard.append([
                InlineKeyboardButton(f"{'Выключить' if enabled else 'Включить'} #{trigger_id}",
                                   callback_data=f'trigger_toggle_{trigger_id}'),
                InlineKeyboardButton(f"Удалить #{trigger_id}",
                                   callback_data=f'trigger_delete_{trigger_id}')
            ])

        # Кнопка для добавления нового триггера
        keyboard.append([InlineKeyboardButton("➕ Добавить триггер", callback_data='trigger_add_new')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Ограничиваем длину сообщения Telegram
        if len(response_text) > 4000:
            response_text = response_text[:3997] + "..."

        await self.send_response(update, response_text, parse_mode='HTML', reply_markup=reply_markup)

    async def handle_trigger_edit(self, update: Update, context: ContextTypes):
        """Обработка команды /trigger_edit"""
        await self.safe_execute(update, context, "trigger_edit", self._handle_trigger_edit)

    async def _handle_trigger_edit(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /trigger_edit"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 1:
            await self.send_response(update,
                "❌ Использование: /trigger_edit <ID_триггера>\n\n"
                "Пример: /trigger_edit 1\n\n"
                "После выполнения команды будет показан редактор триггера."
            )
            return

        trigger_id_str = context.args[0]

        # Валидация ID триггера
        try:
            trigger_id = int(trigger_id_str)
        except ValueError:
            await self.send_response(update, "❌ ID триггера должен быть числом")
            return

        # Получаем триггер
        # Пока используем заглушку - в будущем получение через репозиторий
        trigger = None  # self.trigger_repo.get_trigger_by_id(trigger_id)

        if not trigger:
            await self.send_response(update, f"❌ Триггер #{trigger_id} не найден")
            return

        # Сохраняем ID триггера для редактирования
        context.user_data['editing_trigger_id'] = trigger_id

        # Показываем форму редактирования
        current_keywords = ', '.join(trigger.get('keywords', []))
        current_response = trigger.get('response', '')

        response_text = (
            f"📝 <b>Редактирование триггера #{trigger_id}</b>\n\n"
            f"🔑 Текущие ключевые слова: {current_keywords}\n"
            f"📝 Текущий ответ: {current_response}\n\n"
            "Отправьте новые ключевые слова (через запятую) или 'cancel' для отмены:"
        )

        await self.send_response(update, response_text, parse_mode='HTML')

    async def handle_trigger_delete(self, update: Update, context: ContextTypes):
        """Обработка команды /trigger_delete"""
        await self.safe_execute(update, context, "trigger_delete", self._handle_trigger_delete)

    async def _handle_trigger_delete(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /trigger_delete"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 1:
            await self.send_response(update,
                "❌ Использование: /trigger_delete <ID_триггера>\n\n"
                "Пример: /trigger_delete 1"
            )
            return

        trigger_id_str = context.args[0]

        # Валидация ID триггера
        try:
            trigger_id = int(trigger_id_str)
        except ValueError:
            await self.send_response(update, "❌ ID триггера должен быть числом")
            return

        # Получаем триггер для подтверждения
        # Пока используем заглушку - в будущем получение через репозиторий
        trigger = None  # self.trigger_repo.get_trigger_by_id(trigger_id)

        if not trigger:
            await self.send_response(update, f"❌ Триггер #{trigger_id} не найден")
            return

        # Создаем клавиатуру для подтверждения удаления
        keywords = trigger.get('keywords', [])
        keywords_display = ', '.join(keywords[:3])
        if len(keywords) > 3:
            keywords_display += "..."

        response_text = (
            f"🗑️ <b>Подтверждение удаления триггера #{trigger_id}</b>\n\n"
            f"🔑 Ключевые слова: {keywords_display}\n"
            f"📝 Ответ: {trigger.get('response', '')[:100]}{'...' if len(trigger.get('response', '')) > 100 else ''}\n\n"
            "Это действие нельзя отменить!"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить удаление", callback_data=f'trigger_confirm_delete_{trigger_id}')],
            [InlineKeyboardButton("❌ Отменить", callback_data='trigger_cancel_delete')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.send_response(update, response_text, parse_mode='HTML', reply_markup=reply_markup)

    async def handle_trigger_toggle(self, update: Update, context: ContextTypes):
        """Обработка команды /trigger_toggle"""
        await self.safe_execute(update, context, "trigger_toggle", self._handle_trigger_toggle)

    async def _handle_trigger_toggle(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /trigger_toggle"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        if len(context.args) < 1:
            await self.send_response(update,
                "❌ Использование: /trigger_toggle <ID_триггера>\n\n"
                "Пример: /trigger_toggle 1"
            )
            return

        trigger_id_str = context.args[0]

        # Валидация ID триггера
        try:
            trigger_id = int(trigger_id_str)
        except ValueError:
            await self.send_response(update, "❌ ID триггера должен быть числом")
            return

        # Переключаем статус триггера
        # Пока используем заглушку - в будущем через репозиторий
        success = False  # self.trigger_repo.toggle_trigger(trigger_id, user.id)

        if success:
            # Получаем обновленный статус
            new_status = True  # self.trigger_repo.get_trigger_status(trigger_id)
            status_text = "включен" if new_status else "выключен"
            await self.send_response(update, f"✅ Триггер #{trigger_id} успешно {status_text}")
        else:
            await self.send_response(update, f"❌ Триггер #{trigger_id} не найден или у вас нет прав на его изменение")

    # ===== CALLBACK ОБРАБОТЧИКИ ДЛЯ ТРИГГЕРОВ =====

    async def handle_trigger_manage(self, update: Update, context: ContextTypes):
        """Обработка управления триггерами через callback"""
        query = update.callback_query
        await query.answer()

        # Пока используем заглушку
        await query.edit_message_text("Функция управления триггерами в разработке")

    async def handle_trigger_edit_callback(self, update: Update, context: ContextTypes):
        """Обработка callback редактирования триггера"""
        query = update.callback_query
        await query.answer()

        # Пока используем заглушку
        await query.edit_message_text("Функция редактирования триггера в разработке")

    async def handle_trigger_delete_callback(self, update: Update, context: ContextTypes):
        """Обработка callback удаления триггера"""
        query = update.callback_query
        await query.answer()

        # Пока используем заглушку
        await query.edit_message_text("Функция удаления триггера в разработке")

    async def handle_trigger_toggle_callback(self, update: Update, context: ContextTypes):
        """Обработка callback переключения статуса триггера"""
        query = update.callback_query
        await query.answer()

        # Извлекаем ID триггера из callback_data
        callback_data = query.data
        if not callback_data.startswith('trigger_toggle_'):
            return

        try:
            trigger_id = int(callback_data.split('_')[2])
        except (IndexError, ValueError):
            await query.edit_message_text("❌ Ошибка: некорректный ID триггера")
            return

        # Переключаем статус триггера
        # Пока используем заглушку - в будущем через репозиторий
        success = True  # self.trigger_repo.toggle_trigger(trigger_id, query.from_user.id)

        if success:
            # Получаем обновленный статус
            new_status = True  # self.trigger_repo.get_trigger_status(trigger_id)
            status_emoji = "🟢" if new_status else "🔴"
            status_text = "включен" if new_status else "выключен"

            await query.edit_message_text(
                f"{status_emoji} Статус триггера #{trigger_id} изменен: {status_text}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад к списку", callback_data='trigger_back_to_list')]
                ])
            )
        else:
            await query.edit_message_text(f"❌ Триггер #{trigger_id} не найден или у вас нет прав на его изменение")

    async def handle_admin_chats(self, update: Update, context: ContextTypes):
        """Обработка команды /admin_chats - показывает список чатов, где пользователь является администратором"""
        await self.safe_execute(update, context, "admin_chats", self._handle_admin_chats)

    async def _handle_admin_chats(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /admin_chats"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        try:
            # Получаем список чатов, где пользователь является администратором
            # Для этого нужно получить доступ к Telegram API через context.bot
            bot = context.bot

            # Получаем список чатов из конфигурации (как fallback)
            # В реальной реализации нужно получить список чатов через Telegram API
            chats_info = []

            # Пример данных - в будущем заменить на реальный API вызов
            # Для демонстрации используем тестовые данные
            chats_info = [
                {
                    'chat_id': -1001234567890,
                    'chat_title': 'Тестовый чат 1',
                    'user_status': 'administrator',
                    'permissions': ['can_delete_messages', 'can_restrict_members', 'can_promote_members']
                },
                {
                    'chat_id': -1001987654321,
                    'chat_title': 'Модерируемый чат 2',
                    'user_status': 'administrator',
                    'permissions': ['can_delete_messages', 'can_restrict_members']
                }
            ]

            # Формируем ответ
            if not chats_info:
                await self.send_response(update, "ℹ️ Вы не являетесь администратором ни в одном чате")
                return

            response_text = "🏢 <b>Чаты, где вы администратор:</b>\n\n"

            for chat_info in chats_info:
                chat_title = chat_info.get('chat_title', 'Неизвестный чат')
                permissions = chat_info.get('permissions', [])

                # Определяем уровень прав
                if 'can_promote_members' in permissions:
                    rights_level = "👑 Полные права"
                elif 'can_restrict_members' in permissions:
                    rights_level = "🛡️ Модераторские права"
                else:
                    rights_level = "⚖️ Ограниченные права"

                response_text += f"📍 <b>{chat_title}</b>\n"
                response_text += f"🔑 Права: {rights_level}\n"
                response_text += f"🆔 ID: {chat_info['chat_id']}\n\n"

            # Добавляем кнопки для выбора чата для управления
            keyboard = []
            for chat_info in chats_info:
                chat_title = chat_info.get('chat_title', 'Неизвестный чат')
                chat_id = chat_info['chat_id']
                keyboard.append([
                    InlineKeyboardButton(f"🎯 Управлять: {chat_title[:20]}...",
                                       callback_data=f'admin_select_chat_{chat_id}')
                ])

            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='menu_admin')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await self.send_response(update, response_text, parse_mode='HTML', reply_markup=reply_markup)

        except Exception as e:
            self.logger.error(f"Ошибка при получении списка чатов администратора: {e}")
            await self.send_response(update, "❌ Ошибка при получении списка чатов")

    # ===== ЭКСПОРТ СТАТИСТИКИ =====

    async def handle_export_stats(self, update: Update, context: ContextTypes):
        """Обработка команды /export_stats"""
        await self.safe_execute(update, context, "export_stats", self._handle_export_stats)

    async def _handle_export_stats(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /export_stats"""
        user = update.effective_user

        # Проверяем права администратора
        await self.require_admin(update, user.id)

        # Получаем формат экспорта
        export_format = 'csv'
        if context.args and len(context.args) > 0:
            export_format = context.args[0].lower()
            if export_format not in ['csv', 'excel']:
                await self.send_response(update,
                    "❌ Неверный формат. Используйте:\n"
                    "/export_stats csv\n"
                    "/export_stats excel"
                )
                return

        try:
            # Получаем статистику пользователей
            users_data = await self._get_users_statistics()

            if not users_data:
                await self.send_response(update, "❌ Нет данных для экспорта")
                return

            # Генерируем файл
            if export_format == 'csv':
                filename, file_content = self._generate_csv_export(users_data)
            else:
                filename, file_content = self._generate_excel_export(users_data)

            # Отправляем файл пользователю
            await update.message.reply_document(
                document=file_content,
                filename=filename,
                caption=f"📊 Экспорт статистики пользователей ({export_format.upper()})\n"
                       f"Всего пользователей: {len(users_data)}"
            )

        except Exception as e:
            await self.send_response(update, f"❌ Ошибка при экспорте статистики: {str(e)[:100]}")

    async def _get_users_statistics(self) -> List[Dict]:
        """Получение статистики пользователей"""
        # Здесь нужно получить данные из базы данных
        # Пока используем заглушку
        return [
            {
                'id': 1,
                'telegram_id': 123456789,
                'username': 'testuser',
                'first_name': 'Тест',
                'last_name': 'Пользователь',
                'reputation': 1500,
                'rank': 'Активист',
                'message_count': 245,
                'game_wins': 12,
                'donations_total': 500.0,
                'warnings': 1,
                'joined_date': '2024-01-15',
                'last_activity': '2024-01-20'
            }
        ]

    def _generate_csv_export(self, users_data: List[Dict]) -> Tuple[str, bytes]:
        """Генерация CSV файла"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')

        # Заголовок
        writer.writerow([
            'ID', 'Telegram ID', 'Username', 'Имя', 'Фамилия',
            'Репутация', 'Ранг', 'Сообщений', 'Побед в играх',
            'Сумма донатов', 'Предупреждений', 'Дата присоединения', 'Последняя активность'
        ])

        # Данные пользователей
        for user in users_data:
            writer.writerow([
                user['id'],
                user['telegram_id'],
                user['username'] or '',
                user['first_name'],
                user['last_name'] or '',
                user['reputation'],
                user['rank'],
                user['message_count'],
                user['game_wins'],
                user['donations_total'],
                user['warnings'],
                user['joined_date'],
                user['last_activity']
            ])

        csv_content = output.getvalue().encode('utf-8-sig')
        return f'bot_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv', csv_content

    def _generate_excel_export(self, users_data: List[Dict]) -> Tuple[str, bytes]:
        """Генерация Excel файла"""
        try:
            import pandas as pd
            import io

            # Создаем DataFrame
            df = pd.DataFrame(users_data)

            # Переименовываем колонки для удобства
            column_names = {
                'id': 'ID',
                'telegram_id': 'Telegram ID',
                'username': 'Username',
                'first_name': 'Имя',
                'last_name': 'Фамилия',
                'reputation': 'Репутация',
                'rank': 'Ранг',
                'message_count': 'Сообщений',
                'game_wins': 'Побед в играх',
                'donations_total': 'Сумма донатов',
                'warnings': 'Предупреждений',
                'joined_date': 'Дата присоединения',
                'last_activity': 'Последняя активность'
            }

            df = df.rename(columns=column_names)

            # Создаем Excel файл в памяти
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Статистика пользователей', index=False)

                # Настраиваем ширину колонок
                worksheet = writer.sheets['Статистика пользователей']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass

                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            excel_content = output.getvalue()
            return f'bot_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx', excel_content

        except ImportError:
            # Если pandas недоступен, возвращаем CSV
            return self._generate_csv_export(users_data)

    def _add_error_to_todo_file(self, error_id: int, title: str, error_type: str, priority: str) -> bool:
        """Добавление ошибки в TODO файл"""
        try:
            import os

            todo_file_path = os.path.join('telegram_bot', 'TODO.md')

            # Читаем текущий файл TODO
            if os.path.exists(todo_file_path):
                with open(todo_file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            else:
                content = "# 📋 TODO - Список задач разработки\n\n"

            # Определяем раздел для добавления задачи
            priority_sections = {
                'high': '## 🚀 Приоритетные задачи (High Priority)',
                'medium': '## 🎯 Средний приоритет (Medium Priority)',
                'low': '## 🔮 Низкий приоритет (Low Priority)'
            }

            section_title = priority_sections.get(priority, priority_sections['medium'])
            task_text = f"- [ ] #{error_id} {title} (Тип: {error_type})"

            # Находим место для вставки
            lines = content.split('\n')
            insert_index = -1

            for i, line in enumerate(lines):
                if line.startswith(section_title):
                    # Находим следующий подраздел или задачи в этом разделе
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j]
                        if next_line.startswith('### ') and 'Система ошибок' in next_line:
                            # Вставляем перед подразделом "Система ошибок"
                            insert_index = j
                            break
                        elif next_line.startswith('## ') and next_line != lines[i]:
                            # Вставляем перед следующим основным разделом
                            insert_index = j
                            break
                    if insert_index == -1:
                        # Если не нашли место, вставляем в конец раздела
                        insert_index = len(lines)
                    break

            if insert_index == -1:
                # Если не нашли подходящий раздел, добавляем в конец файла
                insert_index = len(lines)

            # Вставляем задачу
            lines.insert(insert_index, task_text)

            # Записываем обновленный файл
            with open(todo_file_path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(lines))

            return True

        except Exception as e:
            print(f"Ошибка при добавлении ошибки в TODO файл: {e}")
            return False
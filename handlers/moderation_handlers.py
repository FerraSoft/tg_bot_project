"""
Обработчики команд модерации.
Отвечают за предупреждения, заглушки и управление пользователями.
"""

from typing import Dict, Callable, List
from telegram import Update
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from services.user_service import UserService
from services.moderation_service import ModerationService


class ModerationHandlers(BaseHandler):
    """
    Обработчики команд модерации.

    Команды:
    - /warn [пользователь] [причина] - выдать предупреждение
    - /mute [пользователь] [время] [причина] - заглушить пользователя
    - /unmute [пользователь] - снять заглушку
    """

    def __init__(self, config, metrics, user_service: UserService, moderation_service: ModerationService):
        """
        Инициализация обработчика модерации.

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
        """Получение обработчиков команд модерации"""
        return {
            'warn': self.handle_warn,
            'mute': self.handle_mute,
            'unmute': self.handle_unmute,
            'ban': self.handle_ban,
            'unban': self.handle_unban,
            'kick': self.handle_kick,
        }

    def get_callback_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков callback запросов"""
        return {}

    def get_message_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков сообщений"""
        return {}

    async def handle_warn(self, update: Update, context: ContextTypes):
        """Обработка команды /warn"""
        await self.safe_execute(update, context, "warn", self._handle_warn, context.args)

    async def _handle_warn(self, update: Update, context: ContextTypes, args: List[str]):
        """Внутренняя обработка команды /warn"""
        user = update.effective_user

        # Проверяем права модератора (уже проверено в middleware, но оставляем для совместимости)
        if not await self.is_moderator(update, user.id):
            await self.send_response(update, "❌ У вас нет прав модератора")
            return

        if len(args) < 2:
            await self.send_response(update,
                "Использование: /warn [пользователь] [причина]\n\n"
                "Пример: /warn 123456789 Спам в чате"
            )
            return

        # Парсим аргументы
        target_user_id = self.extract_user_id_from_args([args[0]])
        if not target_user_id:
            await self.send_response(update, "❌ Неверный ID пользователя")
            return

        reason = ' '.join(args[1:])

        # Выдаем предупреждение
        result = await self.moderation_service.warn_user(target_user_id, reason, user.id)

        if result['success']:
            # Получаем информацию о цели для уведомления
            target_profile = await self.user_service.get_or_create_user(target_user_id)
            target_name = target_profile.first_name if target_profile else f"ID:{target_user_id}"

            response_text = (
                f"⚠️ Предупреждение выдано!\n\n"
                f"👤 Пользователь: {target_name}\n"
                f"🆔 ID: {target_user_id}\n"
                f"📊 Предупреждений: {result['warnings_count']}\n"
                f"📝 Причина: {reason}\n"
                f"👮 Модератор: {user.first_name}"
            )

            if result['action_taken']:
                response_text += f"\n\n🚨 Автоматическое действие: {result['action_taken']}"

            await self.send_response(update, response_text)

            # Отправляем уведомление пользователю
            try:
                private_message = (
                    f"⚠️ Вам выдано предупреждение!\n\n"
                    f"📊 Предупреждений: {result['warnings_count']}\n"
                    f"📝 Причина: {reason}\n"
                    f"👮 Модератор: {user.first_name}\n\n"
                    f"Будьте внимательнее к правилам чата!"
                )
                await context.bot.send_message(chat_id=target_user_id, text=private_message)
            except Exception as e:
                self.logger.warning(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")

        else:
            await self.send_response(update, "❌ Ошибка при выдаче предупреждения")

    async def handle_mute(self, update: Update, context: ContextTypes):
        """Обработка команды /mute"""
        await self.safe_execute(update, context, "mute", self._handle_mute, context.args)

    async def _handle_mute(self, update: Update, context: ContextTypes, args: List[str]):
        """Внутренняя обработка команды /mute"""
        user = update.effective_user

        # Проверяем права модератора
        if not await self.is_moderator(update, user.id):
            await self.send_response(update, "❌ У вас нет прав модератора")
            return

        if len(args) < 2:
            await self.send_response(update,
                "Использование: /mute [пользователь] [время_в_секундах] [причина]\n\n"
                "Пример: /mute 123456789 300 Спам в чате\n"
                "Время: 300 = 5 мин, 3600 = 1 час, 86400 = 24 часа"
            )
            return

        # Парсим аргументы
        target_user_id = self.extract_user_id_from_args([args[0]])
        if not target_user_id:
            await self.send_response(update, "❌ Неверный ID пользователя")
            return

        try:
            duration = int(args[1])
            if duration <= 0 or duration > 86400:  # Максимум 24 часа
                raise ValueError()
        except ValueError:
            await self.send_response(update, "❌ Время должно быть числом от 1 до 86400 секунд")
            return

        reason = ' '.join(args[2:]) if len(args) > 2 else "Нарушение правил"

        # Заглушаем пользователя
        result = await self.moderation_service.mute_user(target_user_id, reason, user.id, duration)

        if result['success']:
            # Получаем информацию о цели
            target_profile = await self.user_service.get_or_create_user(target_user_id)
            target_name = target_profile.first_name if target_profile else f"ID:{target_user_id}"

            # Преобразуем время в читаемый формат
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60

            time_parts = []
            if hours > 0:
                time_parts.append(f"{hours}ч")
            if minutes > 0:
                time_parts.append(f"{minutes}м")
            if seconds > 0 and not time_parts:  # Показываем секунды только если нет часов/минут
                time_parts.append(f"{seconds}с")

            time_str = " ".join(time_parts)

            response_text = (
                f"🔇 Пользователь заглушен!\n\n"
                f"👤 Пользователь: {target_name}\n"
                f"🆔 ID: {target_user_id}\n"
                f"⏱️ Длительность: {time_str}\n"
                f"📝 Причина: {reason}\n"
                f"👮 Модератор: {user.first_name}\n"
                f"🕐 До: {result['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}"
            )

            await self.send_response(update, response_text)

            # Отправляем уведомление пользователю
            try:
                private_message = (
                    f"🔇 Вы заглушены в чате!\n\n"
                    f"⏱️ Длительность: {time_str}\n"
                    f"📝 Причина: {reason}\n"
                    f"👮 Модератор: {user.first_name}\n"
                    f"🕐 До: {result['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Во время заглушки вы не можете отправлять сообщения."
                )
                await context.bot.send_message(chat_id=target_user_id, text=private_message)
            except Exception as e:
                self.logger.warning(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")

        else:
            await self.send_response(update, "❌ Ошибка при заглушке пользователя")

    async def handle_unmute(self, update: Update, context: ContextTypes):
        """Обработка команды /unmute"""
        await self.safe_execute(update, context, "unmute", self._handle_unmute, context.args)

    async def _handle_unmute(self, update: Update, context: ContextTypes, args: List[str]):
        """Внутренняя обработка команды /unmute"""
        user = update.effective_user

        # Проверяем права модератора
        if not await self.is_moderator(update, user.id):
            await self.send_response(update, "❌ У вас нет прав модератора")
            return

        if not args:
            await self.send_response(update,
                "Использование: /unmute [пользователь]\n\n"
                "Пример: /unmute 123456789"
            )
            return

        # Парсим аргументы
        target_user_id = self.extract_user_id_from_args(args)
        if not target_user_id:
            await self.send_response(update, "❌ Неверный ID пользователя")
            return

        # Снимаем заглушку
        success = await self.moderation_service.unmute_user(target_user_id, user.id)

        if success:
            # Получаем информацию о цели
            target_profile = await self.user_service.get_or_create_user(target_user_id)
            target_name = target_profile.first_name if target_profile else f"ID:{target_user_id}"

            response_text = (
                f"🔊 Заглушка снята!\n\n"
                f"👤 Пользователь: {target_name}\n"
                f"🆔 ID: {target_user_id}\n"
                f"👮 Модератор: {user.first_name}"
            )

            await self.send_response(update, response_text)

            # Отправляем уведомление пользователю
            try:
                private_message = (
                    f"🔊 Заглушка снята!\n\n"
                    f"👮 Модератор: {user.first_name}\n\n"
                    f"Теперь вы можете отправлять сообщения в чате."
                )
                await context.bot.send_message(chat_id=target_user_id, text=private_message)
            except Exception as e:
                self.logger.warning(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")

        else:
            await self.send_response(update, "❌ Пользователь не был заглушен или ошибка при снятии заглушки")

    async def handle_ban(self, update: Update, context: ContextTypes):
        """Обработка команды /ban"""
        await self.safe_execute(update, context, "ban", self._handle_ban, context.args)

    async def _handle_ban(self, update: Update, context: ContextTypes, args: List[str]):
        """Внутренняя обработка команды /ban"""
        user = update.effective_user

        # Проверяем права модератора
        if not await self.is_moderator(update, user.id):
            await self.send_response(update, "❌ У вас нет прав модератора")
            return

        if len(args) < 2:
            await self.send_response(update,
                "Использование: /ban [пользователь] [причина]\n\n"
                "Пример: /ban 123456789 Спам и реклама"
            )
            return

        # Парсим аргументы
        target_user_id = self.extract_user_id_from_args([args[0]])
        if not target_user_id:
            await self.send_response(update, "❌ Неверный ID пользователя")
            return

        reason = ' '.join(args[1:])

        # Баним пользователя
        result = await self.moderation_service.ban_user(target_user_id, reason, user.id)

        if result['success']:
            # Получаем информацию о цели для уведомления
            target_profile = await self.user_service.get_or_create_user(target_user_id)
            target_name = target_profile.first_name if target_profile else f"ID:{target_user_id}"

            response_text = (
                f"🚫 Пользователь забанен!\n\n"
                f"👤 Пользователь: {target_name}\n"
                f"🆔 ID: {target_user_id}\n"
                f"📝 Причина: {reason}\n"
                f"👮 Модератор: {user.first_name}"
            )

            if result['permanent']:
                response_text += "\n\nПостоянный бан"
            else:
                response_text += f"\n\nИстекает: {result['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}"

            await self.send_response(update, response_text)

            # Отправляем уведомление пользователю
            try:
                private_message = (
                    f"🚫 Вы были забанены!\n\n"
                    f"📝 Причина: {reason}\n"
                    f"👮 Модератор: {user.first_name}\n\n"
                    f"Бан {'постоянный' if result['permanent'] else 'истекает ' + result['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Вы не сможете пользоваться ботом до снятия бана."
                )
                await context.bot.send_message(chat_id=target_user_id, text=private_message)
            except Exception as e:
                self.logger.warning(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")

        else:
            await self.send_response(update, "❌ Ошибка при бане пользователя")

    async def handle_unban(self, update: Update, context: ContextTypes):
        """Обработка команды /unban"""
        await self.safe_execute(update, context, "unban", self._handle_unban, context.args)

    async def _handle_unban(self, update: Update, context: ContextTypes, args: List[str]):
        """Внутренняя обработка команды /unban"""
        user = update.effective_user

        # Проверяем права модератора
        if not await self.is_moderator(update, user.id):
            await self.send_response(update, "❌ У вас нет прав модератора")
            return

        if not args:
            await self.send_response(update,
                "Использование: /unban [пользователь]\n\n"
                "Пример: /unban 123456789"
            )
            return

        # Парсим аргументы
        target_user_id = self.extract_user_id_from_args(args)
        if not target_user_id:
            await self.send_response(update, "❌ Неверный ID пользователя")
            return

        # Разбаниваем пользователя
        success = await self.moderation_service.unban_user(target_user_id, user.id)

        if success:
            # Получаем информацию о цели
            target_profile = await self.user_service.get_or_create_user(target_user_id)
            target_name = target_profile.first_name if target_profile else f"ID:{target_user_id}"

            response_text = (
                f"✅ Пользователь разбанен!\n\n"
                f"👤 Пользователь: {target_name}\n"
                f"🆔 ID: {target_user_id}\n"
                f"👮 Модератор: {user.first_name}"
            )

            await self.send_response(update, response_text)

            # Отправляем уведомление пользователю
            try:
                private_message = (
                    f"✅ Ваш бан был снят!\n\n"
                    f"👮 Модератор: {user.first_name}\n\n"
                    f"Теперь вы можете пользоваться ботом в полном объеме."
                )
                await context.bot.send_message(chat_id=target_user_id, text=private_message)
            except Exception as e:
                self.logger.warning(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")

        else:
            await self.send_response(update, "❌ Пользователь не был забанен или ошибка при разбане")

    async def handle_kick(self, update: Update, context: ContextTypes):
        """Обработка команды /kick"""
        await self.safe_execute(update, context, "kick", self._handle_kick, context.args)

    async def _handle_kick(self, update: Update, context: ContextTypes, args: List[str]):
        """Внутренняя обработка команды /kick"""
        user = update.effective_user

        # Проверяем права модератора
        if not await self.is_moderator(update, user.id):
            await self.send_response(update, "❌ У вас нет прав модератора")
            return

        if len(args) < 2:
            await self.send_response(update,
                "Использование: /kick [пользователь] [причина]\n\n"
                "Пример: /kick 123456789 Нарушение правил чата"
            )
            return

        # Парсим аргументы
        target_user_id = self.extract_user_id_from_args([args[0]])
        if not target_user_id:
            await self.send_response(update, "❌ Неверный ID пользователя")
            return

        reason = ' '.join(args[1:])

        # Пытаемся кикнуть пользователя из чата
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_user_id,
                until_date=None  # Временный бан для кика
            )

            # Разбаниваем через 30 секунд (эффект кика)
            import asyncio
            async def unban_after_delay():
                await asyncio.sleep(30)
                try:
                    await context.bot.unban_chat_member(
                        chat_id=update.effective_chat.id,
                        user_id=target_user_id
                    )
                except Exception as e:
                    self.logger.warning(f"Не удалось автоматически разбанить после кика {target_user_id}: {e}")

            # Запускаем задачу в фоне
            asyncio.create_task(unban_after_delay())

            # Получаем информацию о цели
            target_profile = await self.user_service.get_or_create_user(target_user_id)
            target_name = target_profile.first_name if target_profile else f"ID:{target_user_id}"

            response_text = (
                f"👢 Пользователь кикнут!\n\n"
                f"👤 Пользователь: {target_name}\n"
                f"🆔 ID: {target_user_id}\n"
                f"📝 Причина: {reason}\n"
                f"👮 Модератор: {user.first_name}\n\n"
                f"Пользователь сможет вернуться через 30 секунд."
            )

            await self.send_response(update, response_text)

        except Exception as e:
            await self.send_response(update, f"❌ Ошибка при кике пользователя: {str(e)}")

    async def is_moderator(self, update: Update, user_id: int) -> bool:
        """
        Проверка прав модератора (расширенная проверка прав).

        Args:
            update: Обновление от Telegram
            user_id: ID пользователя

        Returns:
            True если пользователь модератор или администратор
        """
        # Проверяем по списку администраторов в конфигурации
        if user_id in self.config.bot_config.admin_ids:
            return True

        # Проверяем права в чате (администратор = модератор)
        try:
            chat = update.effective_chat
            if chat:
                member = await chat.get_member(user_id)
                return member.status in ['administrator', 'creator']
        except Exception:
            pass

        return False
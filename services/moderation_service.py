"""
Сервис модерации пользователей.
Отвечает за бизнес-логику модерации и администрирования.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from core.exceptions import ValidationError, PermissionError
from utils.validators import InputValidator
import re


@dataclass
class ModerationAction:
    """Действие модерации"""
    action_id: str
    user_id: int
    admin_id: int
    action_type: str
    reason: str
    duration: Optional[int] = None  # в секундах для временных наказаний
    created_at: datetime = None
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.duration and self.expires_at is None:
            self.expires_at = self.created_at + timedelta(seconds=self.duration)


class ModerationService:
    """
    Сервис для модерации пользователей и администрирования.

    Отвечает за:
    - Управление предупреждениями
    - Блокировку и разблокировку пользователей
    - Модерацию контента
    - Проверку прав администраторов
    - Логирование действий модерации
    """

    def __init__(self, user_repository, score_repository):
        """
        Инициализация сервиса.

        Args:
            user_repository: Репозиторий пользователей
            score_repository: Репозиторий очков и рейтингов
        """
        self.user_repo = user_repository
        self.score_repo = score_repository

        # Настройки модерации
        self.moderation_settings = {
            'max_warnings': 3,
            'ban_threshold': 5,
            'mute_duration': 300,  # 5 минут по умолчанию
            'profanity_filter_enabled': True,
            'auto_moderate_media': False
        }

        # Список запрещенных слов
        self.profanity_words = [
            'блядь', 'бля', 'блять', 'хуй', 'хуйня', 'пизда', 'пиздец',
            'ебать', 'ебаный', 'сука', 'сукин', 'мудак', 'говно',
            'fuck', 'shit', 'damn', 'asshole', 'bastard', 'cunt', 'dick', 'bitch'
        ]

        # Активные модерационные действия
        self.active_actions = {}

    async def warn_user(self, user_id: int, reason: str, admin_id: int) -> Dict[str, Any]:
        """
        Выдача предупреждения пользователю.

        Args:
            user_id: ID пользователя
            reason: Причина предупреждения
            admin_id: ID администратора

        Returns:
            Результат действия
        """
        if not InputValidator.validate_text_content(reason, max_length=500):
            raise ValidationError("Неверная причина предупреждения")

        # Добавляем предупреждение в базу данных
        print(f"[DEBUG] ModerationService.warn_user: calling user_repo.add_warning({user_id}, '{reason}', {admin_id})")
        success = self.user_repo.add_warning(user_id, reason, admin_id)

        if not success:
            raise ValidationError("Не удалось выдать предупреждение")

        # Получаем обновленное количество предупреждений
        print(f"[DEBUG] ModerationService.warn_user: calling user_repo.get_user_warnings({user_id})")
        current_warnings = self.user_repo.get_user_warnings(user_id)

        # Проверяем необходимость автоматических действий
        action_taken = None
        if current_warnings >= self.moderation_settings['ban_threshold']:
            action_taken = 'auto_ban'
            await self.ban_user(user_id, "Автоматический бан за превышение лимита предупреждений", admin_id, permanent=True)
        elif current_warnings >= self.moderation_settings['max_warnings']:
            action_taken = 'auto_mute'
            await self.mute_user(user_id, "Автоматическая заглушка за превышение лимита предупреждений", admin_id)

        return {
            'success': True,
            'warnings_count': current_warnings,
            'action_taken': action_taken,
            'reason': reason
        }

    async def mute_user(self, user_id: int, reason: str, admin_id: int, duration: int = None) -> Dict[str, Any]:
        """
        Заглушка пользователя.

        Args:
            user_id: ID пользователя
            reason: Причина заглушки
            admin_id: ID администратора
            duration: Длительность в секундах

        Returns:
            Результат действия
        """
        if duration is None:
            duration = self.moderation_settings['mute_duration']

        if not InputValidator.validate_number(duration, min_value=1, max_value=86400):  # макс 24 часа
            raise ValidationError("Неверная длительность заглушки")

        # Создаем действие модерации
        action_id = f"mute_{user_id}_{admin_id}_{datetime.now().strftime('%H%M%S')}"
        action = ModerationAction(
            action_id=action_id,
            user_id=user_id,
            admin_id=admin_id,
            action_type='mute',
            reason=reason,
            duration=duration
        )

        self.active_actions[action_id] = action

        # Логируем действие в базу данных
        await self._log_moderation_action(user_id, admin_id, 'mute', reason, duration)

        return {
            'success': True,
            'action_id': action_id,
            'duration': duration,
            'expires_at': action.expires_at
        }

    async def ban_user(self, user_id: int, reason: str, admin_id: int, permanent: bool = False) -> Dict[str, Any]:
        """
        Блокировка пользователя.

        Args:
            user_id: ID пользователя
            reason: Причина блокировки
            admin_id: ID администратора
            permanent: Постоянная блокировка

        Returns:
            Результат действия
        """
        duration = None if permanent else (24 * 3600)  # 24 часа по умолчанию

        # Создаем действие модерации
        action_id = f"ban_{user_id}_{admin_id}_{datetime.now().strftime('%H%M%S')}"
        action = ModerationAction(
            action_id=action_id,
            user_id=user_id,
            admin_id=admin_id,
            action_type='ban',
            reason=reason,
            duration=duration
        )

        self.active_actions[action_id] = action

        # Логируем действие в базу данных
        await self._log_moderation_action(user_id, admin_id, 'ban', reason, duration)

        return {
            'success': True,
            'action_id': action_id,
            'permanent': permanent,
            'duration': duration,
            'expires_at': action.expires_at if not permanent else None
        }

    async def unban_user(self, user_id: int, admin_id: int) -> bool:
        """
        Разблокировка пользователя.

        Args:
            user_id: ID пользователя
            admin_id: ID администратора

        Returns:
            True если разблокировка успешна
        """
        # Удаляем все активные действия бана для пользователя
        to_remove = []
        for action_id, action in self.active_actions.items():
            if action.user_id == user_id and action.action_type == 'ban':
                to_remove.append(action_id)

        for action_id in to_remove:
            del self.active_actions[action_id]

        # Логируем действие в базу данных
        await self._log_moderation_action(user_id, admin_id, 'unban', "Разблокировка пользователя")

        return len(to_remove) > 0

    async def unmute_user(self, user_id: int, admin_id: int) -> bool:
        """
        Снятие заглушки с пользователя.

        Args:
            user_id: ID пользователя
            admin_id: ID администратора

        Returns:
            True если снятие заглушки успешно
        """
        # Удаляем все активные действия mute для пользователя
        to_remove = []
        for action_id, action in self.active_actions.items():
            if action.user_id == user_id and action.action_type == 'mute':
                to_remove.append(action_id)

        for action_id in to_remove:
            del self.active_actions[action_id]

        # Логируем действие в базу данных
        await self._log_moderation_action(user_id, admin_id, 'unmute', "Снятие заглушки")

        return len(to_remove) > 0

    def check_profanity(self, text: str) -> List[str]:
        """
        Проверка текста на нецензурную лексику.

        Args:
            text: Проверяемый текст

        Returns:
            Список найденных запрещенных слов
        """
        if not self.moderation_settings['profanity_filter_enabled']:
            return []

        found_words = []
        text_lower = text.lower()

        for word in self.profanity_words:
            if word in text_lower:
                found_words.append(word)

        return found_words

    async def moderate_message(self, user_id: int, text: str, chat_id: int) -> Dict[str, Any]:
        """
        Модерация сообщения пользователя.

        Args:
            user_id: ID пользователя
            text: Текст сообщения
            chat_id: ID чата

        Returns:
            Результат модерации
        """
        # Проверяем на нецензурную лексику
        profanity_words = self.check_profanity(text)

        if profanity_words:
            # Автоматически выдаем предупреждение за нецензурную лексику
            admin_id = 0  # Системный администратор для авто-модерации
            await self.warn_user(user_id, f"Нецензурная лексика: {', '.join(profanity_words)}", admin_id)

            return {
                'action': 'warning',
                'reason': 'Нецензурная лексика',
                'profanity_words': profanity_words
            }

        return {
            'action': 'none',
            'clean': True
        }

    def is_user_muted(self, user_id: int) -> bool:
        """
        Проверка, заглушен ли пользователь.

        Args:
            user_id: ID пользователя

        Returns:
            True если пользователь заглушен
        """
        current_time = datetime.now()

        for action in self.active_actions.values():
            if (action.user_id == user_id and
                action.action_type == 'mute' and
                action.expires_at and
                current_time < action.expires_at):
                return True

        return False

    def is_user_banned(self, user_id: int) -> bool:
        """
        Проверка, забанен ли пользователь.

        Args:
            user_id: ID пользователя

        Returns:
            True если пользователь забанен
        """
        current_time = datetime.now()

        for action in self.active_actions.values():
            if (action.user_id == user_id and
                action.action_type == 'ban' and
                (action.expires_at is None or current_time < action.expires_at)):
                return True

        return False

    async def get_moderation_stats(self) -> Dict[str, Any]:
        """
        Получение статистики модерации.

        Returns:
            Статистика модерации
        """
        # Подсчитываем активные действия
        mutes = sum(1 for action in self.active_actions.values() if action.action_type == 'mute')
        bans = sum(1 for action in self.active_actions.values() if action.action_type == 'ban')

        return {
            'active_mutes': mutes,
            'active_bans': bans,
            'total_actions': len(self.active_actions),
            'profanity_filter_enabled': self.moderation_settings['profanity_filter_enabled']
        }

    async def get_user_moderation_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение истории модерации пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей

        Returns:
            История модерации
        """
        # Здесь будет получение истории из базы данных
        return []

    async def _log_moderation_action(self, user_id: int, admin_id: int, action_type: str,
                                   reason: str, duration: int = None):
        """
        Логирование действия модерации в базу данных.

        Args:
            user_id: ID пользователя
            admin_id: ID администратора
            action_type: Тип действия
            reason: Причина
            duration: Длительность (для временных действий)
        """
        # Здесь будет сохранение в базу данных через репозиторий
        pass

    def cleanup_expired_actions(self):
        """Очистка истекших модерационных действий"""
        current_time = datetime.now()

        to_remove = []
        for action_id, action in self.active_actions.items():
            if (action.expires_at and current_time > action.expires_at):
                to_remove.append(action_id)

        for action_id in to_remove:
            del self.active_actions[action_id]

    def add_profanity_word(self, word: str) -> bool:
        """
        Добавление слова в фильтр нецензурной лексики.

        Args:
            word: Слово для добавления

        Returns:
            True если слово добавлено
        """
        if not InputValidator.validate_text_content(word, max_length=50):
            return False

        if word.lower() not in self.profanity_words:
            self.profanity_words.append(word.lower())
            return True

        return False

    def remove_profanity_word(self, word: str) -> bool:
        """
        Удаление слова из фильтра нецензурной лексики.

        Args:
            word: Слово для удаления

        Returns:
            True если слово удалено
        """
        if word.lower() in self.profanity_words:
            self.profanity_words.remove(word.lower())
            return True

        return False
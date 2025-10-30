"""
Система алертов для телеграм-бота.
Отвечает за отправку уведомлений о критических событиях.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import requests
from .config import Config
from .monitoring import MetricsCollector


class AlertManager:
    """Менеджер алертов для мониторинга системы"""

    def __init__(self, config: Config, metrics: MetricsCollector):
        self.config = config
        self.metrics = metrics
        self.logger = logging.getLogger(__name__)

        # Настройки алертов
        self.alert_rules = {
            'high_error_rate': {
                'enabled': True,
                'threshold': 10,  # ошибок в минуту
                'window': 60,  # секунды
                'cooldown': 300,  # 5 минут между алертами
                'last_alert': None
            },
            'bot_down': {
                'enabled': True,
                'cooldown': 60,
                'last_alert': None
            },
            'high_response_time': {
                'enabled': True,
                'threshold': 5.0,  # секунды
                'cooldown': 300,
                'last_alert': None
            },
            'database_connection_failed': {
                'enabled': True,
                'cooldown': 60,
                'last_alert': None
            }
        }

        # Обработчики алертов
        self.alert_handlers: List[Callable] = [
            self._send_telegram_alert,
            self._send_email_alert,
            self._send_webhook_alert
        ]

    async def check_alerts(self):
        """Проверка и отправка алертов"""
        try:
            # Проверяем правила алертов
            await self._check_error_rate_alert()
            await self._check_bot_status_alert()
            await self._check_response_time_alert()
            await self._check_database_alert()

        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")

    async def _check_error_rate_alert(self):
        """Проверка алерта на высокую частоту ошибок"""
        rule = self.alert_rules['high_error_rate']

        if not rule['enabled']:
            return

        # Получаем количество ошибок за последние N секунд
        # В реальной реализации можно использовать Prometheus метрики
        current_time = datetime.now()
        if (rule['last_alert'] and
            current_time - rule['last_alert'] < timedelta(seconds=rule['cooldown'])):
            return

        # Имитация проверки ошибок (в реальности использовать реальные метрики)
        error_count = self._get_error_count_last_minute()

        if error_count > rule['threshold']:
            await self._trigger_alert(
                'high_error_rate',
                f"Высокая частота ошибок: {error_count} ошибок в минуту (порог: {rule['threshold']})",
                {'error_count': error_count, 'threshold': rule['threshold']}
            )
            rule['last_alert'] = current_time

    async def _check_bot_status_alert(self):
        """Проверка алерта о статусе бота"""
        rule = self.alert_rules['bot_down']

        if not rule['enabled']:
            return

        current_time = datetime.now()
        if (rule['last_alert'] and
            current_time - rule['last_alert'] < timedelta(seconds=rule['cooldown'])):
            return

        # Проверяем статус бота
        if self.metrics.bot_status._value.get() == 0:  # Бот остановлен
            await self._trigger_alert(
                'bot_down',
                "Бот остановлен!",
                {'status': 'down'}
            )
            rule['last_alert'] = current_time

    async def _check_response_time_alert(self):
        """Проверка алерта на высокое время отклика"""
        rule = self.alert_rules['high_response_time']

        if not rule['enabled']:
            return

        current_time = datetime.now()
        if (rule['last_alert'] and
            current_time - rule['last_alert'] < timedelta(seconds=rule['cooldown'])):
            return

        # Имитация проверки времени отклика
        avg_response_time = self._get_average_response_time()

        if avg_response_time > rule['threshold']:
            await self._trigger_alert(
                'high_response_time',
                f"Высокое время отклика: {avg_response_time:.2f}с (порог: {rule['threshold']}с)",
                {'response_time': avg_response_time, 'threshold': rule['threshold']}
            )
            rule['last_alert'] = current_time

    async def _check_database_alert(self):
        """Проверка алерта о проблемах с базой данных"""
        rule = self.alert_rules['database_connection_failed']

        if not rule['enabled']:
            return

        current_time = datetime.now()
        if (rule['last_alert'] and
            current_time - rule['last_alert'] < timedelta(seconds=rule['cooldown'])):
            return

        # Имитация проверки подключения к БД
        if not self._check_database_connection():
            await self._trigger_alert(
                'database_connection_failed',
                "Не удалось подключиться к базе данных!",
                {'status': 'connection_failed'}
            )
            rule['last_alert'] = current_time

    async def _trigger_alert(self, alert_type: str, message: str, extra_data: Dict = None):
        """Отправка алерта через все обработчики"""
        self.logger.warning(f"ALERT [{alert_type}]: {message}")

        # Отправляем алерт через все обработчики
        for handler in self.alert_handlers:
            try:
                await handler(alert_type, message, extra_data or {})
            except Exception as e:
                self.logger.error(f"Error in alert handler {handler.__name__}: {e}")

    async def _send_telegram_alert(self, alert_type: str, message: str, extra_data: Dict):
        """Отправка алерта в Telegram"""
        if not self.config.bot_config.enable_developer_notifications:
            return

        try:
            developer_chat_id = self.config.bot_config.developer_chat_id
            if not developer_chat_id:
                return

            # Добавляем эмодзи для типа алерта
            alert_emojis = {
                'high_error_rate': '🚨',
                'bot_down': '💥',
                'high_response_time': '🐌',
                'database_connection_failed': '🗄️'
            }

            emoji = alert_emojis.get(alert_type, '⚠️')
            alert_message = f"{emoji} <b>АЛЕРТ: {alert_type.replace('_', ' ').title()}</b>\n\n{message}"

            # Добавляем время
            alert_message += f"\n\n⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            # Добавляем дополнительные данные
            if extra_data:
                alert_message += "\n\n📊 Дополнительно:"
                for key, value in extra_data.items():
                    alert_message += f"\n• {key}: {value}"

            # Здесь нужно отправить сообщение через Telegram API
            # В реальной реализации использовать уже созданный бот
            self.logger.info(f"Telegram alert sent: {alert_message[:100]}...")

        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")

    async def _send_email_alert(self, alert_type: str, message: str, extra_data: Dict):
        """Отправка алерта по email"""
        # Заглушка для отправки email
        # В реальной реализации использовать SMTP или сервис вроде SendGrid
        self.logger.info(f"Email alert for {alert_type}: {message}")

    async def _send_webhook_alert(self, alert_type: str, message: str, extra_data: Dict):
        """Отправка алерта через webhook"""
        # Заглушка для webhook
        # В реальной реализации отправлять POST запрос на webhook URL
        self.logger.info(f"Webhook alert for {alert_type}: {message}")

    def _get_error_count_last_minute(self) -> int:
        """Получение количества ошибок за последнюю минуту"""
        # Имитация: в реальности использовать Prometheus метрики
        return 5  # Заглушка

    def _get_average_response_time(self) -> float:
        """Получение среднего времени отклика"""
        # Имитация: в реальности использовать Prometheus метрики
        return 2.5  # Заглушка

    def _check_database_connection(self) -> bool:
        """Проверка подключения к базе данных"""
        # Имитация: в реальности проверить реальное подключение
        return True  # Заглушка

    def add_alert_rule(self, name: str, rule: Dict):
        """Добавление нового правила алерта"""
        self.alert_rules[name] = rule
        self.logger.info(f"Added alert rule: {name}")

    def disable_alert_rule(self, name: str):
        """Отключение правила алерта"""
        if name in self.alert_rules:
            self.alert_rules[name]['enabled'] = False
            self.logger.info(f"Disabled alert rule: {name}")

    def enable_alert_rule(self, name: str):
        """Включение правила алерта"""
        if name in self.alert_rules:
            self.alert_rules[name]['enabled'] = True
            self.logger.info(f"Enabled alert rule: {name}")
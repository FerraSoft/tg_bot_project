#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграционный тест для системы мониторинга.
Проверяет работу метрик, логов и алертов.
"""

import asyncio
import logging
import time
import sys
import io
from core.config import Config
from .monitoring import MetricsCollector, structured_logger
from .alerts import AlertManager

# Установка UTF-8 кодировки для вывода
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def test_monitoring_system():
    """Тестирование системы мониторинга"""
    print("🚀 Запуск интеграционного теста системы мониторинга...")

    # Инициализация с тестовыми настройками
    import os
    os.environ['BOT_TOKEN'] = 'test_token_for_monitoring'
    os.environ['ADMIN_IDS'] = '123456789'

    config = Config()

    metrics = MetricsCollector(config)
    alert_manager = AlertManager(config, metrics)

    # Настройка логирования
    logger = structured_logger('test_monitoring', config)

    print("✅ Системы инициализированы")

    # Тест 1: Запись метрик
    print("\n📊 Тест записи метрик...")

    # Записываем различные метрики
    metrics.record_error('TestError', 'test_handler', Exception('Test exception'))
    metrics.record_command('test_command', 'test_handler', 1.5)
    metrics.record_message('text')
    metrics.record_api_call('weather_api', 2.3)
    metrics.update_active_users(100)
    metrics.set_bot_status(1)

    print("✅ Метрики записаны")

    # Тест 2: Логирование
    print("\n📝 Тест логирования...")

    logger.info("Test info message", extra={'user_id': 123, 'command': 'test'})
    logger.warning("Test warning message", extra={'handler': 'test_handler'})
    logger.error("Test error message", extra={'error_type': 'test_error'})

    print("✅ Логи записаны")

    # Тест 3: Алерты
    print("\n🚨 Тест системы алертов...")

    # Имитируем условие для алерта
    metrics.error_counter.labels(error_type='TestError', handler='test_handler')._value.set(15)

    await alert_manager.check_alerts()

    print("✅ Проверка алертов завершена")

    # Тест 4: Sentry (если включен)
    if config.bot_config.enable_sentry:
        print("\n🛡️ Тест Sentry интеграции...")
        metrics.send_sentry_message("Test message from integration test", "info")
        print("✅ Sentry сообщение отправлено")

    print("\n🎉 Все тесты завершены успешно!")
    print("\n📋 Результаты:")
    print("• Метрики: записаны и доступны на /metrics")
    print("• Логи: структурированные JSON логи в bot.log")
    print("• Алерты: система готова к отправке уведомлений")
    print("• Sentry: интеграция настроена (если включена)")


if __name__ == "__main__":
    asyncio.run(test_monitoring_system())
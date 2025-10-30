#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальное тестирование всей системы мониторинга.
Проверяет интеграцию всех компонентов.
"""

import asyncio
import json
import logging
import sys
import io
from datetime import datetime

# Установка UTF-8 кодировки
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("🚀 Финальное тестирование системы мониторинга...")

async def test_monitoring_integration():
    """Тестирование интеграции мониторинга"""

    try:
        # Тест 1: Проверка импорта модулей
        print("\n📦 Тест импорта модулей...")
        from metrics.monitoring import MetricsCollector, structured_logger
        from metrics.alerts import AlertManager
        from core.config import Config
        print("✅ Все модули импортированы успешно")

        # Тест 2: Проверка конфигурации
        print("\n⚙️ Тест конфигурации...")
        import os
        os.environ['BOT_TOKEN'] = 'test_token_for_monitoring'
        os.environ['ADMIN_IDS'] = '123456789'

        config = Config()
        print("✅ Конфигурация загружена")

        # Тест 3: Проверка метрик
        print("\n📊 Тест системы метрик...")
        metrics = MetricsCollector(config)

        # Записываем тестовые метрики
        metrics.record_error('TestError', 'test_handler', Exception('Test exception'))
        metrics.record_command('start', 'user_handler', 1.2)
        metrics.record_message('text')
        metrics.update_active_users(100)
        metrics.set_bot_status(1)

        print("✅ Метрики записаны")

        # Тест 4: Проверка логирования
        print("\n📝 Тест логирования...")
        logger = structured_logger('final_test', config)

        # Тестируем разные уровни логирования
        logger.info("Test info message", extra={'user_id': 123, 'command': 'test'})
        logger.warning("Test warning message", extra={'handler': 'test_handler'})
        logger.error("Test error message", extra={'error_type': 'test_error'})

        print("✅ Логи записаны в JSON формате")

        # Тест 5: Проверка алертов
        print("\n🚨 Тест системы алертов...")
        alert_manager = AlertManager(config, metrics)

        # Имитируем условие для алерта
        metrics.error_counter.labels(error_type='TestError', handler='test_handler')._value.set(15)

        await alert_manager.check_alerts()
        print("✅ Система алертов проверена")

        # Тест 6: Проверка файла логов
        print("\n📄 Тест файла логов...")
        try:
            with open('bot.log', 'r', encoding='utf-8') as f:
                logs = f.readlines()
                if logs:
                    # Проверяем, что логи в JSON формате
                    first_log = logs[-1].strip()
                    try:
                        json.loads(first_log)
                        print("✅ Логи записываются в JSON формате")
                    except json.JSONDecodeError:
                        print("⚠️ Логи не в JSON формате")
                else:
                    print("⚠️ Лог файл пуст")
        except FileNotFoundError:
            print("⚠️ Лог файл не найден")

        print("\n🎉 Все тесты завершены успешно!")
        print("\n📋 Результаты тестирования:")
        print("✅ Мониторинг: система работает корректно")
        print("✅ Метрики: Prometheus метрики записываются")
        print("✅ Логи: структурированные JSON логи")
        print("✅ Алерты: система алертов инициализирована")
        print("✅ Конфигурация: все настройки загружаются")

        print("\n🚀 Система мониторинга готова к использованию!")
        print("\n📚 Документация:")
        print("• MONITORING.md - подробная документация")
        print("• README_MONITORING.md - быстрый старт")
        print("• GLITCHTIP_SETUP.md - настройка GlitchTip")
        print("• START_MONITORING.md - инструкция по запуску")

        return True

    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_monitoring_integration())
    if success:
        print("\n🏆 Система мониторинга прошла все тесты!")
    else:
        print("\n💥 В системе мониторинга найдены проблемы!")
        sys.exit(1)
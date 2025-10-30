#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест метрик Prometheus без зависимости от конфигурации.
"""

import asyncio
import sys
import io
from prometheus_client import start_http_server, Counter, Histogram, Gauge

# Установка UTF-8 кодировки
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("🚀 Запуск простого тестового сервера метрик...")

# Создаем метрики
error_counter = Counter('telegram_bot_errors_total', 'Total number of errors by type', ['error_type', 'handler'])
command_duration = Histogram('telegram_bot_command_duration_seconds', 'Time spent processing commands', ['command', 'handler'])
active_users = Gauge('telegram_bot_active_users', 'Number of active users')
messages_total = Counter('telegram_bot_messages_total', 'Total number of messages processed', ['message_type'])
bot_status = Gauge('telegram_bot_status', 'Bot operational status (1 = running, 0 = stopped)')

try:
    # Запускаем HTTP сервер
    start_http_server(8000)
    print("✅ Prometheus сервер запущен на порту 8000")
    print("📊 Метрики доступны по адресу: http://localhost:8000/metrics")

    # Устанавливаем статус бота
    bot_status.set(1)
    print("📊 Установлен статус бота: 1 (работает)")

    # Имитируем активность
    print("\n📈 Имитация активности...")

    # Записываем тестовые метрики
    error_counter.labels(error_type='TestError', handler='test_handler').inc(5)
    print("📊 Записано 5 ошибок типа TestError")

    command_duration.labels(command='start', handler='user_handler').observe(1.2)
    command_duration.labels(command='help', handler='user_handler').observe(0.8)
    print("📊 Записано время выполнения команд: start (1.2с), help (0.8с)")

    active_users.set(150)
    print("📊 Установлено активных пользователей: 150")

    messages_total.labels(message_type='text').inc(100)
    messages_total.labels(message_type='command').inc(50)
    print("📊 Записано сообщений: 100 текстовых, 50 команд")

    print("\n🎉 Тест завершен!")
    print("📋 Проверьте метрики на: http://localhost:8000/metrics")
    print("\nПример команды для проверки:")
    print("curl http://localhost:8000/metrics | grep telegram_bot")

    # Держим сервер запущенным
    print("\n⏸️  Сервер работает... Нажмите Ctrl+C для остановки")

    try:
        while True:
            import time
            time.sleep(10)
            # Имитируем обновление метрик каждые 10 секунд
            active_users.set(150 + (time.time() % 50))
    except KeyboardInterrupt:
        print("\n🛑 Остановка сервера...")
        bot_status.set(0)

except Exception as e:
    print(f"❌ Ошибка: {e}")
    print("Убедитесь, что порт 8000 свободен")
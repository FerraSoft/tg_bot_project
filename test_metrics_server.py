#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой сервер для тестирования метрик Prometheus.
"""

import asyncio
import logging
import sys
import io
from prometheus_client import start_http_server, Counter, Histogram, Gauge

# Установка UTF-8 кодировки
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Создаем метрики
error_counter = Counter('telegram_bot_errors_total', 'Total number of errors by type', ['error_type', 'handler'])
command_duration = Histogram('telegram_bot_command_duration_seconds', 'Time spent processing commands', ['command', 'handler'])
active_users = Gauge('telegram_bot_active_users', 'Number of active users')
messages_total = Counter('telegram_bot_messages_total', 'Total number of messages processed', ['message_type'])
bot_status = Gauge('telegram_bot_status', 'Bot operational status (1 = running, 0 = stopped)')

async def test_metrics():
    """Тестирование метрик"""
    print("🚀 Запуск тестового сервера метрик Prometheus...")

    # Запускаем HTTP сервер
    try:
        start_http_server(8000)
        print("✅ Prometheus сервер запущен на порту 8000")
        print("📊 Метрики доступны по адресу: http://localhost:8000/metrics")
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        return

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
    print("\nПример запроса к метрикам:")
    print("curl http://localhost:8000/metrics | grep telegram_bot")

    # Держим сервер запущенным
    print("\n⏸️  Сервер работает... Нажмите Ctrl+C для остановки")

    try:
        while True:
            await asyncio.sleep(10)
            # Имитируем обновление метрик каждые 10 секунд
            active_users.set(150 + (asyncio.get_event_loop().time() % 50))
    except KeyboardInterrupt:
        print("\n🛑 Остановка сервера...")
        bot_status.set(0)

if __name__ == "__main__":
    asyncio.run(test_metrics())
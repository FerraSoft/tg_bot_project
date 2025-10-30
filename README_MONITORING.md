# 📊 Система мониторинга телеграм-бота

## 🚀 Быстрый старт

1. **Установите зависимости:**
   ```bash
   pip install prometheus_client sentry-sdk
   ```

2. **Настройте конфигурацию в `config_local.py`:**
   ```python
   # Включение мониторинга
   ENABLE_SENTRY = True
   SENTRY_DSN = "https://your-dsn@sentry.io/project-id"

   # Настройки Prometheus
   PROMETHEUS_PORT = 8000

   # Уведомления
   ENABLE_DEVELOPER_NOTIFICATIONS = True
   DEVELOPER_CHAT_ID = 123456789
   ```

3. **Запустите бота:**
   ```bash
   python new_bot.py
   ```

4. **Проверьте метрики:**
   - Prometheus: http://localhost:8000/metrics
   - Sentry: https://sentry.io (после настройки DSN)
   - Логи: `bot.log`

## 📈 Метрики

Основные метрики:
- `telegram_bot_errors_total` - ошибки по типам
- `telegram_bot_command_duration_seconds` - время команд
- `telegram_bot_active_users` - активные пользователи
- `telegram_bot_messages_total` - количество сообщений
- `telegram_bot_status` - статус бота

## 🔔 Алерты

Система автоматически отправляет алерты при:
- Высокой частоте ошибок (>10 в минуту)
- Падении бота
- Медленном отклике (>5 секунд)
- Проблемах с БД

Уведомления приходят в Telegram, email и webhook.

## 📋 Документация

Подробная документация в `MONITORING.md`:
- Настройка и конфигурация
- Использование метрик
- Настройка алертов
- Troubleshooting

## 🧪 Тестирование

```bash
pytest tests/test_monitoring.py -v
```

---

*Система мониторинга реализована и готова к использованию! 🎉*
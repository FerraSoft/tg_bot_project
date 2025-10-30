# 📊 Система мониторинга ошибок

## Обзор

Система мониторинга телеграм-бота включает в себя комплексное решение для отслеживания ошибок, производительности и отправки алертов. Реализована с использованием Prometheus, Sentry и кастомной системы алертов.

## 🚀 Компоненты системы

### 1. Логирование (Structured Logging)
- **Формат**: JSON для легкого парсинга
- **Уровни**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Ротация**: Автоматическая ротация логов
- **Интеграция**: Отправка ERROR и выше в Sentry

### 2. Метрики (Prometheus)
- **Сервер метрик**: HTTP endpoint на порту 8000 (настраиваемо)
- **Собираемые метрики**:
  - `telegram_bot_errors_total` - количество ошибок по типам
  - `telegram_bot_command_duration_seconds` - время выполнения команд
  - `telegram_bot_active_users` - количество активных пользователей
  - `telegram_bot_messages_total` - общее количество сообщений
  - `telegram_bot_api_response_time_seconds` - время отклика внешних API
  - `telegram_bot_status` - статус бота (1=работает, 0=остановлен)

### 3. Мониторинг ошибок (Sentry)
- **Автоматический захват**: Все необработанные исключения
- **Performance monitoring**: Отслеживание производительности
- **Фильтрация**: Исключение тестовых данных и чувствительной информации
- **Контекст**: Добавление информации о боте и конфигурации

### 4. Система алертов (AlertManager)
- **Типы алертов**:
  - Высокая частота ошибок (>10 в минуту)
  - Падение бота
  - Высокое время отклика (>5 секунд)
  - Проблемы с подключением к БД
- **Каналы уведомлений**:
  - Telegram (разработчикам)
  - Email
  - Webhook

## 🛠 Настройка

### 1. Установка зависимостей

```bash
pip install prometheus_client sentry-sdk
```

### 2. Конфигурация

Добавьте в `config_local.py`:

```python
# Включение мониторинга
ENABLE_SENTRY = True
SENTRY_DSN = "https://your-dsn@sentry.io/project-id"

# Настройки Prometheus
PROMETHEUS_PORT = 8000

# Уведомления разработчиков
ENABLE_DEVELOPER_NOTIFICATIONS = True
DEVELOPER_CHAT_ID = 123456789  # ID чата для алертов
```

### 3. Переменные окружения

```bash
export ENABLE_SENTRY=true
export SENTRY_DSN="https://your-dsn@sentry.io/project-id"
export PROMETHEUS_PORT=8000
export DEVELOPER_CHAT_ID=123456789
```

## 📈 Использование метрик

### Prometheus endpoint
```
http://localhost:8000/metrics
```

### Пример запросов к метрикам

```promql
# Количество ошибок в минуту
rate(telegram_bot_errors_total[1m])

# Среднее время отклика команд
rate(telegram_bot_command_duration_seconds_sum[5m]) / rate(telegram_bot_command_duration_seconds_count[5m])

# Активные пользователи
telegram_bot_active_users

# Статус бота
telegram_bot_status
```

## 🎯 Настройка алертов

### Добавление нового правила алерта

```python
from .alerts import AlertManager

# В Application или где-то еще
alert_manager = AlertManager(config, metrics)

# Добавляем новое правило
alert_manager.add_alert_rule('custom_rule', {
    'enabled': True,
    'threshold': 100,
    'cooldown': 600,  # 10 минут
    'last_alert': None
})
```

### Отключение алерта

```python
alert_manager.disable_alert_rule('high_error_rate')
```

## 🔧 Интеграция в код

### Использование декораторов

```python
from core.monitoring import measure_time, error_handler

class MyHandler(BaseHandler):
    @measure_time(metrics, 'weather_api')
    async def call_external_api(self):
        # Код API вызова
        pass

    @error_handler(metrics, 'my_handler')
    async def risky_operation(self):
        # Рискованный код
        pass
```

### Ручная запись метрик

```python
# Запись ошибки
metrics.record_error('DatabaseError', 'user_handler', exception)

# Запись команды
metrics.record_command('start', 'user_handler', duration)

# Запись сообщения
metrics.record_message('text')

# Обновление активных пользователей
metrics.update_active_users(150)
```

## 📊 Grafana дашборды

### Рекомендуемые панели

1. **Обзор ошибок**
   - График количества ошибок по времени
   - Разбивка по типам ошибок
   - Топ обработчиков с ошибками

2. **Производительность**
   - Время отклика команд
   - Среднее время API вызовов
   - Загрузка системы

3. **Активность пользователей**
   - Количество активных пользователей
   - Общее количество сообщений
   - Топ команд

4. **Системные метрики**
   - Статус бота
   - Использование памяти/CPU
   - Состояние подключений

### Пример конфигурации datasource

```json
{
  "name": "Telegram Bot Prometheus",
  "type": "prometheus",
  "url": "http://localhost:8000",
  "access": "proxy"
}
```

## 🧪 Тестирование

### Запуск тестов мониторинга

```bash
pytest tests/test_monitoring.py -v
```

### Имитация ошибок для тестирования

```python
# В коде для тестирования
import time

async def test_error_scenario():
    # Имитация медленного ответа
    await asyncio.sleep(6)  # > 5 секунд для триггера алерта

    # Имитация ошибки
    raise ValueError("Test error for monitoring")
```

## 🚨 Troubleshooting

### Проблемы с Prometheus

1. **Метрики не собираются**
   - Проверьте порт 8000
   - Убедитесь, что `prometheus_client` установлен

2. **Высокая нагрузка**
   - Уменьшите частоту сбора метрик
   - Используйте sampling для высоконагруженных endpoint'ов

### Проблемы с Sentry

1. **Ошибки не отправляются**
   - Проверьте SENTRY_DSN
   - Убедитесь, что ENABLE_SENTRY=true
   - Проверьте сетевые настройки

2. **Слишком много событий**
   - Настройте фильтры в `_before_send_sentry`
   - Увеличьте `traces_sample_rate`

### Проблемы с алертами

1. **Алерты не приходят**
   - Проверьте DEVELOPER_CHAT_ID
   - Убедитесь, что бот имеет права отправки сообщений

2. **Слишком много алертов**
   - Увеличьте cooldown в правилах
   - Настройте пороги срабатывания

## 📋 TODO для продакшена

- [ ] Настроить мониторинг ресурсов сервера (CPU, память, диск)
- [ ] Добавить health checks endpoint
- [ ] Интегрировать с внешними системами мониторинга
- [ ] Настроить retention политику для метрик и логов
- [ ] Добавить A/B тестирование алертов
- [ ] Создать runbook для реагирования на алерты

## 🤝 Вклад в развитие

При добавлении новых метрик или алертов:

1. Добавьте описание в эту документацию
2. Обновите тесты
3. Убедитесь в обратной совместимости
4. Протестируйте в staging окружении

## 📞 Поддержка

При проблемах с системой мониторинга:

1. Проверьте логи в `bot.log`
2. Посмотрите метрики в Prometheus
3. Проверьте настройки в Sentry
4. Обратитесь к разработчикам

---

*Последнее обновление: Октябрь 2025*
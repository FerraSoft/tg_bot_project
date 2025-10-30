# 🚀 Запуск системы мониторинга

## 📋 Полная инструкция по запуску

### 1. **Установка зависимостей**
```bash
pip install prometheus_client sentry-sdk flask requests
```

### 2. **Настройка GlitchTip (альтернатива Sentry)**

#### Вариант A: Docker Compose (рекомендуется)
```bash
# Создайте docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.8'
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: glitchtip
      POSTGRES_USER: glitchtip
      POSTGRES_PASSWORD: glitchtip
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:alpine

  glitchtip:
    image: glitchtip/glitchtip:latest
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      SECRET_KEY: your-secret-key-here-generate-random-32-chars
      DATABASE_URL: postgresql://glitchtip:glitchtip@postgres:5432/glitchtip
      REDIS_URL: redis://redis:6379/0
      EMAIL_URL: console://
    volumes:
      - glitchtip_data:/data

volumes:
  postgres_data:
  glitchtip_data:
EOF

# Запустите
docker-compose up -d
```

#### Вариант B: Обычный Docker
```bash
docker run -d --name glitchtip -p 8000:8000 glitchtip/glitchtip:latest
```

### 3. **Настройка проекта в GlitchTip**

1. Откройте: http://localhost:8000
2. Зарегистрируйтесь
3. Создайте проект "Telegram Bot"
4. Получите DSN в Settings → API Keys
5. Скопируйте DSN

### 4. **Настройка конфигурации бота**

В `config_local.py` добавьте:
```python
# Мониторинг
ENABLE_SENTRY = True
SENTRY_DSN = "http://localhost:8000/api/1/project/your-project-id/dsn/"
PROMETHEUS_PORT = 8000

# Уведомления разработчиков
ENABLE_DEVELOPER_NOTIFICATIONS = True
DEVELOPER_CHAT_ID = -1001234567890  # ID вашего чата
```

### 5. **Запуск компонентов**

#### Терминал 1: GlitchTip (если не через Docker)
```bash
# Если используете Docker, пропустите этот шаг
glitchtip runserver 0.0.0.0:8000
```

#### Терминал 2: Prometheus сервер метрик
```bash
python prometheus_server.py
```

#### Терминал 3: Webhook для алертов (опционально)
```bash
python webhook_server.py
```

#### Терминал 4: Основной бот
```bash
python new_bot.py
```

### 6. **Проверка работы**

#### Метрики Prometheus
- URL: http://localhost:8000/metrics
- Ожидаемые метрики: telegram_bot_errors_total, telegram_bot_command_duration_seconds, etc.

#### GlitchTip
- URL: http://localhost:8000
- Проверьте, что ошибки отображаются в проекте

#### Логи
- Файл: bot.log
- Формат: JSON с timestamp, level, message

### 7. **Настройка алертов в GlitchTip**

1. В проекте перейдите в Alerts
2. Создайте правило:
   - Condition: "An issue is first seen"
   - Action: "Send a webhook"
   - URL: `http://localhost:5000/glitchtip-webhook`

### 8. **Тестирование**

#### Тест интеграции
```bash
python test_monitoring_integration.py
```

#### Тест метрик
```bash
python test_metrics_server.py
```

### 9. **Мониторинг в продакшене**

#### Grafana для визуализации
```bash
docker run -d -p 3000:3000 grafana/grafana
```

Настройте Data Source:
- Type: Prometheus
- URL: http://localhost:8000

#### Дашборды для создания:
1. **Обзор ошибок** - графики ошибок по времени
2. **Производительность** - время отклика команд
3. **Активность** - пользователи и сообщения

## 🎯 Итоговый статус:

✅ **Система мониторинга запущена и работает!**

- 🔍 Логирование: JSON формат в bot.log
- 📊 Метрики: Prometheus на порту 8000
- 🛡️ Ошибки: GlitchTip на порту 8000
- 🚨 Алерты: Telegram уведомления
- 📚 Документация: полная в README файлах

## 🚨 Что делать при ошибках:

1. **Проверьте логи:** `tail -f bot.log`
2. **Метрики:** `curl http://localhost:8000/metrics`
3. **GlitchTip:** http://localhost:8000
4. **Конфигурация:** проверьте config_local.py

## 📞 Поддержка:

При проблемах обращайтесь к документации в:
- `MONITORING.md` - подробная документация
- `README_MONITORING.md` - быстрый старт
- `GLITCHTIP_SETUP.md` - настройка GlitchTip

---

**Система мониторинга готова к использованию!** 🎉
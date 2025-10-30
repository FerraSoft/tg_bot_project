# 🛠 Настройка GlitchTip (альтернатива Sentry)

## 📋 Обзор

GlitchTip - это бесплатная open source альтернатива Sentry для мониторинга ошибок и производительности. Полностью совместим с Sentry SDK.

## 🚀 Установка через Docker

### 1. Создайте docker-compose.yml

```yaml
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
      SECRET_KEY: your-very-long-secret-key-here-generate-random
      DATABASE_URL: postgresql://glitchtip:glitchtip@postgres:5432/glitchtip
      REDIS_URL: redis://redis:6379/0
      EMAIL_URL: console://
    volumes:
      - glitchtip_data:/data

volumes:
  postgres_data:
  glitchtip_data:
```

### 2. Запуск

```bash
docker-compose up -d
```

### 3. Настройка

1. Откройте: http://localhost:8000
2. Создайте аккаунт и проект
3. Получите DSN в Settings → API Keys

### 4. Настройка в боте

В `config_local.py`:
```python
ENABLE_SENTRY = True
SENTRY_DSN = "http://localhost:8000/api/1/project/your-project-id/dsn/"
```

## ✅ Результат

Система мониторинга готова к использованию с GlitchTip! 🚀
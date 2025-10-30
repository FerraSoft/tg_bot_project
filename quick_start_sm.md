# 🚀 Быстрый старт системы мониторинга

## ⏱ 5 минут на запуск!

### 1. **Установка** (1 минута)
```bash
cd telegram_bot
pip install -r requirements.txt
```

### 2. **Настройка GlitchTip** (2 минуты)
```bash
# Создайте docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  glitchtip:
    image: glitchtip/glitchtip:latest
    ports: ["8000:8000"]
    environment:
      SECRET_KEY: your-secret-key-here
      DATABASE_URL: sqlite:///db.sqlite3
EOF

# Запустите
docker-compose up -d
```

### 3. **Настройка бота** (1 минута)
В `config_local.py` добавьте:
```python
# Мониторинг
ENABLE_SENTRY = True
SENTRY_DSN = "http://localhost:8000/api/1/project/your-project-id/dsn/"
PROMETHEUS_PORT = 8000
ENABLE_DEVELOPER_NOTIFICATIONS = True
DEVELOPER_CHAT_ID = 123456789
```

### 4. **Запуск** (1 минута)
```bash
python new_bot.py
```

### 5. **Проверка**
- 🌐 GlitchTip: http://localhost:8000
- 📊 Метрики: http://localhost:8000/metrics
- 📝 Логи: `bot.log`

## 🎉 Готово!

Система мониторинга работает! Все ошибки и метрики отслеживаются автоматически.

**Документация:**
- Подробно: `MONITORING.md`
- Быстрый старт: `README_MONITORING.md`
- GlitchTip: `GLITCHTIP_SETUP.md`

**Тестирование:**
```bash
python final_test.py  # Финальное тестирование
python setup_monitoring.py  # Проверка настройки
```

---
*Система мониторинга запущена за 5 минут! 🚀*
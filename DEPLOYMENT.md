# 🚀 Руководство по развертыванию телеграм-бота

## 📋 Содержание
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Запуск](#запуск)
- [Docker развертывание](#docker-развертывание)
- [Мониторинг](#мониторинг)
- [Резервное копирование](#резервное-копирование)

## 🏃‍♂️ Быстрый старт

### 1. Получите токен бота
1. Создайте бота через [@BotFather](https://t.me/botfather) в Telegram
2. Сохраните токен в безопасном месте

### 2. Настройте конфигурацию
```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Откройте .env и заполните реальные значения
nano .env
```

**Обязательные настройки:**
```env
BOT_TOKEN=123456789:ВАШ_РЕАЛЬНЫЙ_ТОКЕН_ЗДЕСЬ
ADMIN_IDS=123456789
DEVELOPER_CHAT_ID=123456789
```

**Опциональные API ключи:**
```env
OPENWEATHER_API_KEY=ваш_ключ_погоды
NEWS_API_KEY=ваш_ключ_новостей
OPENAI_API_KEY=ваш_ключ_openai
```

### 3. Запустите бота
```bash
python run_production.py
```

## ⚙️ Конфигурация

### Файлы конфигурации
- `config_prod.py` - продакшн конфигурация
- `.env` - переменные окружения
- `.env.example` - пример конфигурации

### Основные настройки
| Параметр | Описание | Значение по умолчанию |
|----------|----------|----------------------|
| BOT_TOKEN | Токен телеграм-бота | Обязателен |
| ADMIN_IDS | ID администраторов | Обязателен |
| OPENWEATHER_API_KEY | API ключ для погоды | Опционален |
| NEWS_API_KEY | API ключ для новостей | Опционален |
| LOG_LEVEL | Уровень логирования | INFO |
| DATABASE_URL | Путь к БД | telegram_bot.db |

## 🎯 Запуск

### Локальный запуск
```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
python run_production.py
```

### Запуск в фоновом режиме
```bash
# Linux/macOS
nohup python run_production.py > logs/bot.log 2>&1 &

# Windows
pythonw run_production.py
```

### Системный сервис (Linux)
```bash
# Создать сервис
sudo nano /etc/systemd/system/telegram-bot.service
```

**Содержимое service файла:**
```ini
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/path/to/telegram_bot
ExecStart=/usr/bin/python3 run_production.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Управление сервисом:**
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
sudo systemctl restart telegram-bot
```

## 🐳 Docker развертывание

### Сборка и запуск
```bash
# Сборка образа
docker build -t telegram-bot .

# Запуск контейнера
docker run -d \
  --name telegram-bot \
  -e BOT_TOKEN=ваш_токен \
  -e OPENWEATHER_API_KEY=ваш_ключ \
  -v ./data:/app/data \
  telegram-bot
```

### Docker Compose
```bash
# Скопировать пример .env
cp .env.example .env

# Заполнить .env реальными значениями
nano .env

# Запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### Production Docker
```bash
# Сборка для продакшена
docker build -t telegram-bot:prod .

# Запуск с переменными окружения
docker run -d \
  --name telegram-bot-prod \
  --restart unless-stopped \
  -e BOT_TOKEN=${BOT_TOKEN} \
  -e OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY} \
  -e NEWS_API_KEY=${NEWS_API_KEY} \
  -v /opt/telegram_bot/data:/app/data \
  telegram-bot:prod
```

## 📊 Мониторинг

### Логи
```bash
# Просмотр логов в реальном времени
tail -f logs/bot.log

# Docker логи
docker-compose logs -f telegram-bot
```

### Статус бота
```bash
# Проверка работоспособности
curl -f http://localhost:8080/health || echo "Health check failed"
```

### Мониторинг ресурсов
```bash
# Docker статистика
docker stats telegram-bot

# Системные ресурсы
htop
```

## 💾 Резервное копирование

### Автоматическое резервное копирование
```bash
#!/bin/bash
# Скрипт резервного копирования
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории если не существует
mkdir -p $BACKUP_DIR

# Копирование базы данных
cp telegram_bot.db "$BACKUP_DIR/bot_backup_$DATE.db"

# Упаковка логов
tar -czf "$BACKUP_DIR/logs_backup_$DATE.tar.gz" logs/

# Очистка старых бэкапов (старше 30 дней)
find $BACKUP_DIR -type f -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -type f -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Восстановление из бэкапа
```bash
# Остановка бота
docker-compose down

# Восстановление базы данных
cp backups/bot_backup_YYYYMMDD.db telegram_bot.db

# Запуск бота
docker-compose up -d
```

## 🔧 Обновление

### Обновление кода
```bash
# Остановка бота
docker-compose down

# Получение обновлений
git pull

# Пересборка образа
docker-compose build --no-cache

# Запуск с обновлениями
docker-compose up -d
```

### Проверка обновлений
```bash
# Проверка статуса
docker-compose ps

# Проверка логов после обновления
docker-compose logs -f
```

## 🚨 Устранение неисправностей

### Проблемы с запуском
```bash
# Проверка логов
docker-compose logs telegram-bot

# Проверка переменных окружения
docker-compose exec telegram-bot env

# Проверка подключения к БД
docker-compose exec telegram-bot python -c "from database import UserRepository; print('DB OK')"
```

### Проблемы с токеном
```bash
# Проверка токена
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getMe" | jq .

# Проверка прав бота в группе
# Добавьте бота в группу и дайте права администратора
```

### Проблемы с памятью
```bash
# Очистка Docker
docker system prune -a

# Перезапуск контейнера
docker-compose restart
```

## 📞 Поддержка

### Полезные команды
```bash
# Статус всех сервисов
docker-compose ps

# Логи всех сервисов
docker-compose logs

# Перезапуск всех сервисов
docker-compose restart

# Остановка всех сервисов
docker-compose down

# Очистка неиспользуемых ресурсов
docker system prune
```

### Мониторинг
- **Health check**: `GET /health`
- **Логи**: `logs/bot.log`
- **Метрики**: Интегрируйте с Prometheus/Grafana для продакшена

---

*Последнее обновление: 2025-01-20*
*Версия бота: 2.0.0*
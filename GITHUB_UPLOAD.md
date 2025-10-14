# 📤 Загрузка проекта на GitHub

## Шаги для загрузки проекта на GitHub:

### 1. Создать репозиторий на GitHub
1. Зайдите на [github.com](https://github.com)
2. Нажмите "+" в правом верхнем углу → "New repository"
3. Укажите название репозитория (например, `telegram-bot-scheduler`)
4. Добавьте описание (не обязательно)
5. **НЕ** добавляйте README, .gitignore или лицензию (они уже есть в проекте)
6. Нажмите "Create repository"

### 2. Получить URL репозитория
После создания репозитория скопируйте URL в формате:
- HTTPS: `https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git`
- SSH: `git@github.com:YOUR_USERNAME/YOUR_REPOSITORY.git`

### 3. Добавить удаленный репозиторий
```bash
cd telegram_bot
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

### 4. Загрузить код на GitHub
```bash
git branch -M main
git push -u origin main
```

## 🔧 Если используете SSH (рекомендуется):

### Настройка SSH ключа (если не настроен):
1. Проверьте наличие SSH ключа: `ls ~/.ssh/id_rsa.pub`
2. Если ключа нет, создайте: `ssh-keygen -t rsa -b 4096 -C "your_email@example.com"`
3. Добавьте публичный ключ в GitHub: Settings → SSH and GPG keys → New SSH key

### Использование SSH:
```bash
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

## 🚨 Важные напоминания:

1. **Персональные токены:** Убедитесь, что в файле `config.py` нет реальных токенов бота или API ключей перед загрузкой на GitHub

2. **База данных:** Файл `telegram_bot.db` содержит данные пользователей - решите, нужно ли его загружать (может содержать личную информацию)

3. **CSV файлы:** Файлы с данными пользователей (`chat_*.csv`) могут содержать личную информацию - проверьте перед загрузкой

## 🔍 Проверка статуса репозитория:
```bash
git status                    # Показать статус файлов
git log --oneline            # Показать историю коммитов
git remote -v                # Показать удаленные репозитории
```

## 📁 Структура проекта на GitHub:
```
telegram_bot/
├── bot.py                    # Основной бот
├── scheduler.py             # Планировщик постов
├── database_sqlite.py       # Работа с базой данных
├── migrate_ranks.py         # Миграция системы рангов
├── config.py                # Конфигурация
├── requirements.txt         # Зависимости Python
├── README.md                # Основная документация
├── SCHEDULER_GUIDE.md       # Руководство по планировщику
├── .gitignore              # Исключения Git
└── chat_*.csv              # CSV файлы с данными (опционально)
```

## 🎉 После загрузки:
1. Проект будет доступен по адресу: `https://github.com/YOUR_USERNAME/YOUR_REPOSITORY`
2. Другие разработчики смогут клонировать проект: `git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git`
3. Установите зависимости: `pip install -r requirements.txt`
4. Настройте токены в `config.py`

## 💡 Рекомендации:
- Добавьте лицензию (например, MIT) в репозиторий на GitHub
- Включите подробное описание проекта в README
- Добавьте теги релизов при крупных обновлениях
- Настройте GitHub Actions для автоматического тестирования (опционально)
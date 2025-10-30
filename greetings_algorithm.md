# Алгоритм кодовой реализации разделения приветствий

## Обзор
Реализация разделения приветствий на основе ролей пользователей (user, moderator, admin) для Telegram бота.

## Шаг 1: Обновление файла messages.py
Добавляем новые приветствия в словарь USER_MESSAGES:

```python
# Новые приветствия по ролям
'greetings_by_role': {
    'user': '''Привет, {name}! 👋
Добро пожаловать в чат. Я ваш помощник здесь.
Используйте /help для подробной информации.''',

    'moderator': '''Привет, {name}! 👋
Как модератор, вы можете управлять чатом.
Используйте /help для команд модерации.''',

    'admin': '''Привет, {name}! 👋
Добро пожаловать, администратор. У вас полный доступ к управлению ботом.
Начните с /help для списка команд.'''
}
```

## Шаг 2: Модификация обработчика команды /start

```python
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    user_name = user.first_name or "пользователь"

    # Получить роль пользователя из базы данных
    user_role = database.get_user_role(user_id)

    # Если роль не найдена, назначить 'user' по умолчанию
    if not user_role:
        user_role = USER_ROLES['user']
        database.add_user(user_id, user_name, user_role)

    # Выбрать соответствующее приветствие
    greeting_template = USER_MESSAGES['greetings_by_role'].get(
        user_role,
        USER_MESSAGES['greetings_by_role']['user']  # fallback
    )

    # Форматировать приветствие
    greeting = greeting_template.format(name=user_name)

    await update.message.reply_text(greeting)
```

## Шаг 3: Проверка базы данных
Убедиться, что таблица пользователей содержит поле `role` с значениями:
- 'user' - обычный пользователь
- 'moderator' - модератор
- 'admin' - администратор

## Шаг 4: Тестирование
1. Проверить приветствия для каждого типа роли
2. Убедиться в корректной работе для новых пользователей
3. Проверить fallback для неизвестных ролей
4. Тестировать интеграцию с существующим кодом

## Требования к реализации
- Персонализация приветствий по ролям пользователей
- Fallback на приветствие для обычных пользователей
- Совместимость с существующей архитектурой бота
- Безопасность и валидация данных
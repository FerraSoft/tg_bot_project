# Тесты для Telegram Bot

Этот каталог содержит тесты для различных компонентов телеграм-бота.

## Структура тестов

- `test_services/` - Unit-тесты для сервисов (user_service, game_service)
- `test_utils/` - Тесты для утилит (formatters, helpers, validators, exceptions)
- `test_integration/` - Интеграционные тесты для полного потока
- `test_performance/` - Тесты производительности критических функций

## Запуск тестов

### Unit-тесты сервисов
```bash
python -m pytest test_services/test_game_service.py -v
python -m pytest test_services/test_user_service.py -v
```

### Интеграционные тесты
```bash
python test_games_navigation.py  # Тестирование навигации к играм
python -m pytest test_integration/ -v
```

### Все тесты
```bash
python -m pytest -v
```

## Важные исправления

### Поддержка русского ввода в Rock-Paper-Scissors
Добавлена поддержка русского ввода в game_service.py:
- 'камень' -> 'rock'
- 'ножницы' -> 'scissors'
- 'бумага' -> 'paper'

Тесты в test_game_service.py проверяют эту функциональность.

### Исправление ошибок в тестах
- Исправлен test_games_navigation.py: добавлен game_service в GameHandlers
- Добавлены AsyncMock для Telegram API вызовов
- Исправлены проблемы с валидацией и очисткой сессий

## Автоматическое тестирование

Тесты интегрированы в CI/CD пайплайн через GitHub Actions (.github/workflows/ci.yml).
"""
Вспомогательные функции для телеграм-бота.
Содержит общие утилиты и хелперы для повседневных задач.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from core.exceptions import BotException


def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """
    Безопасное выполнение функции с обработкой исключений.

    Args:
        func: Функция для выполнения
        *args: Позиционные аргументы
        **kwargs: Именованные аргументы

    Returns:
        Результат выполнения функции или None при ошибке
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции {func.__name__}: {e}")
        return None


def chunk_text(text: str, chunk_size: int = 4000) -> List[str]:
    """
    Разбиение текста на части указанного размера.

    Args:
        text: Исходный текст
        chunk_size: Максимальный размер части

    Returns:
        Список частей текста
    """
    if not text:
        return []

    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    return chunks


def escape_markdown(text: str) -> str:
    """
    Экранирование специальных символов Markdown.

    Args:
        text: Текст для экранирования

    Returns:
        Экранированный текст
    """
    if not text:
        return ""

    # Символы, которые нужно экранировать в Markdown
    escape_chars = r'_*`['

    result = text
    for char in escape_chars:
        result = result.replace(char, f'\\{char}')

    return result


def create_chunks(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Разбиение списка на части указанного размера.

    Args:
        items: Исходный список
        chunk_size: Размер части

    Returns:
        Список частей
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def format_number(num: Union[int, float]) -> str:
    """
    Форматирование числа с разделителями тысяч.

    Args:
        num: Число для форматирования

    Returns:
        Отформатированная строка
    """
    try:
        if isinstance(num, float):
            # Для float возвращаем как есть
            return str(num)
        else:
            # Ручное форматирование для кроссплатформенности
            s = str(int(num))
            if len(s) <= 3:
                return s
            groups = []
            while s:
                groups.append(s[-3:])
                s = s[:-3]
            return ','.join(reversed(groups))
    except (ValueError, TypeError):
        return str(num)


def get_nested_value(data: Dict, path: str, default: Any = None) -> Any:
    """
    Получение значения из вложенного словаря по пути.

    Args:
        data: Исходный словарь
        path: Путь к значению (через точку)
        default: Значение по умолчанию

    Returns:
        Значение или default

    Example:
        data = {'user': {'profile': {'name': 'John'}}}
        get_nested_value(data, 'user.profile.name')  # 'John'
    """
    keys = path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def set_nested_value(data: Dict, path: str, value: Any) -> Dict:
    """
    Установка значения во вложенный словарь по пути.

    Args:
        data: Исходный словарь
        path: Путь к значению (через точку)
        value: Значение для установки

    Returns:
        Обновленный словарь

    Example:
        data = {}
        set_nested_value(data, 'user.profile.name', 'John')
        # data = {'user': {'profile': {'name': 'John'}}}
    """
    keys = path.split('.')
    current = data

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
    return data


def retry_async(max_attempts: int = 3, delay: float = 1.0):
    """
    Декоратор для повторных попыток асинхронных функций.

    Args:
        max_attempts: Максимальное количество попыток
        delay: Задержка между попытками в секундах
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def validate_required_fields(data: Dict, required_fields: List[str]) -> bool:
    """
    Проверка наличия обязательных полей в данных.

    Args:
        data: Словарь с данными
        required_fields: Список обязательных полей

    Returns:
        True если все поля присутствуют

    Raises:
        ValidationError: Если отсутствуют обязательные поля
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise ValidationError(f"Отсутствуют обязательные поля: {', '.join(missing_fields)}")

    return True


def calculate_percentage(part: Union[int, float], total: Union[int, float]) -> float:
    """
    Вычисление процента.

    Args:
        part: Часть от целого
        total: Целое

    Returns:
        Процент (0-100)
    """
    try:
        if total == 0:
            return 0.0
        return (float(part) / float(total)) * 100
    except (ValueError, TypeError):
        return 0.0


def format_duration(seconds: int) -> str:
    """
    Форматирование длительности в читаемый вид.

    Args:
        seconds: Длительность в секундах

    Returns:
        Отформатированная строка
    """
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes} мин {remaining_seconds} сек"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ч {minutes} мин"


def is_empty(value: Any) -> bool:
    """
    Проверка значения на пустоту.

    Args:
        value: Значение для проверки

    Returns:
        True если значение пустое
    """
    if value is None:
        return True

    if isinstance(value, (str, list, dict, tuple)):
        return len(value) == 0

    return False


def generate_user_mention(user_id: int, name: str) -> str:
    """
    Генерация упоминания пользователя.

    Args:
        user_id: ID пользователя
        name: Имя пользователя

    Returns:
        Строка упоминания в формате Markdown
    """
    return f"[{name}](tg://user?id={user_id})"


def clean_string(text: str) -> str:
    """
    Очистка строки от лишних пробелов и символов.

    Args:
        text: Исходная строка

    Returns:
        Очищенная строка
    """
    if not text:
        return ""

    # Удаляем лишние пробелы и переносы строк
    cleaned = ' '.join(text.split())
    return cleaned.strip()


def merge_dicts(*dicts: Dict) -> Dict:
    """
    Объединение словарей с приоритетом последних.

    Args:
        *dicts: Словари для объединения

    Returns:
        Объединенный словарь
    """
    result = {}

    for d in dicts:
        if d:
            result.update(d)

    return result


def filter_dict(data: Dict, keys: List[str]) -> Dict:
    """
    Фильтрация словаря по ключам.

    Args:
        data: Исходный словарь
        keys: Ключи для сохранения

    Returns:
        Отфильтрованный словарь
    """
    return {k: v for k, v in data.items() if k in keys}


def async_context_manager(func: Callable) -> Callable:
    """
    Декоратор для создания асинхронного контекстного менеджера.

    Args:
        func: Функция для декорирования

    Returns:
        Декорированная функция
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    return wrapper
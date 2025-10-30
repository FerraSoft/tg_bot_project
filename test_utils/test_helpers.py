"""
Тесты для вспомогательных функций.
Проверяет корректность работы utility функций.
"""

import pytest
from utils.helpers import (
    safe_execute, chunk_text, escape_markdown, create_chunks,
    format_number, get_nested_value, set_nested_value, calculate_percentage,
    format_duration, is_empty, generate_user_mention, clean_string,
    merge_dicts, filter_dict
)


class TestSafeExecute:
    """Тесты функции safe_execute"""

    def test_safe_execute_success(self):
        """Тест успешного выполнения функции"""
        def test_func(x, y):
            return x + y

        result = safe_execute(test_func, 5, 3)
        assert result == 8

    def test_safe_execute_exception(self):
        """Тест выполнения функции с исключением"""
        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func)
        assert result is None

    def test_safe_execute_with_params(self):
        """Тест выполнения функции с параметрами"""
        def multiply(a, b=1):
            return a * b

        result = safe_execute(multiply, 5, b=3)
        assert result == 15


class TestTextUtilities:
    """Тесты текстовых утилит"""

    def test_chunk_text_empty(self):
        """Тест разбиения пустого текста"""
        result = chunk_text("")
        assert result == []

    def test_chunk_text_normal(self):
        """Тест разбиения текста на части"""
        text = "A" * 100
        result = chunk_text(text, 50)

        assert len(result) == 2
        assert len(result[0]) == 50
        assert len(result[1]) == 50

    def test_escape_markdown(self):
        """Тест экранирования markdown"""
        text = "Text with *special* _characters_ `code` [link]"
        result = escape_markdown(text)

        assert "\\*" in result
        assert "\\_" in result
        assert "\\`" in result
        assert "\\[" in result

    def test_escape_markdown_empty(self):
        """Тест экранирования пустого текста"""
        assert escape_markdown("") == ""
        assert escape_markdown(None) == ""


class TestDataUtilities:
    """Тесты утилит работы с данными"""

    def test_create_chunks(self):
        """Тест разбиения списка на части"""
        items = list(range(10))
        result = create_chunks(items, 3)

        assert len(result) == 4
        assert result[0] == [0, 1, 2]
        assert result[1] == [3, 4, 5]
        assert result[2] == [6, 7, 8]
        assert result[3] == [9]

    def test_format_number(self):
        """Тест форматирования числа"""
        assert format_number(1234) == "1,234"
        assert format_number(1234567) == "1,234,567"
        assert format_number(123.456) == "123.456"
        assert format_number("not_a_number") == "not_a_number"

    def test_get_nested_value(self):
        """Тест получения вложенного значения"""
        data = {
            'user': {
                'profile': {
                    'name': 'John',
                    'age': 30
                }
            }
        }

        assert get_nested_value(data, 'user.profile.name') == 'John'
        assert get_nested_value(data, 'user.profile.age') == 30
        assert get_nested_value(data, 'user.profile.email') is None
        assert get_nested_value(data, 'nonexistent.key', 'default') == 'default'

    def test_set_nested_value(self):
        """Тест установки вложенного значения"""
        data = {}

        result = set_nested_value(data, 'user.profile.name', 'John')

        assert result['user']['profile']['name'] == 'John'
        assert data['user']['profile']['name'] == 'John'

    def test_calculate_percentage(self):
        """Тест вычисления процента"""
        assert calculate_percentage(25, 100) == 25.0
        assert abs(calculate_percentage(1, 3) - 33.333333333333336) < 1e-10
        assert calculate_percentage(0, 100) == 0.0
        assert calculate_percentage(10, 0) == 0.0

    def test_format_duration(self):
        """Тест форматирования длительности"""
        assert format_duration(30) == "30 сек"
        assert format_duration(90) == "1 мин 30 сек"
        assert format_duration(3661) == "1 ч 1 мин"
        assert format_duration(7323) == "2 ч 2 мин"

    def test_is_empty(self):
        """Тест проверки на пустоту"""
        assert is_empty(None) is True
        assert is_empty("") is True
        assert is_empty([]) is True
        assert is_empty({}) is True
        assert is_empty("text") is False
        assert is_empty([1, 2, 3]) is False

    def test_generate_user_mention(self):
        """Тест генерации упоминания пользователя"""
        result = generate_user_mention(123456789, "John Doe")
        assert result == "[John Doe](tg://user?id=123456789)"

    def test_clean_string(self):
        """Тест очистки строки"""
        assert clean_string("  Text with   spaces  ") == "Text with spaces"
        assert clean_string("Text\nwith\nnewlines") == "Text with newlines"
        assert clean_string("  ") == ""
        assert clean_string(None) == ""

    def test_merge_dicts(self):
        """Тест объединения словарей"""
        dict1 = {'a': 1, 'b': 2}
        dict2 = {'b': 3, 'c': 4}
        dict3 = {'c': 5, 'd': 6}

        result = merge_dicts(dict1, dict2, dict3)

        assert result == {'a': 1, 'b': 3, 'c': 5, 'd': 6}

    def test_filter_dict(self):
        """Тест фильтрации словаря"""
        data = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        keys = ['a', 'c']

        result = filter_dict(data, keys)

        assert result == {'a': 1, 'c': 3}
        assert 'b' not in result
        assert 'd' not in result


class TestEdgeCases:
    """Тесты краевых случаев"""

    def test_calculate_percentage_edge_cases(self):
        """Тест вычисления процента в краевых случаях"""
        assert calculate_percentage(0, 0) == 0.0
        assert calculate_percentage(-10, 100) == -10.0
        assert calculate_percentage(10, -5) == -200.0

    def test_format_duration_edge_cases(self):
        """Тест форматирования длительности в краевых случаях"""
        assert format_duration(0) == "0 сек"
        assert format_duration(-10) == "-10 сек"

    def test_merge_dicts_with_none(self):
        """Тест объединения словарей с None значениями"""
        dict1 = {'a': 1}
        dict2 = None
        dict3 = {'b': 2}

        result = merge_dicts(dict1, dict2, dict3)

        assert result == {'a': 1, 'b': 2}

    def test_filter_dict_empty_keys(self):
        """Тест фильтрации словаря с пустым списком ключей"""
        data = {'a': 1, 'b': 2}

        result = filter_dict(data, [])

        assert result == {}
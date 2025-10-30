"""
Тестовый пакет для телеграм-бота.
Содержит все тесты для проверки корректности работы системы.
"""

import sys
import os

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Общие тестовые утилиты и фикстуры
from .conftest import *

__version__ = "1.0.0"
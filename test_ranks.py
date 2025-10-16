#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест системы рангов
"""

import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_sqlite import Database
from messages import RANK_THRESHOLDS

def test_rank_calculation():
    """Тестирование расчета рангов"""
    db = Database()

    print("Testing rank system...\n")

    # Тестовые значения репутации и ожидаемые ранги
    test_cases = [
        (0, "Рядовой"),
        (50, "Рядовой"),
        (100, "Ефрейтор"),
        (200, "Ефрейтор"),
        (235, "Младший сержант"),
        (400, "Младший сержант"),
        (505, "Сержант"),
        (700, "Сержант"),
        (810, "Старший сержант"),
        (1000, "Старший сержант"),
        (1250, "Старшина"),
        (1500, "Старшина"),
        (1725, "Прапорщик"),
        (2000, "Прапорщик"),
        (2335, "Старший прапорщик"),
        (2500, "Старший прапорщик"),
        (2980, "Младший лейтенант"),
        (3500, "Младший лейтенант"),
        (3760, "Лейтенант"),
        (4000, "Лейтенант"),
        (4575, "Старший лейтенант"),
        (5000, "Старший лейтенант"),
        (5525, "Капитан"),
        (6000, "Капитан"),
        (6112, "Капитан"),  # Это значение из примера в TODO
        (6510, "Майор"),
        (7000, "Майор"),
        (256000, "Маршал"),  # Максимальный ранг
    ]

    print("Rank thresholds:")
    for threshold, rank_name in RANK_THRESHOLDS:
        print(f"  {threshold:6} points -> {rank_name}")
    print()

    print("Test results:")
    all_passed = True

    for reputation, expected_rank in test_cases:
        calculated_rank = db.calculate_rank(reputation)
        status = "PASS" if calculated_rank == expected_rank else "FAIL"
        if calculated_rank != expected_rank:
            all_passed = False
        print(f"  {status} {reputation:6} points -> {calculated_rank}"+" "*(20-len(calculated_rank)) + f"(expected: {expected_rank})")

    print()
    if all_passed:
        print("All tests passed successfully!")
    else:
        print("Some tests failed!")

    # Проверка конкретного примера из TODO (6112 очков должны давать Капитана)
    print(f"\nChecking TODO example:")
    print(f"   6112 points -> {db.calculate_rank(6112)} (should be Капитан)")

    db.close()
    return all_passed

if __name__ == "__main__":
    test_rank_calculation()
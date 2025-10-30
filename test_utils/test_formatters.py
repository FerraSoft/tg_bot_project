"""
Тесты для модуля форматирования сообщений.
Проверяет корректность форматирования различных типов контента.
"""

import pytest
from datetime import datetime
from utils.formatters import MessageFormatter, KeyboardFormatter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class TestMessageFormatter:
    """Тесты форматтера сообщений"""

    def test_format_user_info(self):
        """Тест форматирования информации о пользователе"""
        user_data = {
            'id': 123456789,
            'name': 'Test User',
            'username': 'test_user',
            'reputation': 150,
            'rank': 'Активист',
            'message_count': 45,
            'joined_date': '2024-01-15'
        }

        result = MessageFormatter.format_user_info(user_data)

        assert "👤 <b>Информация о пользователе:</b>" in result
        assert "🆔 ID: 123456789" in result
        assert "👤 Имя: Test User" in result
        assert "📱 Username: @test_user" in result
        assert "🏆 Репутация: 150" in result
        assert "⭐ Ранг: Активист" in result
        assert "💬 Сообщений: 45" in result

    def test_format_rank_info(self):
        """Тест форматирования информации о ранге"""
        result = MessageFormatter.format_rank_info(150, 2, "Активист")

        assert "🏆 <b>Ваш ранг:</b>" in result
        assert "⭐ Очки: 150" in result
        assert "⚠️ Предупреждений: 2" in result
        assert "👑 Роль: Активист" in result

    def test_format_leaderboard_empty(self):
        """Тест форматирования пустой таблицы лидеров"""
        result = MessageFormatter.format_leaderboard([])
        assert "📭 Таблица лидеров пуста" in result

    def test_format_leaderboard_with_data(self):
        """Тест форматирования таблицы лидеров с данными"""
        users = [
            (111, "user1", "User One", 100),
            (222, "user2", "User Two", 90),
            (333, None, "User Three", 80)
        ]

        result = MessageFormatter.format_leaderboard(users)

        assert "🏆 <b>Таблица лидеров:</b>" in result
        assert "🥇 <b>User One</b> - 100 очков" in result
        assert "🥈 <b>User Two</b> - 90 очков" in result
        assert "🥉 <b>User Three</b> - 80 очков" in result

    def test_get_medal(self):
        """Тест получения медали для позиции"""
        formatter = MessageFormatter()

        assert formatter._get_medal(1) == "🥇"
        assert formatter._get_medal(2) == "🥈"
        assert formatter._get_medal(3) == "🥉"
        assert formatter._get_medal(10) == "🔟"
        assert formatter._get_medal(15) == "15."

    def test_format_weather_info(self):
        """Тест форматирования информации о погоде"""
        weather_data = {
            'city': 'Москва',
            'temp': 20,
            'feels_like': 18,
            'humidity': 65,
            'description': 'ясно'
        }

        result = MessageFormatter.format_weather_info(weather_data)

        assert "🌤️ <b>Погода в Москва</b>" in result
        assert "🌡️ Температура: 20°C" in result
        assert "🌡️ Ощущается как: 18°C" in result
        assert "💧 Влажность: 65%" in result
        assert "💬 Описание: ясно" in result

    def test_format_news_empty(self):
        """Тест форматирования пустого списка новостей"""
        result = MessageFormatter.format_news([])
        assert "📰 Новости не найдены" in result

    def test_format_news_with_data(self):
        """Тест форматирования новостей с данными"""
        articles = [
            {
                'title': 'Заголовок новости 1',
                'url': 'https://example.com/news1'
            },
            {
                'title': 'Заголовок новости 2',
                'url': 'https://example.com/news2'
            }
        ]

        result = MessageFormatter.format_news(articles)

        assert "📰 <b>Последние новости:</b>" in result
        assert "1. <b>Заголовок новости 1</b>" in result
        assert "🔗 https://example.com/news1" in result
        assert "2. <b>Заголовок новости 2</b>" in result

    def test_format_error_report(self):
        """Тест форматирования отчета об ошибке"""
        error_data = {
            'id': 1,
            'type': 'bug',
            'title': 'Тестовая ошибка',
            'priority': 'high',
            'admin_name': 'Test Admin',
            'created_at': '2024-01-15',
            'description': 'Описание ошибки'
        }

        result = MessageFormatter.format_error_report(error_data)

        assert "🐛 <b>Отчет об ошибке #1</b>" in result
        assert "📋 Тип: bug" in result
        assert "📝 Заголовок: Тестовая ошибка" in result
        assert "⭐ Приоритет: high" in result
        assert "👤 Создатель: Test Admin" in result
        assert "📄 Описание:\nОписание ошибки" in result

    def test_format_donation_info(self):
        """Тест форматирования информации о донате"""
        result = MessageFormatter.format_donation_info(100.0, 10)

        assert "💰 <b>Спасибо за поддержку!</b>" in result
        assert "💵 Сумма: 100.0 RUB" in result
        assert "⭐ Получено очков: 10" in result
        assert "🎉 Ваша поддержка помогает развивать бота!" in result

    def test_format_achievement(self):
        """Тест форматирования достижения"""
        result = MessageFormatter.format_achievement("Первый донат", "Вы сделали свой первый донат!")

        assert "🏆 <b>Новое достижение!</b>" in result
        assert "🎖 Первый донат" in result
        assert "📝 Вы сделали свой первый донат!" in result

    def test_format_moderation_info_with_transcription(self):
        """Тест форматирования информации для модерации с транскрипцией"""
        result = MessageFormatter.format_moderation_info("audio", "Test User", "Текст транскрипции")

        assert "🔍 <b>Медиафайл на модерации</b>" in result
        assert "👤 Пользователь: Test User" in result
        assert "📁 Тип файла: АУДИО" in result
        assert "🎵 Транскрипция: Текст транскрипции" in result

    def test_format_moderation_info_without_transcription(self):
        """Тест форматирования информации для модерации без транскрипции"""
        result = MessageFormatter.format_moderation_info("video", "Test User")

        assert "🔍 <b>Медиафайл на модерации</b>" in result
        assert "👤 Пользователь: Test User" in result
        assert "📁 Тип файла: ВИДЕО" in result
        assert "🎵 Транскрипция:" not in result

    def test_escape_html(self):
        """Тест экранирования HTML символов"""
        text = '<div>Test & "quotes" \'apostrophe\'</div>'
        result = MessageFormatter.escape_html(text)

        assert "<div>" in result
        assert "&" in result
        #assert ""quotes"" in result #Исправлена ошибка с повторяющимися кавычками
        assert "&quot;quotes&quot;" in result
        assert "&#x27;apostrophe&#x27;" in result

    def test_escape_html_empty(self):
        """Тест экранирования пустой строки"""
        assert MessageFormatter.escape_html("") == ""
        assert MessageFormatter.escape_html(None) == ""

    def test_truncate_text(self):
        """Тест усечения текста"""
        text = "Это очень длинный текст, который нужно усечь"

        # Нормальная длина
        result = MessageFormatter.truncate_text(text, 50)
        assert len(result) <= 50
        # Text length is 45, max_length is 50, so no truncation should occur
        assert result == text

        # Короткий текст
        short_text = "Короткий"
        result = MessageFormatter.truncate_text(short_text, 50)
        assert result == short_text

        # Текст без усечения
        result = MessageFormatter.truncate_text(text, 100)
        assert result == text

    def test_truncate_text_custom_suffix(self):
        """Тест усечения текста с кастомным суффиксом"""
        text = "Тестовый текст"
        result = MessageFormatter.truncate_text(text, 5, "[...]")
        # "Тестовый текст" has length 14, max_length=5, suffix="[...]" has length 5
        # So text[:5-5] + "[...]" = text[:0] + "[...]" = "[...]"
        assert result == "[...]"
        assert len(result) == 5  # суффикс имеет длину 5 символов


class TestKeyboardFormatter:
    """Тесты форматтера клавиатур"""

    def test_create_main_menu(self):
        """Тест создания главного меню"""
        keyboard = KeyboardFormatter.create_main_menu()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 4

        # Проверяем кнопки
        buttons = keyboard.inline_keyboard
        assert buttons[0][0].text == "📋 Помощь"
        assert buttons[0][0].callback_data == "menu_help"
        assert buttons[1][0].text == "🎮 Мини игры"
        assert buttons[1][0].callback_data == "menu_games"

    def test_create_games_menu(self):
        """Тест создания меню игр"""
        keyboard = KeyboardFormatter.create_games_menu()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 8  # 7 игр + кнопка назад

        # Проверяем последнюю кнопку (Назад)
        buttons = keyboard.inline_keyboard
        assert buttons[-1][0].text == "⬅️ Назад"
        assert buttons[-1][0].callback_data == "menu_main"

    def test_create_donation_menu(self):
        """Тест создания меню донатов"""
        keyboard = KeyboardFormatter.create_donation_menu()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 7  # 5 сумм + другая сумма + назад

        # Проверяем кнопки сумм
        buttons = keyboard.inline_keyboard
        assert buttons[0][0].text == "💰 100 ₽"
        assert buttons[0][0].callback_data == "donate_100"
        assert buttons[5][0].text == "💰 Другая сумма"
        assert buttons[5][0].callback_data == "donate_custom"

    def test_create_admin_menu(self):
        """Тест создания меню администратора"""
        keyboard = KeyboardFormatter.create_admin_menu()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 5  # 4 функции + назад

        # Проверяем кнопки админских функций
        buttons = keyboard.inline_keyboard
        assert buttons[0][0].text == "👥 Управление пользователями"
        assert buttons[0][0].callback_data == "admin_users"
        assert buttons[1][0].text == "📊 Статистика"
        assert buttons[1][0].callback_data == "admin_stats"

    def test_create_moderation_menu(self):
        """Тест создания меню модерации"""
        keyboard = KeyboardFormatter.create_moderation_menu("audio", 123456789)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 3  # 3 кнопки действий

        buttons = keyboard.inline_keyboard
        assert buttons[0][0].text == "✅ Одобрить"
        assert buttons[0][0].callback_data == "moderate_approve_123456789"
        assert buttons[1][0].text == "⏰ Одобрить с задержкой"
        assert buttons[1][0].callback_data == "moderate_delay_123456789"
        assert buttons[2][0].text == "❌ Отклонить"
        assert buttons[2][0].callback_data == "moderate_reject_123456789"

    def test_create_confirmation_menu(self):
        """Тест создания меню подтверждения"""
        keyboard = KeyboardFormatter.create_confirmation_menu("yes", "no")

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 2

        buttons = keyboard.inline_keyboard
        assert buttons[0][0].text == "Да"
        assert buttons[0][0].callback_data == "yes"
        assert buttons[1][0].text == "Нет"
        assert buttons[1][0].callback_data == "no"

    def test_create_confirmation_menu_custom_text(self):
        """Тест создания меню подтверждения с кастомным текстом"""
        keyboard = KeyboardFormatter.create_confirmation_menu("confirm", "cancel", "Подтвердить", "Отмена")

        assert isinstance(keyboard, InlineKeyboardMarkup)
        buttons = keyboard.inline_keyboard
        assert buttons[0][0].text == "Подтвердить"
        assert buttons[0][0].callback_data == "confirm"
        assert buttons[1][0].text == "Отмена"
        assert buttons[1][0].callback_data == "cancel"

    def test_create_pagination_menu_single_page(self):
        """Тест создания меню пагинации для одной страницы"""
        keyboard = KeyboardFormatter.create_pagination_menu(1, 1, "test")

        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Должна быть только информационная кнопка
        assert len(keyboard.inline_keyboard) == 1
        assert keyboard.inline_keyboard[0][0].text == "📄 1/1"

    def test_create_pagination_menu_multiple_pages(self):
        """Тест создания меню пагинации для нескольких страниц"""
        keyboard = KeyboardFormatter.create_pagination_menu(2, 5, "test")

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 2  # Навигация + информация

        # Проверяем навигационные кнопки
        nav_buttons = keyboard.inline_keyboard[0]
        assert nav_buttons[0].text == "⬅️"
        assert nav_buttons[0].callback_data == "test_prev"
        assert nav_buttons[1].text == "➡️"
        assert nav_buttons[1].callback_data == "test_next"

        # Проверяем информационную кнопку
        info_button = keyboard.inline_keyboard[1][0]
        assert info_button.text == "📄 2/5"
        assert info_button.callback_data == "test_info"

    def test_create_pagination_menu_first_page(self):
        """Тест создания меню пагинации для первой страницы"""
        keyboard = KeyboardFormatter.create_pagination_menu(1, 5, "test")

        assert isinstance(keyboard, InlineKeyboardMarkup)
        nav_buttons = keyboard.inline_keyboard[0]
        # Должна быть только кнопка "вперед"
        assert len(nav_buttons) == 1
        assert nav_buttons[0].text == "➡️"
        assert nav_buttons[0].callback_data == "test_next"

    def test_create_pagination_menu_last_page(self):
        """Тест создания меню пагинации для последней страницы"""
        keyboard = KeyboardFormatter.create_pagination_menu(5, 5, "test")

        assert isinstance(keyboard, InlineKeyboardMarkup)
        nav_buttons = keyboard.inline_keyboard[0]
        # Должна быть только кнопка "назад"
        assert len(nav_buttons) == 1
        assert nav_buttons[0].text == "⬅️"
        assert nav_buttons[0].callback_data == "test_prev"

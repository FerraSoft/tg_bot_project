import logging
import random
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, InlineQueryHandler, ChatMemberHandler
from database_sqlite import Database
from config import BOT_TOKEN, OPENWEATHER_API_KEY, NEWS_API_KEY

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
db = Database()

# Предопределенные ответы
PREDEFINED_RESPONSES = {
    'привет': 'Привет! Как дела?',
    'как дела': 'Отлично! А у тебя?',
    'что делаешь': 'Отвечаю на сообщения в чате 😊',
    'спасибо': 'Пожалуйста! Рад помочь!',
    'пока': 'До свидания! Заходи еще!',
}

# Текст справки
HELP_TEXT = """
🤖 <b>Команды бота:</b>

<b>Основные:</b>
/start - Начать работу с ботом
/help - Показать это сообщение
/info - Информация о вас

<b>Рейтинг:</b>
/rank - Ваш текущий рейтинг
/ranks_info - Информация о системе рангов
/leaderboard - Топ-10 участников

<b>Информация:</b>
/weather [город] - Погода в городе
/news - Последние новости
/translate [текст] [язык] - Перевод текста

<b>Прочее:</b>
Введите "реквизиты" - Получить реквизиты для оплаты

<b>Игры:</b>
/play_game - Запустить мини-игру

<b>Модерация (только для админов):</b>
/warn [пользователь] [причина] - Выдать предупреждение
/mute [пользователь] [время] - Заглушить пользователя
/unmute [пользователь] - Снять заглушку
/ban [пользователь] [причина] - Забанить пользователя
/unban [пользователь] - Разбанить пользователя
/kick [пользователь] [причина] - Кикнуть пользователя
/promote [пользователь] - Повысить до модератора
/demote [пользователь] - Понизить с модератора
"""

# Текст реквизитов
BANK_DETAILS_TEXT = "Денежные средства можно перечислить по номерам: \r\n💳 89066935474 Елена, \r\n💳89207144698 Людмила\r\nБольшая просьба не писать сообщения при переводе, карту могут заблокировать!!!"

class TelegramBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""

        # Команды
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("rank", self.rank))
        self.application.add_handler(CommandHandler("ranks_info", self.ranks_info))
        self.application.add_handler(CommandHandler("leaderboard", self.leaderboard))
        self.application.add_handler(CommandHandler("info", self.user_info))
        self.application.add_handler(CommandHandler("weather", self.weather))
        self.application.add_handler(CommandHandler("news", self.news))
        self.application.add_handler(CommandHandler("translate", self.translate))
        self.application.add_handler(CommandHandler("play_game", self.play_game))
        self.application.add_handler(CommandHandler("ban", self.ban_user))
        self.application.add_handler(CommandHandler("mute", self.mute_user))
        self.application.add_handler(CommandHandler("warn", self.warn_user))
        self.application.add_handler(CommandHandler("kick", self.kick_user))
        self.application.add_handler(CommandHandler("unmute", self.unmute_user))
        self.application.add_handler(CommandHandler("unban", self.unban_user))
        self.application.add_handler(CommandHandler("promote", self.promote_user))
        self.application.add_handler(CommandHandler("demote", self.demote_user))
        self.application.add_handler(CommandHandler("import_csv", self.import_csv))
        self.application.add_handler(CommandHandler("schedule_post", self.schedule_post))
        self.application.add_handler(CommandHandler("list_posts", self.list_posts))
        self.application.add_handler(CommandHandler("delete_post", self.delete_post))
        self.application.add_handler(CommandHandler("publish_now", self.publish_now))

        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(ChatMemberHandler(self.handle_new_chat_members, ChatMemberHandler.CHAT_MEMBER))

        # Инлайновые запросы
        self.application.add_handler(InlineQueryHandler(self.handle_inline_query))

        # Callback queries для игр
        from telegram.ext import CallbackQueryHandler
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name, user.last_name)

        keyboard = [
            [InlineKeyboardButton("📋 Помощь", callback_data='cmd_help')],
            [InlineKeyboardButton("🎮 Мини игры", callback_data='cmd_play_game')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = f"""
Привет, {user.first_name}! 👋

Я ваш помощник в чате. Вот что я умею:
• Отвечать на сообщения
• Вести рейтинг участников
• Предоставлять погоду и новости
• Играть в мини-игры
• Помогать с модерацией

Используйте /help для подробной информации.
        """

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        keyboard = [
            [InlineKeyboardButton("🚀 Старт", callback_data='cmd_start')],
            [InlineKeyboardButton("🔄 Начать заново", callback_data='cmd_restart')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        help_text = """
🤖 <b>Команды бота:</b>

<b>Основные:</b>
/start - Начать работу с ботом
/help - Показать это сообщение
/info - Информация о вас

<b>Рейтинг:</b>
/rank - Ваш текущий рейтинг
/ranks_info - Информация о системе рангов
/leaderboard - Топ-10 участников

<b>Информация:</b>
/weather [город] - Погода в городе
/news - Последние новости
/translate [текст] [язык] - Перевод текста

<b>Прочее:</b>
Введите "реквизиты" - Получить реквизиты для оплаты

<b>Игры:</b>
/play_game - Запустить мини-игру

<b>Посты по расписанию (только для админов):</b>
/schedule_post [время] [текст] - Запланировать пост
/list_posts - Показать запланированные посты
/delete_post [ID] - Удалить пост по расписанию
/publish_now [ID] - Опубликовать пост немедленно

<b>Посты по расписанию (только для админов):</b>
/schedule_post [время] [текст] - Запланировать пост
/list_posts - Показать запланированные посты
/delete_post [ID] - Удалить пост по расписанию
/publish_now [ID] - Опубликовать пост немедленно

<b>Модерация (только для админов):</b>
/warn [пользователь] [причина] - Выдать предупреждение
/mute [пользователь] [время] - Заглушить пользователя
/unmute [пользователь] - Снять заглушку
/ban [пользователь] [причина] - Забанить пользователя
/unban [пользователь] - Разбанить пользователя
/kick [пользователь] [причина] - Кикнуть пользователя
/promote [пользователь] - Повысить до модератора
/demote [пользователь] - Понизить с модератора
/import_csv [файл] - Импорт пользователей из CSV файла
        """

        await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=reply_markup)

    async def rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рейтинг пользователя"""
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name, user.last_name)
        user_info = db.get_user_info(user.id)

        if user_info:
            rank_text = f"""
🏆 <b>Ваш рейтинг:</b>

Очки: {user_info['Очки']}
Предупреждений: {user_info['Предупреждений']}
Роль: {user_info['Роль']}
            """
        else:
            rank_text = "Информация о вас не найдена."

        await update.message.reply_text(rank_text, parse_mode='HTML')

    async def leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать топ пользователей"""
        top_users = db.get_top_users(10)

        if top_users:
            leaderboard_text = "🏆 <b>Топ-10 участников:</b>\n\n"
            for i, (user_id, username, first_name, score) in enumerate(top_users, 1):
                name = username if username else first_name
                leaderboard_text += f"{i}. {name} - {score} очков\n"
        else:
            leaderboard_text = "Рейтинг пока пуст."

        await update.message.reply_text(leaderboard_text, parse_mode='HTML')

    async def user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о пользователе"""
        user = update.effective_user

        # Проверяем, является ли пользователь администратором
        is_admin = await self.is_admin(update.effective_chat, user.id)

        if len(context.args) > 0 and is_admin:
            # Администратор запрашивает информацию о другом пользователе
            target_user = context.args[0]
            try:
                target_user_id = int(target_user)
                user_info = db.get_user_info(target_user_id)
                if user_info:
                    info_text = f"""
👤 <b>Информация о пользователе:</b>

ID: {user_info['ID']}
Имя: {user_info['Имя']}
Имя пользователя: @{user_info['Имя пользователя']}
Репутация: {user_info['Репутация']}
Ранг: {user_info['Ранг']}
Количество сообщений: {user_info['Количество сообщений']}
Активные дни: {user_info['Активные дни']}
Дней с присоединения: {user_info['Дней с присоединения']}
Последнее сообщение: {user_info['Последнее сообщение'] or 'никогда'}
Присоединился: {user_info['Присоединился']}
Покинул: {user_info['Покинул'] or 'ещё здесь'}
Язык: {user_info['Язык']}
Действия: {user_info['Действия']}
Очки: {user_info['Очки']}
Предупреждений: {user_info['Предупреждений']}
Роль: {user_info['Роль']}
                    """
                else:
                    info_text = f"Пользователь с ID {target_user_id} не найден."
            except ValueError:
                info_text = f"Неверный формат ID пользователя: {target_user}"
        else:
            # Обычный пользователь запрашивает свою информацию
            db.add_user(user.id, user.username, user.first_name, user.last_name)
            user_info = db.get_user_info(user.id)

            if user_info:
                info_text = f"""
👤 <b>Информация о вас:</b>

ID: {user_info['ID']}
Имя: {user_info['Имя']}
Имя пользователя: @{user_info['Имя пользователя']}
Репутация: {user_info['Репутация']}
Ранг: {user_info['Ранг']}
Количество сообщений: {user_info['Количество сообщений']}
Активные дни: {user_info['Активные дни']}
Дней с присоединения: {user_info['Дней с присоединения']}
Последнее сообщение: {user_info['Последнее сообщение'] or 'никогда'}
Присоединился: {user_info['Присоединился']}
Покинул: {user_info['Покинул'] or 'ещё здесь'}
Язык: {user_info['Язык']}
Действия: {user_info['Действия']}
Очки: {user_info['Очки']}
Предупреждений: {user_info['Предупреждений']}
Роль: {user_info['Роль']}
                """
            else:
                info_text = "Информация не найдена."

        await update.message.reply_text(info_text, parse_mode='HTML')

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получить погоду"""
        if not OPENWEATHER_API_KEY:
            await update.message.reply_text("API ключ для погоды не настроен.")
            return

        city = ' '.join(context.args) if context.args else 'Moscow'

        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
            response = requests.get(url)
            data = response.json()

            if data['cod'] == 200:
                weather_text = f"""
🌤️ <b>Погода в {data['name']}:</b>

Температура: {data['main']['temp']}°C
Ощущается как: {data['main']['feels_like']}°C
Влажность: {data['main']['humidity']}%
Описание: {data['weather'][0]['description']}
                """
            else:
                weather_text = "Город не найден."

            await update.message.reply_text(weather_text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"Ошибка при получении погоды: {e}")

    async def news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получить новости"""
        if not NEWS_API_KEY:
            await update.message.reply_text("API ключ для новостей не настроен.")
            return

        try:
            url = f"https://newsapi.org/v2/top-headlines?country=ru&apiKey={NEWS_API_KEY}"
            response = requests.get(url)
            data = response.json()

            if data['status'] == 'ok' and data['articles']:
                news_text = "📰 <b>Последние новости:</b>\n\n"
                for i, article in enumerate(data['articles'][:5], 1):
                    news_text += f"{i}. {article['title']}\n{article['url']}\n\n"
            else:
                news_text = "Новости не найдены."

            await update.message.reply_text(news_text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"Ошибка при получении новостей: {e}")

    async def translate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевод текста"""
        if len(context.args) < 2:
            await update.message.reply_text("Использование: /translate [текст] [язык] (например: /translate hello en)")
            return

        text = ' '.join(context.args[:-1])
        target_lang = context.args[-1]

        # Простой перевод с помощью Google Translate API (нужен API ключ)
        try:
            # В реальном проекте используйте Google Translate API или другой сервис
            await update.message.reply_text(f"Перевод '{text}' на {target_lang}: [здесь будет перевод]")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при переводе: {e}")

    async def play_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запустить мини-игру"""
        keyboard = [
            [InlineKeyboardButton("Камень-ножницы-бумага", callback_data='game_rps')],
            [InlineKeyboardButton("Крестики-нолики", callback_data='game_tic_tac_toe')],
            [InlineKeyboardButton("Викторина", callback_data='game_quiz')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("🎮 Выберите игру:", reply_markup=reply_markup)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback запросов от инлайновых кнопок"""
        query = update.callback_query
        await query.answer()

        if query.data == 'cmd_start' or query.data == 'cmd_restart':
            await self.show_start_menu(query)
        elif query.data == 'cmd_help':
            await self.show_help_menu(query)
        elif query.data == 'cmd_play_game':
            await self.show_games_menu(query)
        elif query.data == 'game_rps':
            await self.start_rps_game(query, context)
        elif query.data == 'game_tic_tac_toe':
            await self.start_tic_tac_toe_game(query, context)
        elif query.data == 'game_quiz':
            await self.start_quiz_game(query, context)
        elif query.data.startswith('rps_'):
            await self.handle_rps(query, context)
        elif query.data.startswith('tictactoe_'):
            await self.handle_tic_tac_toe_move(query, context)
        elif query.data.startswith('quiz_'):
            await self.handle_quiz_answer(query, context)


    async def start_rps_game(self, query, context):
        """Запуск игры 'Камень-ножницы-бумага'"""
        keyboard = [
            [InlineKeyboardButton("🪨 Камень", callback_data='rps_rock')],
            [InlineKeyboardButton("📄 Бумага", callback_data='rps_paper')],
            [InlineKeyboardButton("✂️ Ножницы", callback_data='rps_scissors')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("🤖 Камень, ножницы, бумага!\n\nВыберите ваш ход:", reply_markup=reply_markup)

    async def start_tic_tac_toe_game(self, query, context):
        """Запуск игры 'Крестики-нолики'"""
        board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]
        context.user_data['tictactoe_board'] = board
        context.user_data['tictactoe_turn'] = 'user'

        keyboard = self.create_tic_tac_toe_keyboard(board)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("❌⭕ Крестики-нолики!\n\nВы ходите первым. Выберите клетку:", reply_markup=reply_markup)

    async def handle_tic_tac_toe_move(self, query, context):
        """Обработка ходов в игре Крестики-нолики"""
        move_data = query.data.split('_')[1]
        if move_data == 'restart':
            await self.start_tic_tac_toe_game(query, context)
            return

        if len(move_data) != 2:
            await query.answer("Неверный формат хода!")
            return

        row, col = map(int, move_data)

        board = context.user_data.get('tictactoe_board')
        turn = context.user_data.get('tictactoe_turn')

        if not board or not (0 <= row < 3 and 0 <= col < 3) or board[row][col] != ' ' or turn != 'user':
            await query.answer("Неверный ход!")
            return

        # Ход пользователя
        board[row][col] = 'X'

        if self.check_winner(board, 'X'):
            await query.edit_message_text("🎉 Вы выиграли! 🏆")
            db.update_score(query.from_user.id, 15)
            db.update_reputation(query.from_user.id, 15)
            rank_update = db.update_rank(query.from_user.id, query.message.chat.id, query.from_user.first_name)
            if rank_update and rank_update.get("promoted"):
                await query.message.chat.send_message(
                    f"🌟 За активное участие в группе {rank_update['name']} получил(-а) новое звание {rank_update['new_rank']}!"
                )
            # Показать финальное поле с кнопками
            keyboard = self.create_tic_tac_toe_keyboard(board, game_over=True)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("🎉 Вы выиграли! 🏆", reply_markup=reply_markup)
            context.user_data.pop('tictactoe_board', None)
            context.user_data.pop('tictactoe_turn', None)
            return

        if self.is_board_full(board):
            keyboard = self.create_tic_tac_toe_keyboard(board, game_over=True)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("🤝 Ничья!", reply_markup=reply_markup)
            return

        # Ход бота
        bot_row, bot_col = self.get_bot_move(board)
        board[bot_row][bot_col] = 'O'

        if self.check_winner(board, 'O'):
            keyboard = self.create_tic_tac_toe_keyboard(board, game_over=True)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("😞 Вы проиграли. Бот победил!", reply_markup=reply_markup)
            return

        if self.is_board_full(board):
            await query.edit_message_text("🤝 Ничья!")
            return

        keyboard = self.create_tic_tac_toe_keyboard(board)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌⭕ Крестики-нолики!\n\nВаш ход. Выберите клетку:", reply_markup=reply_markup)

    def create_tic_tac_toe_keyboard(self, board, game_over=False):
        """Создание клавиатуры для игры"""
        keyboard = []
        for i in range(3):
            row = []
            for j in range(3):
                symbol = board[i][j]
                if symbol == 'X':
                    text = '❌'
                elif symbol == 'O':
                    text = '⭕'
                else:
                    text = ' '
                if game_over:
                    # Пустая callback_data для завершенной игры
                    row.append(InlineKeyboardButton(text, callback_data='game_over'))
                else:
                    row.append(InlineKeyboardButton(text, callback_data=f'tictactoe_{i}{j}'))
            keyboard.append(row)

        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("🔄 Новая игра", callback_data='tictactoe_restart'),
            InlineKeyboardButton("⬅️ Назад к играм", callback_data='cmd_play_game')
        ])
        return keyboard

    def check_winner(self, board, player):
        """Проверка победителя"""
        for row in board:
            if all(cell == player for cell in row):
                return True
        for col in range(3):
            if all(row[col] == player for row in board):
                return True
        if all(board[i][i] == player for i in range(3)) or all(board[i][2-i] == player for i in range(3)):
            return True
        return False

    def is_board_full(self, board):
        """Проверка, заполнена ли доска"""
        return all(cell != ' ' for row in board for cell in row)

    def get_bot_move(self, board):
        """Получение хода бота (простая логика)"""
        # Сначала проверяем, можем ли выиграть
        for i in range(3):
            for j in range(3):
                if board[i][j] == ' ':
                    board[i][j] = 'O'
                    if self.check_winner(board, 'O'):
                        board[i][j] = ' '
                        return i, j
                    board[i][j] = ' '

        # Блокируем ход пользователя
        for i in range(3):
            for j in range(3):
                if board[i][j] == ' ':
                    board[i][j] = 'X'
                    if self.check_winner(board, 'X'):
                        board[i][j] = ' '
                        return i, j
                    board[i][j] = ' '

        # Случайный ход
        import random
        while True:
            i, j = random.randint(0, 2), random.randint(0, 2)
            if board[i][j] == ' ':
                return i, j

    async def handle_rps(self, query, context):
        """Обработка ходов в игре КНБ"""
        user_choice = query.data.split('_')[1]
        bot_choice = random.choice(['rock', 'paper', 'scissors'])

        choices = {'rock': '🪨 Камень', 'paper': '📄 Бумага', 'scissors': '✂️ Ножницы'}

        result = self.determine_rps_winner(user_choice, bot_choice)

        if result == 'win':
            message = f"🎉 Вы выиграли!\n\nВаш выбор: {choices[user_choice]}\nМой выбор: {choices[bot_choice]}"
            db.update_score(query.from_user.id, 5)
            db.update_reputation(query.from_user.id, 5)
            db.update_reputation(query.from_user.id, 5)
        elif result == 'lose':
            message = f"😞 Вы проиграли!\n\nВаш выбор: {choices[user_choice]}\nМой выбор: {choices[bot_choice]}"
        else:
            message = f"🤝 Ничья!\n\nВаш выбор: {choices[user_choice]}\nМой выбор: {choices[bot_choice]}"

        keyboard = [
            [InlineKeyboardButton("🔄 Новая игра", callback_data='game_rps')],
            [InlineKeyboardButton("⬅️ Назад к играм", callback_data='cmd_play_game')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    def determine_rps_winner(self, user, bot):
        """Определение победителя в КНБ"""
        if user == bot:
            return 'draw'
        elif (user == 'rock' and bot == 'scissors') or \
             (user == 'paper' and bot == 'rock') or \
             (user == 'scissors' and bot == 'paper'):
            return 'win'
        else:
            return 'lose'

    async def start_quiz_game(self, query, context):
        """Запуск викторины"""
        questions = [
            {"question": "Столица Франции?", "answers": ["Париж", "Лондон", "Берлин"], "correct": 0},
            {"question": "2 + 2 = ?", "answers": ["3", "4", "5"], "correct": 1},
            {"question": "Цвет неба?", "answers": ["Зеленый", "Синий", "Красный"], "correct": 1},
            {"question": "Сколько планет в Солнечной системе?", "answers": ["8", "9", "10"], "correct": 0},
            {"question": "Какой язык программирования мы используем?", "answers": ["JavaScript", "Python", "Java"], "correct": 1}
        ]

        question = random.choice(questions)
        context.user_data['quiz_correct'] = question['correct']
        context.user_data['quiz_question'] = question

        keyboard = []
        for i, answer in enumerate(question['answers']):
            keyboard.append([InlineKeyboardButton(answer, callback_data=f'quiz_{i}')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"🧠 Викторина:\n\n{question['question']}", reply_markup=reply_markup)

    async def handle_quiz_answer(self, query, context):
        """Обработка ответа на вопрос викторины"""
        answer_index = int(query.data.split('_')[1])
        correct_index = context.user_data.get('quiz_correct')

        if correct_index is None:
            await query.edit_message_text("Вопрос викторины не найден.")
            return

        question = context.user_data.get('quiz_question', {})

        if answer_index == correct_index:
            keyboard = [
                [InlineKeyboardButton("🔄 Новая игра", callback_data='game_quiz')],
                [InlineKeyboardButton("⬅️ Назад к играм", callback_data='cmd_play_game')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"🎉 Правильно! Вы заработали 5 очков!\n\nВопрос: {question.get('question', '')}\nОтвет: {question.get('answers', [])[correct_index]}", reply_markup=reply_markup)
            db.update_score(query.from_user.id, 5)
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 Новая игра", callback_data='game_quiz')],
                [InlineKeyboardButton("⬅️ Назад к играм", callback_data='cmd_play_game')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            correct_answer = question.get('answers', [])[correct_index] if correct_index < len(question.get('answers', [])) else "неизвестен"
            await query.edit_message_text(f"❌ Неправильно!\n\nВопрос: {question.get('question', '')}\nПравильный ответ: {correct_answer}", reply_markup=reply_markup)

        # Очистка данных викторины
        context.user_data.pop('quiz_correct', None)
        context.user_data.pop('quiz_question', None)

    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Забанить пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("Использование: /ban [пользователь] [причина]")
            return

        user_id = context.args[0]
        reason = ' '.join(context.args[1:])

        try:
            await update.effective_chat.ban_member(int(user_id))
            await update.message.reply_text(f"🚫 Пользователь {user_id} забанен.\nПричина: {reason}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при бане пользователя: {e}")

    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разбанить пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        if len(context.args) < 1:
            await update.message.reply_text("Использование: /unban [пользователь]")
            return

        user_id = context.args[0]

        try:
            await update.effective_chat.unban_member(int(user_id))
            await update.message.reply_text(f"✅ Пользователь {user_id} разбанен.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при разбане пользователя: {e}")

    async def mute_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Заглушить пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("Использование: /mute [пользователь] [время_в_секундах]")
            return

        user_id = context.args[0]
        try:
            mute_time = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ Время должно быть числом в секундах.")
            return

        from datetime import datetime, timedelta
        until_date = datetime.now() + timedelta(seconds=mute_time)

        try:
            await update.effective_chat.restrict_member(
                int(user_id),
                until_date=until_date,
                can_send_messages=False
            )
            await update.message.reply_text(f"🔇 Пользователь {user_id} заглушен на {mute_time} секунд.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при mute пользователя: {e}")

    async def unmute_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять заглушку с пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        if len(context.args) < 1:
            await update.message.reply_text("Использование: /unmute [пользователь]")
            return

        user_id = context.args[0]

        try:
            await update.effective_chat.restrict_member(
                int(user_id),
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
            await update.message.reply_text(f"🔊 Заглушка с пользователя {user_id} снята.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при unmute пользователя: {e}")

    async def kick_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кикнуть пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("Использование: /kick [пользователь] [причина]")
            return

        user_id = context.args[0]
        reason = ' '.join(context.args[1:])

        try:
            await update.effective_chat.ban_member(int(user_id))
            await update.effective_chat.unban_member(int(user_id))  # Разбан сразу после бана = кик
            await update.message.reply_text(f"👢 Пользователь {user_id} кикнут.\nПричина: {reason}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при кике пользователя: {e}")

    async def promote_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Повысить пользователя до модератора (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            #return

        if len(context.args) < 1:
            await update.message.reply_text("Использование: /promote [пользователь]")
            return

        user_id = context.args[0]

        try:
            await update.effective_chat.promote_member(
                int(user_id),
                can_delete_messages=True,
                can_restrict_members=True,
                can_invite_users=True
            )
            await update.message.reply_text(f"⬆️ Пользователь {user_id} повышен до модератора.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при повышении пользователя: {e}")

    async def demote_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Понизить пользователя с модератора (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        if len(context.args) < 1:
            await update.message.reply_text("Использование: /demote [пользователь]")
            return

        user_id = context.args[0]

        try:
            await update.effective_chat.promote_member(
                int(user_id),
                can_delete_messages=False,
                can_restrict_members=False,
                can_invite_users=False,
                can_pin_messages=False
            )
            await update.message.reply_text(f"⬇️ Пользователь {user_id} понижен с модератора.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при понижении пользователя: {e}")

    async def warn_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать предупреждение пользователю (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("Использование: /warn [пользователь] [причина]")
            return

        user_id = context.args[0]
        reason = ' '.join(context.args[1:])

        db.add_warning(user_id, reason, update.effective_user.id)
        await update.message.reply_text(f"⚠️ Предупреждение выдано пользователю {user_id} по причине: {reason}")

    async def ranks_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о системе рангов"""
        ranks_text = """
        🏆 <b>Военная система рангов</b>

        <b>Как работает система:</b>
        • Каждый участник начинает с звания "Рядовой"
        • Звание повышается автоматически при достижении определенного количества очков
        • Очки начисляются за активность в чате и победы в играх

        <b>Иерархия званий:</b>
        🪖 Рядовой (0 очков)
        🪖 Ефрейтор (100 очков)
        🪖 Младший сержант (235 очков)
        🪖 Сержант (505 очков)
        🪖 Старший сержант (810 очков)
        🪖 Старшина (1,250 очков)
        🪖 Прапорщик (1,725 очков)
        🪖 Старший прапорщик (2,335 очков)
        🪖 Младший лейтенант (2,980 очков)
        🪖 Лейтенант (3,760 очков)
        🪖 Старший лейтенант (4,575 очков)
        🪖 Капитан (5,525 очков)
        🪖 Майор (6,510 очков)
        🪖 Подполковник (7,630 очков)
        🪖 Полковник (8,785 очков)
        🪖 Генерал майор (16,075 очков)
        🪖 Генерал лейтенант (32,150 очков)
        🪖 Генерал полковник (64,300 очков)
        🪖 Генерал армии (128,600 очков)
        🪖 Маршал (256,000 очков)

        <b>Как получить очки:</b>
        • +1 очко за каждое сообщение в чате
        • +5 очков за победу в мини-игре
        • +15 очков за победу в крестиках-ноликах
        • Бонусные очки за активность (случайно 1-5 очков)

        <b>Команды для работы с рангом:</b>
        /rank - Показать ваш текущий ранг и очки
        /leaderboard - Топ-10 участников по очкам
        /info - Детальная информация о вашем профиле

        Служите чату верой и правдой, чтобы достичь высших воинских званий! 🎖️
        """

        await update.message.reply_text(ranks_text, parse_mode='HTML')

    async def import_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Импорт пользователей из CSV файла (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        if len(context.args) < 1:
            await update.message.reply_text("Использование: /import_csv [путь_к_файлу]\n\nПо умолчанию: /import_csv chat_-1001519866478_users_full_20251014.csv")
            return

        csv_file = context.args[0] if context.args else 'chat_-1001519866478_users_full_20251014.csv'

        # Если путь относительный, добавляем путь к директории telegram_bot
        if not os.path.isabs(csv_file):
            csv_file = os.path.join('telegram_bot', csv_file)

        await update.message.reply_text(f"🔄 Начинаю импорт пользователей из файла: {csv_file}")

        try:
            success = db.import_users_from_csv(csv_file)

            if success:
                await update.message.reply_text("✅ Импорт пользователей успешно завершен!")
            else:
                await update.message.reply_text("❌ Произошла ошибка при импорте пользователей.")

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при импорте: {str(e)}")

    async def schedule_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запланировать пост для публикации"""
        user = update.effective_user

        # Проверка прав администратора
        if not await self.is_admin(update.effective_chat, user.id):
            await update.message.reply_text("❌ У вас нет прав для планирования постов.")
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "Использование: /schedule_post [время] [текст поста]\n\n"
                "Формат времени:\n"
                "• Абсолютное: 2024-01-15 14:30:00\n"
                "• Относительное: +30m (через 30 минут), +2h (через 2 часа), +1d (через день)\n\n"
                "Пример: /schedule_post +2h Привет всем!"
            )
            return

        # Парсинг времени и текста
        time_str = context.args[0]
        text = ' '.join(context.args[1:])

        try:
            schedule_time = self.parse_schedule_time(time_str)
        except ValueError as e:
            await update.message.reply_text(f"❌ Ошибка формата времени: {str(e)}")
            return

        if schedule_time <= datetime.now():
            await update.message.reply_text("❌ Время публикации должно быть в будущем!")
            return

        # Добавление поста в базу данных
        post_id = db.add_scheduled_post(
            chat_id=update.effective_chat.id,
            text=text,
            schedule_time=schedule_time.strftime('%Y-%m-%d %H:%M:%S'),
            created_by=user.id
        )

        if post_id:
            await update.message.reply_text(
                f"✅ Пост запланирован!\n\n"
                f"📅 Время публикации: {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📝 Текст: {text[:50]}{'...' if len(text) > 50 else ''}\n"
                f"🆔 ID поста: {post_id}"
            )
        else:
            await update.message.reply_text("❌ Ошибка при сохранении поста в базу данных.")

    async def list_posts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список запланированных постов"""
        user = update.effective_user

        # Проверка прав администратора
        if not await self.is_admin(update.effective_chat, user.id):
            await update.message.reply_text("❌ У вас нет прав для просмотра постов.")
            return

        posts = db.get_scheduled_posts(chat_id=update.effective_chat.id)

        if not posts:
            await update.message.reply_text("📭 Нет запланированных постов.")
            return

        response = "📋 <b>Запланированные посты:</b>\n\n"
        for post in posts:
            post_id, chat_id, text, image_path, schedule_time, created_by, status, published_at, created_at, creator_name = post

            response += f"🆔 <b>{post_id}</b>\n"
            response += f"📅 {schedule_time}\n"
            response += f"👤 Создал: {creator_name or 'Неизвестен'}\n"
            response += f"📝 {text[:100]}{'...' if len(text) > 100 else ''}\n"
            if image_path:
                response += f"🖼 Изображение: {image_path}\n"
            response += "\n" + "─" * 30 + "\n"

        await update.message.reply_text(response, parse_mode='HTML')

    async def delete_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить запланированный пост"""
        user = update.effective_user

        # Проверка прав администратора
        if not await self.is_admin(update.effective_chat, user.id):
            await update.message.reply_text("❌ У вас нет прав для удаления постов.")
            return

        if len(context.args) < 1:
            await update.message.reply_text("Использование: /delete_post [ID поста]")
            return

        try:
            post_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID поста должен быть числом.")
            return

        success = db.delete_scheduled_post(post_id, user.id)

        if success:
            await update.message.reply_text(f"✅ Пост {post_id} удален.")
        else:
            await update.message.reply_text(f"❌ Пост {post_id} не найден или у вас нет прав для его удаления.")

    async def publish_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Опубликовать пост немедленно"""
        user = update.effective_user

        # Проверка прав администратора
        if not await self.is_admin(update.effective_chat, user.id):
            await update.message.reply_text("❌ У вас нет прав для публикации постов.")
            return

        if len(context.args) < 1:
            await update.message.reply_text("Использование: /publish_now [ID поста]")
            return

        try:
            post_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID поста должен быть числом.")
            return

        # Получаем пост из базы данных
        posts = db.get_scheduled_posts()
        post = None
        for p in posts:
            if p[0] == post_id:  # p[0] is post_id
                post = p
                break

        if not post:
            await update.message.reply_text(f"❌ Пост {post_id} не найден.")
            return

        post_id, chat_id, text, image_path, schedule_time, created_by, status, published_at, created_at, creator_name = post

        try:
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    await update.effective_chat.send_photo(photo, caption=text)
            else:
                await update.effective_chat.send_message(text)

            # Отмечаем пост как опубликованный
            db.mark_post_published(post_id)

            await update.message.reply_text(f"✅ Пост {post_id} опубликован немедленно!")

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при публикации поста: {str(e)}")

    def parse_schedule_time(self, time_str):
        """Парсинг времени публикации из строки"""
        from datetime import datetime, timedelta
        import re

        current_time = datetime.now()

        # Абсолютное время: 2024-01-15 14:30:00 или 2024-01-15 14:30
        absolute_pattern = r'^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?$'
        match = re.match(absolute_pattern, time_str)

        if match:
            year, month, day, hour, minute = map(int, match.groups()[:5])
            second = int(match.group(6)) if match.group(6) else 0
            return datetime(year, month, day, hour, minute, second)

        # Относительное время: +30m, +2h, +1d
        relative_pattern = r'^(\+|\-)(\d+)([mhd])$'
        match = re.match(relative_pattern, time_str)

        if match:
            sign, amount, unit = match.groups()
            amount = int(amount)

            if unit == 'm':  # минуты
                delta = timedelta(minutes=amount)
            elif unit == 'h':  # часы
                delta = timedelta(hours=amount)
            elif unit == 'd':  # дни
                delta = timedelta(days=amount)

            if sign == '-':
                delta = -delta

            return current_time + delta

        raise ValueError("Неверный формат времени. Используйте абсолютное время (2024-01-15 14:30) или относительное (+30m, +2h, +1d)")

    async def is_admin(self, chat, user_id):
        """Проверка, является ли пользователь администратором"""
        try:
            member = await chat.get_member(user_id)
            return member.status in ['administrator', 'creator']
        except:
            return False

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        message_text = update.message.text.lower()

        # Добавление пользователя в базу данных
        db.add_user(user.id, user.username, user.first_name, user.last_name)

        # Начисление очков за сообщение и обновление статистики
        db.update_score(user.id)
        # Обновление репутации за активность
        db.update_reputation(user.id, 1)
        # Проверка на повышение ранга
        rank_update = db.update_rank(user.id, update.effective_chat.id, user.first_name)
        if rank_update and rank_update.get("promoted"):
            await update.effective_chat.send_message(
                f"🌟 За активное участие в группе {rank_update['name']} получил(-а) новое звание {rank_update['new_rank']}!"
            )

        # Проверка на слова "реквизиты"
        if "реквизиты" in message_text or "реквизит" in message_text:
            await update.message.reply_text(BANK_DETAILS_TEXT, reply_to_message_id=update.message.message_id)
            return

        # Предопределенные ответы
        response_found = False
        for key, response in PREDEFINED_RESPONSES.items():
            if key in message_text:
                await update.message.reply_text(response)
                response_found = True
                break

        if not response_found:
            # Если нет предопределенного ответа, показываем сообщение и help
            keyboard = [
                [InlineKeyboardButton("📋 Помощь", callback_data='cmd_help')],
                [InlineKeyboardButton("🎮 Мини игры", callback_data='cmd_play_game')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "🤖 Извините, я не понял ваше сообщение. Вот что я умею:\n\n"
                "• Отвечать на простые вопросы\n"
                "• Вести рейтинг участников\n"
                "• Предоставлять погоду и новости\n"
                "• Играть в мини-игры\n"
                "• Помогать с модерацией\n\n"
                "Используйте /help для подробной информации.",
                reply_markup=reply_markup
            )
            return

        # Случайное начисление очков от 1 до 5 вместо случайных ответов
        if random.random() < 0.1:  # 10% шанс
            bonus_points = random.randint(1, 5)
            db.update_score(user.id, bonus_points)
            await update.message.reply_text(f"🎁 Бонус! Вам начислено {bonus_points} очков!")

    async def handle_new_chat_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка новых участников чата"""
        for member in update.chat_member.new_chat_members:
            db.add_user(member.id, member.username, member.first_name, member.last_name)

            welcome_text = f"""
🎉 Добро пожаловать в чат, {member.first_name}! 

Мы рады видеть вас здесь! Используйте /help чтобы узнать о возможностях бота.
            """

            await update.effective_chat.send_message(welcome_text)

    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка инлайновых запросов"""
        query = update.inline_query.query

        results = []

        try:
            if query.startswith('weather'):
                city = query.split(' ', 1)[1] if len(query.split(' ', 1)) > 1 else 'Moscow'

                if OPENWEATHER_API_KEY:
                    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
                    response = requests.get(url)
                    data = response.json()

                    if data['cod'] == 200:
                        weather_text = f"🌤️ Погода в {data['name']}:\nТемпература: {data['main']['temp']}°C\nОщущается как: {data['main']['feels_like']}°C\nВлажность: {data['main']['humidity']}%\nОписание: {data['weather'][0]['description']}"
                        results.append(InlineQueryResultArticle(
                            id='1',
                            title=f"Погода в {city}",
                            input_message_content=InputTextMessageContent(weather_text)
                        ))
                    else:
                        results.append(InlineQueryResultArticle(
                            id='1',
                            title="Город не найден",
                            input_message_content=InputTextMessageContent("Город не найден")
                        ))

            elif query.startswith('translate'):
                # Базовая заглушка для перевода
                text_parts = query.split(' ', 2)
                if len(text_parts) >= 3:
                    text = text_parts[1]
                    lang = text_parts[2]
                    result_text = f"Перевод '{text}' на {lang}: [здесь будет перевод]"
                    results.append(InlineQueryResultArticle(
                        id='1',
                        title=f"Перевод на {lang}",
                        input_message_content=InputTextMessageContent(result_text)
                    ))

            await update.inline_query.answer(results)

        except Exception as e:
            print(f"Ошибка при обработке инлайнового запроса: {e}")

    async def show_start_menu(self, query):
        """Показать стартовое меню"""
        keyboard = [
            [InlineKeyboardButton("📋 Помощь", callback_data='cmd_help')],
            [InlineKeyboardButton("🎮 Мини игры", callback_data='cmd_play_game')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = f"""
Привет, {query.from_user.first_name}! 👋

Я ваш помощник в чате. Вот что я умею:
• Отвечать на сообщения
• Вести рейтинг участников
• Предоставлять погоду и новости
• Играть в мини-игры
• Помогать с модерацией

Используйте /help для подробной информации.
        """

        await query.edit_message_text(welcome_text, reply_markup=reply_markup)

    async def show_help_menu(self, query):
        """Показать меню помощи"""
        keyboard = [
            [InlineKeyboardButton("🚀 Старт", callback_data='cmd_start')],
            [InlineKeyboardButton("🔄 Начать заново", callback_data='cmd_restart')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        help_text = HELP_TEXT

        await query.edit_message_text(help_text, parse_mode='HTML', reply_markup=reply_markup)

    async def show_games_menu(self, query):
        """Показать меню выбора игр"""
        keyboard = [
            [InlineKeyboardButton("Камень-ножницы-бумага", callback_data='game_rps')],
            [InlineKeyboardButton("Крестики-нолики", callback_data='game_tic_tac_toe')],
            [InlineKeyboardButton("Викторина", callback_data='game_quiz')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("🎮 Выберите игру:", reply_markup=reply_markup)

    def run(self):
        """Запуск бота"""
        print("Bot started!")
        self.application.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()
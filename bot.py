import logging
import random
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, InlineQueryHandler, ChatMemberHandler
from database_sqlite import Database
from config_local import BOT_TOKEN, OPENWEATHER_API_KEY, NEWS_API_KEY
from messages import *

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
db = Database()

# Все текстовые сообщения теперь хранятся в отдельном файле messages.py

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

        welcome_text = USER_MESSAGES['welcome'].format(name=user.first_name)

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        keyboard = [
            [InlineKeyboardButton("🚀 Старт", callback_data='cmd_start')],
            [InlineKeyboardButton("🔄 Начать заново", callback_data='cmd_restart')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(HELP_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    async def rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рейтинг пользователя"""
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name, user.last_name)
        user_info = db.get_user_info(user.id)

        if user_info:
            rank_text = RANK_MESSAGES['rank_title'].format(
                score=user_info['Очки'],
                warnings=user_info['Предупреждений'],
                role=user_info['Роль']
            )
        else:
            rank_text = RANK_MESSAGES['rank_not_found']

        await update.message.reply_text(rank_text, parse_mode='HTML')

    async def leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать топ пользователей"""
        top_users = db.get_top_users(100)

        if top_users:
            leaderboard_text = RANK_MESSAGES['leaderboard_title']
            for i, (user_id, username, first_name, score) in enumerate(top_users, 1):
                name = username if username else first_name
                leaderboard_text += RANK_MESSAGES['leaderboard_entry'].format(
                    position=i, name=name, score=score
                )
        else:
            leaderboard_text = RANK_MESSAGES['leaderboard_empty']

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
                info_text = USER_MESSAGES['info_not_found']

        await update.message.reply_text(info_text, parse_mode='HTML')

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получить погоду"""
        if not OPENWEATHER_API_KEY:
            await update.message.reply_text(WEATHER_MESSAGES['no_api_key'])
            return

        city = ' '.join(context.args) if context.args else 'Moscow'

        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
            response = requests.get(url)
            data = response.json()

            if data['cod'] == 200:
                weather_text = WEATHER_MESSAGES['weather_info'].format(
                    city=data['name'],
                    temp=data['main']['temp'],
                    feels_like=data['main']['feels_like'],
                    humidity=data['main']['humidity'],
                    description=data['weather'][0]['description']
                )
            else:
                weather_text = WEATHER_MESSAGES['city_not_found']

            await update.message.reply_text(weather_text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(WEATHER_MESSAGES['weather_error'].format(error=e))

    async def news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получить новости"""
        if not NEWS_API_KEY:
            await update.message.reply_text(NEWS_MESSAGES['no_api_key'])
            return

        try:
            url = f"https://newsapi.org/v2/top-headlines?country=ru&apiKey={NEWS_API_KEY}"
            response = requests.get(url)
            data = response.json()

            if data['status'] == 'ok' and data['articles']:
                news_text = NEWS_MESSAGES['news_title']
                for i, article in enumerate(data['articles'][:5], 1):
                    news_text += f"{i}. {article['title']}\n{article['url']}\n\n"
            else:
                news_text = NEWS_MESSAGES['news_not_found']

            await update.message.reply_text(news_text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(NEWS_MESSAGES['news_error'].format(error=e))

    async def translate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевод текста"""
        if len(context.args) < 2:
            await update.message.reply_text(TRANSLATE_MESSAGES['usage'])
            return

        text = ' '.join(context.args[:-1])
        target_lang = context.args[-1]

        # Простой перевод с помощью Google Translate API (нужен API ключ)
        try:
            # В реальном проекте используйте Google Translate API или другой сервис
            await update.message.reply_text(TRANSLATE_MESSAGES['result'].format(text=text, lang=target_lang))
        except Exception as e:
            await update.message.reply_text(TRANSLATE_MESSAGES['error'].format(error=e))

    async def play_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запустить мини-игру"""
        keyboard = [
            [InlineKeyboardButton("Камень-ножницы-бумага", callback_data='game_rps')],
            [InlineKeyboardButton("Крестики-нолики", callback_data='game_tic_tac_toe')],
            [InlineKeyboardButton("Викторина", callback_data='game_quiz')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        keyboard = [
            [InlineKeyboardButton("Камень-ножницы-бумага", callback_data='game_rps')],
            [InlineKeyboardButton("Крестики-нолики", callback_data='game_tic_tac_toe')],
            [InlineKeyboardButton("Викторина", callback_data='game_quiz')],
            [InlineKeyboardButton("Морской бой", callback_data='game_battleship')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(GAME_MESSAGES['select_game'], reply_markup=reply_markup)

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
        elif query.data == 'game_battleship':
            await self.start_battleship_game(query, context)
        elif query.data.startswith('bs_'):
            await self.handle_battleship_shot(query, context)
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

        await query.edit_message_text(GAME_MESSAGES['rps_game'], reply_markup=reply_markup)

    async def start_tic_tac_toe_game(self, query, context):
        """Запуск игры 'Крестики-нолики'"""
        board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]
        context.user_data['tictactoe_board'] = board
        context.user_data['tictactoe_turn'] = 'user'

        keyboard = self.create_tic_tac_toe_keyboard(board)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(GAME_MESSAGES['tic_tac_toe_game'], reply_markup=reply_markup)

    async def handle_tic_tac_toe_move(self, query, context):
        """Обработка ходов в игре Крестики-нолики"""
        move_data = query.data.split('_')[1]
        if move_data == 'restart':
            await self.start_tic_tac_toe_game(query, context)
            return

        if len(move_data) != 2:
            await query.answer(GAME_MESSAGES['invalid_move'])
            return

        row, col = map(int, move_data)

        board = context.user_data.get('tictactoe_board')
        turn = context.user_data.get('tictactoe_turn')

        if not board or not (0 <= row < 3 and 0 <= col < 3) or board[row][col] != ' ' or turn != 'user':
            await query.answer(GAME_MESSAGES['invalid_move'])
            return

        # Ход пользователя
        board[row][col] = 'X'

        if self.check_winner(board, 'X'):
            await query.edit_message_text(GAME_MESSAGES['tic_tac_toe_win'])
            db.update_score(query.from_user.id, SCORE_VALUES['tic_tac_toe_win'])
            db.update_reputation(query.from_user.id, SCORE_VALUES['reputation_per_message'])
            rank_update = db.update_rank(query.from_user.id, query.message.chat.id, query.from_user.first_name)
            if rank_update and rank_update.get("promoted"):
                await query.message.chat.send_message(
                    RANK_MESSAGES['promotion_message'].format(
                        name=rank_update['name'],
                        new_rank=rank_update['new_rank']
                    )
                )
            # Показать финальное поле с кнопками
            keyboard = self.create_tic_tac_toe_keyboard(board, game_over=True)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(GAME_MESSAGES['tic_tac_toe_win'], reply_markup=reply_markup)
            context.user_data.pop('tictactoe_board', None)
            context.user_data.pop('tictactoe_turn', None)
            return

        if self.is_board_full(board):
            keyboard = self.create_tic_tac_toe_keyboard(board, game_over=True)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(GAME_MESSAGES['tic_tac_toe_draw'], reply_markup=reply_markup)
            return

        # Ход бота
        bot_row, bot_col = self.get_bot_move(board)
        board[bot_row][bot_col] = 'O'

        if self.check_winner(board, 'O'):
            keyboard = self.create_tic_tac_toe_keyboard(board, game_over=True)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(GAME_MESSAGES['tic_tac_toe_lose'], reply_markup=reply_markup)
            return
            return

        if self.is_board_full(board):
            await query.edit_message_text(GAME_MESSAGES['tic_tac_toe_draw'], reply_markup=reply_markup)
            return

        keyboard = self.create_tic_tac_toe_keyboard(board)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(GAME_MESSAGES['tic_tac_toe_game'], reply_markup=reply_markup)

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
            message = GAME_MESSAGES['rps_win'].format(
                user_choice=choices[user_choice],
                bot_choice=choices[bot_choice]
            )
            db.update_score(query.from_user.id, SCORE_VALUES['game_win'])
            db.update_reputation(query.from_user.id, SCORE_VALUES['reputation_per_message'])
        elif result == 'lose':
            message = GAME_MESSAGES['rps_lose'].format(
                user_choice=choices[user_choice],
                bot_choice=choices[bot_choice]
            )
        else:
            message = GAME_MESSAGES['rps_draw'].format(
                user_choice=choices[user_choice],
                bot_choice=choices[bot_choice]
            )

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
        await query.edit_message_text(GAME_MESSAGES['quiz_game'].format(question=question['question']), reply_markup=reply_markup)

    async def handle_quiz_answer(self, query, context):
        """Обработка ответа на вопрос викторины"""
        answer_index = int(query.data.split('_')[1])
        correct_index = context.user_data.get('quiz_correct')

        if correct_index is None:
            await query.edit_message_text(GAME_MESSAGES['quiz_not_found'])
            return

        question = context.user_data.get('quiz_question', {})

        if answer_index == correct_index:
            keyboard = [
                [InlineKeyboardButton("🚀 Старт", callback_data='cmd_start')],
                [InlineKeyboardButton("🔄 Начать заново", callback_data='cmd_restart')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(GAME_MESSAGES['quiz_correct'].format(
                question=question.get('question', ''),
                answer=question.get('answers', [])[correct_index]
            ), reply_markup=reply_markup)
            db.update_score(query.from_user.id, SCORE_VALUES['game_win'])
        else:
            keyboard = [
                [InlineKeyboardButton("🚀 Старт", callback_data='cmd_start')],
                [InlineKeyboardButton("🔄 Начать заново", callback_data='cmd_restart')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            correct_answer = question.get('answers', [])[correct_index] if correct_index < len(question.get('answers', [])) else "неизвестен"
            await query.edit_message_text(GAME_MESSAGES['quiz_wrong'].format(
                question=question.get('question', ''),
                correct_answer=correct_answer
            ), reply_markup=reply_markup)

        # Очистка данных викторины
        context.user_data.pop('quiz_correct', None)
        context.user_data.pop('quiz_question', None)

    async def start_battleship_game(self, query, context):
        """Запуск игры 'Морской бой'"""
        # Создаем поле 5x5 для упрощения (вместо 10x10)
        board = [['~' for _ in range(5)] for _ in range(5)]
        bot_ships = self.place_ships()  # Размещаем корабли бота

        # Сохраняем состояние игры
        context.user_data['battleship_board'] = board
        context.user_data['battleship_bot_ships'] = bot_ships
        context.user_data['battleship_shots'] = 0
        context.user_data['battleship_hits'] = 0

        # Создаем клавиатуру для стрельбы
        keyboard = self.create_battleship_keyboard(board)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(GAME_MESSAGES['battleship_start'], reply_markup=reply_markup, parse_mode='HTML')

    def create_battleship_keyboard(self, board):
        """Создание клавиатуры для Морского боя"""
        keyboard = []

        # Заголовки столбцов (0-4)
        header_row = [InlineKeyboardButton(" ", callback_data='bs_header')]
        for j in range(5):
            header_row.append(InlineKeyboardButton(str(j), callback_data='bs_header'))
        keyboard.append(header_row)

        # Строки с буквами и клетками
        letters = ['A', 'B', 'C', 'D', 'E']
        for i in range(5):
            row = [InlineKeyboardButton(letters[i], callback_data='bs_header')]
            for j in range(5):
                cell = board[i][j]
                callback_data = f'bs_{i}{j}'  # Координаты в формате row,col
                row.append(InlineKeyboardButton(cell, callback_data=callback_data))
            keyboard.append(row)

        # Кнопка назад
        keyboard.append([InlineKeyboardButton("⬅️ Назад к играм", callback_data='cmd_play_game')])

        return keyboard

    def place_ships(self):
        """Размещение кораблей бота (упрощенная версия - 3 корабля)"""
        ships = []  # Список кораблей как список координат
        import random

        # Размещаем 3 корабля: 3-клеточный, 2-клеточный, 1-клеточный
        ship_sizes = [3, 2, 1]

        for size in ship_sizes:
            placed = False
            while not placed:
                # Случайное направление: 0 - горизонтально, 1 - вертикально
                direction = random.randint(0, 1)
                if direction == 0:  # Горизонтально
                    row = random.randint(0, 4)
                    col = random.randint(0, 4 - size)
                    ship_coords = [(row, col + i) for i in range(size)]
                else:  # Вертикально
                    row = random.randint(0, 4 - size)
                    col = random.randint(0, 4)
                    ship_coords = [(row + i, col) for i in range(size)]

                # Проверяем, что корабль не пересекает другие
                if not any(coord in [c for ship in ships for c in ship] for coord in ship_coords):
                    ships.append(ship_coords)
                    placed = True

        return ships

    async def handle_battleship_shot(self, query, context):
        """Обработка выстрела в Морском бое"""
        if query.data == 'bs_header':
            return  # Игнорируем клики по заголовкам

        # Парсим координаты
        coords = query.data[3:]  # bs_01 -> 01
        if len(coords) != 2:
            await query.answer(GAME_MESSAGES['battleship_invalid_coord'])
            return

        try:
            row, col = int(coords[0]), int(coords[1])
        except ValueError:
            await query.answer(GAME_MESSAGES['battleship_invalid_coord'])
            return

        board = context.user_data.get('battleship_board')
        bot_ships = context.user_data.get('battleship_bot_ships')

        if not board or not (0 <= row < 5 and 0 <= col < 5):
            await query.answer(GAME_MESSAGES['battleship_invalid_coord'])
            return

        # Проверяем, стреляли ли уже в эту клетку
        if board[row][col] != '~':
            await query.answer(GAME_MESSAGES['battleship_already_shot'])
            return

        # Обновляем счетчик выстрелов
        context.user_data['battleship_shots'] += 1

        # Проверяем попадание
        hit = False
        ship_hit = None
        for ship in bot_ships:
            if (row, col) in ship:
                hit = True
                ship_hit = ship
                break

        if hit:
            board[row][col] = '💥'  # Попадание
            context.user_data['battleship_hits'] += 1

            # Проверяем, потоплен ли корабль
            ship_sunk = all(board[r][c] == '💥' for r, c in ship_hit)
            if ship_sunk:
                # Помечаем потопленный корабль
                for r, c in ship_hit:
                    board[r][c] = '🔥'
                await query.answer(GAME_MESSAGES['battleship_sunk'])
            else:
                await query.answer(GAME_MESSAGES['battleship_hit'])
        else:
            board[row][col] = '💧'  # Промах
            await query.answer(GAME_MESSAGES['battleship_miss'])

        # Проверяем победу (все корабли потоплены)
        total_ship_cells = sum(len(ship) for ship in bot_ships)
        if context.user_data['battleship_hits'] >= total_ship_cells:
            # Победа игрока
            db.update_score(query.from_user.id, SCORE_VALUES['tic_tac_toe_win'])  # +15 очков
            db.update_reputation(query.from_user.id, SCORE_VALUES['reputation_per_message'])

            # Проверяем повышение ранга
            rank_update = db.update_rank(query.from_user.id, query.message.chat.id, query.from_user.first_name)
            if rank_update and rank_update.get("promoted"):
                await query.message.chat.send_message(
                    RANK_MESSAGES['promotion_message'].format(
                        name=rank_update['name'],
                        new_rank=rank_update['new_rank']
                    )
                )

            keyboard = self.create_battleship_keyboard(board)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(GAME_MESSAGES['battleship_win'], reply_markup=reply_markup)
            # Очистка данных игры
            context.user_data.pop('battleship_board', None)
            context.user_data.pop('battleship_bot_ships', None)
            context.user_data.pop('battleship_shots', None)
            context.user_data.pop('battleship_hits', None)
        else:
            # Продолжаем игру - обновляем клавиатуру
            keyboard = self.create_battleship_keyboard(board)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(GAME_MESSAGES['battleship_start'], reply_markup=reply_markup, parse_mode='HTML')

    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Забанить пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(MODERATION_MESSAGES['no_permission'])
            return

        if len(context.args) < 2:
            await update.message.reply_text(MODERATION_MESSAGES['ban_usage'])
            return

        user_id = context.args[0]
        reason = ' '.join(context.args[1:])

        try:
            await update.effective_chat.ban_member(int(user_id))
            await update.message.reply_text(MODERATION_MESSAGES['user_banned'].format(user_id=user_id, reason=reason))
        except Exception as e:
            await update.message.reply_text(MODERATION_MESSAGES['ban_error'].format(error=e))

    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разбанить пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(MODERATION_MESSAGES['no_permission'])
            return

        if len(context.args) < 1:
            await update.message.reply_text(MODERATION_MESSAGES['unban_usage'])
            return

        user_id = context.args[0]

        try:
            await update.effective_chat.unban_member(int(user_id))
            await update.message.reply_text(MODERATION_MESSAGES['user_unbanned'].format(user_id=user_id))
        except Exception as e:
            await update.message.reply_text(MODERATION_MESSAGES['unban_error'].format(error=e))

    async def mute_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Заглушить пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(MODERATION_MESSAGES['no_permission'])
            return

        if len(context.args) < 2:
            await update.message.reply_text(MODERATION_MESSAGES['mute_usage'])
            return

        user_id = context.args[0]
        try:
            mute_time = int(context.args[1])
        except ValueError:
            await update.message.reply_text(MODERATION_MESSAGES['mute_invalid_time'])
            return

        from datetime import datetime, timedelta
        until_date = datetime.now() + timedelta(seconds=mute_time)

        try:
            await update.effective_chat.restrict_member(
                int(user_id),
                until_date=until_date,
                can_send_messages=False
            )
            await update.message.reply_text(MODERATION_MESSAGES['user_muted'].format(user_id=user_id, time=mute_time))
        except Exception as e:
            await update.message.reply_text(MODERATION_MESSAGES['mute_error'].format(error=e))

    async def unmute_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Снять заглушку с пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(MODERATION_MESSAGES['no_permission'])
            return

        if len(context.args) < 1:
            await update.message.reply_text(MODERATION_MESSAGES['unmute_usage'])
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
            await update.message.reply_text(MODERATION_MESSAGES['user_unmuted'].format(user_id=user_id))
        except Exception as e:
            await update.message.reply_text(MODERATION_MESSAGES['unmute_error'].format(error=e))

    async def kick_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кикнуть пользователя (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(MODERATION_MESSAGES['no_permission'])
            return

        if len(context.args) < 2:
            await update.message.reply_text(MODERATION_MESSAGES['kick_usage'])
            return

        user_id = context.args[0]
        reason = ' '.join(context.args[1:])

        try:
            await update.effective_chat.ban_member(int(user_id))
            await update.effective_chat.unban_member(int(user_id))  # Разбан сразу после бана = кик
            await update.message.reply_text(MODERATION_MESSAGES['user_kicked'].format(user_id=user_id, reason=reason))
        except Exception as e:
            await update.message.reply_text(MODERATION_MESSAGES['kick_error'].format(error=e))

    async def promote_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Повысить пользователя до модератора (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(MODERATION_MESSAGES['no_permission'])
            return

        if len(context.args) < 1:
            await update.message.reply_text(MODERATION_MESSAGES['promote_usage'])
            return

        user_id = context.args[0]

        try:
            await update.effective_chat.promote_member(
                int(user_id),
                can_delete_messages=True,
                can_restrict_members=True,
                can_invite_users=True
            )
            await update.message.reply_text(MODERATION_MESSAGES['user_promoted'].format(user_id=user_id))
        except Exception as e:
            await update.message.reply_text(MODERATION_MESSAGES['promote_error'].format(error=e))

    async def demote_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Понизить пользователя с модератора (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(MODERATION_MESSAGES['no_permission'])
            return

        if len(context.args) < 1:
            await update.message.reply_text(MODERATION_MESSAGES['demote_usage'])
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
            await update.message.reply_text(MODERATION_MESSAGES['user_demoted'].format(user_id=user_id))
        except Exception as e:
            await update.message.reply_text(MODERATION_MESSAGES['demote_error'].format(error=e))

    async def warn_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать предупреждение пользователю (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(MODERATION_MESSAGES['no_permission'])
            return

        if len(context.args) < 2:
            await update.message.reply_text(MODERATION_MESSAGES['warn_usage'])
            return

        user_id = context.args[0]
        reason = ' '.join(context.args[1:])

        db.add_warning(user_id, reason, update.effective_user.id)
        await update.message.reply_text(MODERATION_MESSAGES['warning_issued'].format(user_id=user_id, reason=reason))

    async def ranks_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о системе рангов"""
        await update.message.reply_text(RANK_MESSAGES['rank_info'], parse_mode='HTML')

    async def import_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Импорт пользователей из CSV файла (только админы)"""
        if not await self.is_admin(update.effective_chat, update.effective_user.id):
            await update.message.reply_text(IMPORT_MESSAGES['no_permission'])
            return

        if len(context.args) < 1:
            await update.message.reply_text(IMPORT_MESSAGES['usage'])
            return

        csv_file = context.args[0] if context.args else 'chat_-1001519866478_users_full_20251014.csv'

        # Если путь относительный, добавляем путь к директории telegram_bot
        if not os.path.isabs(csv_file):
            csv_file = os.path.join('telegram_bot', csv_file)

        await update.message.reply_text(IMPORT_MESSAGES['start_import'].format(file=csv_file))

        try:
            success = db.import_users_from_csv(csv_file)

            if success:
                await update.message.reply_text(IMPORT_MESSAGES['success'])
            else:
                await update.message.reply_text(IMPORT_MESSAGES['error'])

        except Exception as e:
            await update.message.reply_text(IMPORT_MESSAGES['file_error'].format(error=str(e)))

    async def schedule_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запланировать пост для публикации"""
        user = update.effective_user

        # Проверка прав администратора
        if not await self.is_admin(update.effective_chat, user.id):
            await update.message.reply_text(SCHEDULER_MESSAGES['no_permission'])
            return

        if len(context.args) < 2:
            await update.message.reply_text(SCHEDULER_MESSAGES['usage_schedule'])
            return

        # Парсинг времени и текста
        time_str = context.args[0]
        text = ' '.join(context.args[1:])

        try:
            schedule_time = self.parse_schedule_time(time_str)
        except ValueError as e:
            await update.message.reply_text(SCHEDULER_MESSAGES['invalid_format'].format(error=str(e)))
            return

        if schedule_time <= datetime.now():
            await update.message.reply_text(SCHEDULER_MESSAGES['time_in_past'])
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
                SCHEDULER_MESSAGES['post_scheduled'].format(
                    time=schedule_time.strftime('%Y-%m-%d %H:%M:%S'),
                    text=text[:50] + ('...' if len(text) > 50 else ''),
                    post_id=post_id
                )
            )
        else:
            await update.message.reply_text(SCHEDULER_MESSAGES['save_error'])

    async def list_posts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список запланированных постов"""
        user = update.effective_user

        # Проверка прав администратора
        if not await self.is_admin(update.effective_chat, user.id):
            await update.message.reply_text(SCHEDULER_MESSAGES['no_permission_view'])
            return

        posts = db.get_scheduled_posts(chat_id=update.effective_chat.id)

        if not posts:
            await update.message.reply_text(SCHEDULER_MESSAGES['no_posts'])
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
            await update.message.reply_text(SCHEDULER_MESSAGES['no_permission_delete'])
            return

        if len(context.args) < 1:
            await update.message.reply_text(SCHEDULER_MESSAGES['usage_delete'])
            return

        try:
            post_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(SCHEDULER_MESSAGES['invalid_id'])
            return

        success = db.delete_scheduled_post(post_id, user.id)

        if success:
            await update.message.reply_text(SCHEDULER_MESSAGES['post_deleted'].format(post_id=post_id))
        else:
            await update.message.reply_text(SCHEDULER_MESSAGES['post_not_found'].format(post_id=post_id))

    async def publish_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Опубликовать пост немедленно"""
        user = update.effective_user

        # Проверка прав администратора
        if not await self.is_admin(update.effective_chat, user.id):
            await update.message.reply_text(SCHEDULER_MESSAGES['no_permission_publish'])
            return

        if len(context.args) < 1:
            await update.message.reply_text(SCHEDULER_MESSAGES['usage_publish'])
            return

        try:
            post_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(SCHEDULER_MESSAGES['invalid_id'])
            return

        # Получаем пост из базы данных
        posts = db.get_scheduled_posts()
        post = None
        for p in posts:
            if p[0] == post_id:  # p[0] is post_id
                post = p
                break

        if not post:
            await update.message.reply_text(SCHEDULER_MESSAGES['post_not_found'].format(post_id=post_id))
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

            await update.message.reply_text(SCHEDULER_MESSAGES['post_published'].format(post_id=post_id))

        except Exception as e:
            await update.message.reply_text(SCHEDULER_MESSAGES['publish_error'].format(error=str(e)))

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
                RANK_MESSAGES['promotion_message'].format(
                    name=rank_update['name'],
                    new_rank=rank_update['new_rank']
                )
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
                USER_MESSAGES['unknown_message'],
                reply_markup=reply_markup
            )
            return

        # Случайное начисление очков от 1 до 5 вместо случайных ответов
        if random.random() < 0.1:  # 10% шанс
            bonus_points = random.randint(SCORE_VALUES['bonus_min'], SCORE_VALUES['bonus_max'])
            db.update_score(user.id, bonus_points)
            await update.message.reply_text(USER_MESSAGES['bonus_points'].format(points=bonus_points))

    async def handle_new_chat_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка новых участников чата"""
        for member in update.chat_member.new_chat_members:
            db.add_user(member.id, member.username, member.first_name, member.last_name)

            welcome_text = USER_MESSAGES['welcome_new_user'].format(name=member.first_name)

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

        await query.edit_message_text(messages.HELP_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    async def show_games_menu(self, query):
        """Показать меню выбора игр"""
        keyboard = [
            [InlineKeyboardButton("Камень-ножницы-бумага", callback_data='game_rps')],
            [InlineKeyboardButton("Крестики-нолики", callback_data='game_tic_tac_toe')],
            [InlineKeyboardButton("Викторина", callback_data='game_quiz')],
            [InlineKeyboardButton("Морской бой", callback_data='game_battleship')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(GAME_MESSAGES['select_game'], reply_markup=reply_markup)

    def run(self):
        """Запуск бота"""
        print("Bot started!")
        self.application.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()
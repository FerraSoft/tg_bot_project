"""
Обработчики игровых команд.
Отвечают за взаимодействие с играми и игровыми механиками.
"""

import logging
from typing import Dict, Callable, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from services.game_service import GameService


class GameHandlers(BaseHandler):
    """
    Обработчики игровых команд.

    Игры:
    - Камень-ножницы-бумага
    - Крестики-нолики
    - Викторина
    """

    def __init__(self, config, metrics, game_service: GameService, moderation_service=None):
        """
        Инициализация обработчика.

        Args:
            config: Конфигурация приложения
            metrics: Сборщик метрик
            game_service: Сервис управления играми
            moderation_service: Сервис модерации (опционально)
        """
        super().__init__(config, metrics)
        self.game_service = game_service
        self.moderation_service = moderation_service

    def get_command_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков команд"""
        return {
            'play_game': self.handle_play_game,
            'rock_paper_scissors': self.handle_rock_paper_scissors,
            'tic_tac_toe': self.handle_tic_tac_toe,
            'quiz': self.handle_quiz,
            'battleship': self.handle_battleship,
            'game_2048': self.handle_2048,
            'tetris': self.handle_tetris,
            'snake': self.handle_snake,
        }

    def get_callback_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков callback запросов"""
        return {
            'game_rps_rock': self.handle_rps_choice,
            'game_rps_paper': self.handle_rps_choice,
            'game_rps_scissors': self.handle_rps_choice,
            'game_rps_start': self.handle_rock_paper_scissors,
            'game_tictactoe_move': self.handle_tictactoe_move,
            'game_tictactoe_start': self.handle_tic_tac_toe,
            'game_quiz_answer': self.handle_quiz_answer,
            'game_quiz_start': self.handle_quiz,
            'game_menu': self.handle_game_menu,
            'menu_games': self.handle_game_menu,  # Обработчик для кнопки "Мини игры"
            'game_battleship_shot': self.handle_battleship_shot,
            'game_battleship_start': self.handle_battleship,
            'game_2048_move': self.handle_2048_move,
            'game_2048_start': self.handle_2048,
            'game_tetris_move': self.handle_tetris_move,
            'game_tetris_start': self.handle_tetris,
            'game_snake_move': self.handle_snake_move,
            'game_snake_start': self.handle_snake,
        }

    def get_message_handlers(self) -> Dict[str, Callable]:
        """Получение обработчиков сообщений"""
        return {}

    async def handle_play_game(self, update: Update, context: ContextTypes):
        """Обработка команды /play_game"""
        await self.safe_execute(update, context, "play_game", self._handle_play_game)

    async def _handle_play_game(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /play_game"""
        user = update.effective_user

        # Создаем клавиатуру выбора игры
        keyboard = [
            [InlineKeyboardButton("🪨 Камень-ножницы-бумага", callback_data='game_rps_start')],
            [InlineKeyboardButton("❌⭕ Крестики-нолики", callback_data='game_tictactoe_start')],
            [InlineKeyboardButton("🧠 Викторина", callback_data='game_quiz_start')],
            [InlineKeyboardButton("🚢 Морской бой", callback_data='game_battleship_start')],
            # [InlineKeyboardButton("🔢 2048", callback_data='game_2048_start')],
            # [InlineKeyboardButton("🧩 Тетрис", callback_data='game_tetris_start')],
            # [InlineKeyboardButton("🐍 Змейка", callback_data='game_snake_start')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_main')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.send_response(
            update,
            "🎮 Выберите игру:\n\n"
            "🪨 Камень-ножницы-бумага - классическая игра\n"
            "❌⭕ Крестики-нолики - стратегическая игра\n"
            "🧠 Викторина - проверка знаний\n"
            "🚢 Морской бой - потопи корабли противника\n"
            "🔢 2048 - соединяй числа и достигни 2048\n"
            "🧩 Тетрис - складывай фигуры и заполняй линии\n"
            "🐍 Змейка - управляй змейкой и собирай еду\n\n"
            "За каждую игру вы получаете очки рейтинга!",
            reply_markup=reply_markup
        )

    async def handle_rock_paper_scissors(self, update: Update, context: ContextTypes):
        """Обработка команды /rock_paper_scissors"""
        await self.safe_execute(update, context, "rock_paper_scissors", self._handle_rock_paper_scissors)

    async def _handle_rock_paper_scissors(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /rock_paper_scissors"""
        user = update.effective_user

        # Создаем игровую сессию
        session = self.game_service.create_game_session('rock_paper_scissors', user.id, update.effective_chat.id)

        if not session or not session.game_id:
            if update.callback_query:
                await update.callback_query.edit_message_text("❌ Ошибка в создании игры")
            else:
                await update.message.reply_text("❌ Ошибка в создании игры")
            return

        # Создаем клавиатуру выбора
        keyboard = [
            [InlineKeyboardButton("🪨 Камень", callback_data=f'game_rps_rock_{session.game_id}')],
            [InlineKeyboardButton("📄 Бумага", callback_data=f'game_rps_paper_{session.game_id}')],
            [InlineKeyboardButton("✂️ Ножницы", callback_data=f'game_rps_scissors_{session.game_id}')],
            [InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.send_response(
            update,
            "🤖 Камень, ножницы, бумага!\n\nВыберите ваш ход:",
            reply_markup=reply_markup
        )

    async def handle_tic_tac_toe(self, update: Update, context: ContextTypes):
        """Обработка команды /tic_tac_toe"""
        await self.safe_execute(update, context, "tic_tac_toe", self._handle_tic_tac_toe)

    async def _handle_tic_tac_toe(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /tic_tac_toe"""
        user = update.effective_user

        # Создаем игровую сессию
        session = self.game_service.create_game_session('tic_tac_toe', user.id, update.effective_chat.id)

        if not session or not session.game_id:
            if update.callback_query:
                await update.callback_query.edit_message_text("❌ Ошибка в создании игры")
            else:
                await update.message.reply_text("❌ Ошибка в создании игры")
            return

        # Создаем игровое поле
        keyboard = self._create_tictactoe_keyboard(session.game_id)

        await self.send_response(
            update,
            "❌⭕ Крестики-нолики!\n\nВы ходите первым (❌). Выберите клетку:",
            reply_markup=keyboard
        )

    async def handle_quiz(self, update: Update, context: ContextTypes):
        """Обработка команды /quiz"""
        await self.safe_execute(update, context, "quiz", self._handle_quiz)

    async def _handle_quiz(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /quiz"""
        user = update.effective_user

        # Создаем игровую сессию
        session = self.game_service.create_game_session('quiz', user.id, update.effective_chat.id)

        if not session or not session.game_id:
            if update.callback_query:
                await update.callback_query.edit_message_text("❌ Ошибка в создании игры")
            else:
                await update.message.reply_text("❌ Ошибка в создании игры")
            return

        # Получаем первый вопрос
        await self._send_quiz_question(update, session)

    async def handle_rps_choice(self, update: Update, context: ContextTypes):
        """Обработка выбора в камень-ножницы-бумага"""
        query = update.callback_query
        await query.answer()

        # Парсим callback_data
        parts = query.data.split('_')
        self.logger.debug(f"Парсинг callback_data для RPS: {query.data}, parts: {parts}")
        if len(parts) < 4:
            self.logger.error(f"Ошибка в данных игры: rps, len(parts) < 4, parts: {parts}")
            await self.send_response(update, "Ошибка в данных игры")
            return

        choice = parts[2]  # rock, paper, или scissors
        game_id = '_'.join(parts[3:])  # ID игры

        if not game_id:
            self.logger.error(f"Ошибка в данных игры: rps, game_id пустой, parts: {parts}")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        await self.safe_execute(update, context, "rps_choice", self._handle_rps_choice, game_id, choice)

    async def _handle_rps_choice(self, update: Update, context: ContextTypes, game_id: str, choice: str):
        """Внутренняя обработка выбора в RPS"""
        query = update.callback_query

        if not game_id:
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        # Проверяем, активна ли сессия
        session = self.game_service.get_game_session(game_id)
        if not session or session.status != "active":
            await self.handle_game_menu(update, context)
            return

        # Играем в RPS
        result = self.game_service.play_rock_paper_scissors(game_id, choice)

        # Формируем результат
        choice_emojis = {
            'rock': '🪨',
            'paper': '📄',
            'scissors': '✂️'
        }

        result_text = (
            f"🤖 Камень, ножницы, бумага!\n\n"
            f"Ваш выбор: {choice_emojis[choice]}\n"
            f"Выбор бота: {choice_emojis[result['bot_choice']]}\n\n"
        )

        if result['result'] == 'win':
            result_text += f"🎉 Вы выиграли! +{result['points']} очков"
        elif result['result'] == 'draw':
            result_text += f"🤝 Ничья! +{result['points']} очков"
        else:
            result_text += "😞 Вы проиграли!"

        # Завершаем игровую сессию
        self.game_service.end_game_session(game_id)

        # Добавляем кнопку назад к играм
        keyboard = [[InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.send_response(update, result_text, reply_markup=reply_markup)

    async def handle_tictactoe_move(self, update: Update, context: ContextTypes):
        """Обработка хода в крестики-нолики"""
        query = update.callback_query
        await query.answer()

        # Парсим callback_data
        parts = query.data.split('_')
        logging.debug(f"Парсинг callback_data для tictactoe: {query.data}, parts: {parts}")

        # Проверяем, является ли это start командой
        if len(parts) == 3 and parts[2] == 'start':
            logging.warning(f"Получена start команда для tictactoe, игнорируем: {query.data}")
            return

        if len(parts) < 5:
            logging.error(f"Ошибка в данных игры: tictactoe, len(parts) < 5, parts: {parts}")
            await self.send_response(update, "Ошибка в данных игры")
            return

        try:
            position = int(parts[3])  # позиция хода
            game_id = '_'.join(parts[4:]) if len(parts) > 4 else None
        except (ValueError, IndexError):
            self.logger.error(f"Ошибка в формате данных игры для tictactoe: parts: {parts}")
            await self.send_response(update, "Ошибка в формате данных игры")
            return

        self.logger.info(f"Обработка хода в tictactoe: game_id={game_id}, position={position}, parts={parts}")
        if not game_id:
            self.logger.error(f"Ошибка в данных игры: tictactoe, game_id пустой, parts: {parts}")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        await self.safe_execute(update, context, "tictactoe_move", self._handle_tictactoe_move, game_id, position)

    async def _handle_tictactoe_move(self, update: Update, context: ContextTypes, game_id: str, position: int):
        """Внутренняя обработка хода в крестики-нолики"""
        query = update.callback_query

        if not game_id:
            logging.error("Ошибка в данных игры: tictactoe, game_id пустой")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        # Проверяем, активна ли сессия
        session = self.game_service.get_game_session(game_id)
        if not session or session.status != "active":
            await self.handle_game_menu(update, context)
            return

        # Делаем ход
        result = self.game_service.make_tic_tac_toe_move(game_id, position)

        if result['status'] == 'player_win':
            # Создаем новое игровое поле
            keyboard = self._create_tictactoe_keyboard(game_id)
            await self.send_response(
                update,
                f"🎉 Вы выиграли! 🏆\n\n{self._format_tictactoe_board(result['board'])}",
                reply_markup=keyboard
            )
            self.game_service.end_game_session(game_id)
        elif result['status'] == 'bot_win':
            keyboard = [[InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_response(
                update,
                f"😞 Вы проиграли. Бот победил!\n\n{self._format_tictactoe_board(result['board'])}",
                reply_markup=reply_markup
            )
            self.game_service.end_game_session(game_id)
        elif result['status'] == 'draw':
            keyboard = [[InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_response(
                update,
                f"🤝 Ничья!\n\n{self._format_tictactoe_board(result['board'])}",
                reply_markup=reply_markup
            )
            self.game_service.end_game_session(game_id)
        elif result['status'] == 'already_occupied':
            # Клетка уже занята, просто подтверждаем
            await update.callback_query.answer("Клетка уже занята!")
        elif result['status'] == 'continue':
            # Ход сделан
            keyboard = self._create_tictactoe_keyboard(game_id)
            await self.send_response(
                update,
                f"Ход бота сделан!\n\n{self._format_tictactoe_board(result['board'])}\n\nВаш ход:",
                reply_markup=keyboard
            )

    async def handle_quiz_answer(self, update: Update, context: ContextTypes):
        """Обработка ответа в викторине"""
        query = update.callback_query
        await query.answer()

        # Парсим callback_data
        parts = query.data.split('_')
        logging.debug(f"Парсинг callback_data для quiz: {query.data}, parts: {parts}")
        if len(parts) < 4:
            logging.error(f"Ошибка в данных игры: quiz, len(parts) < 4, parts: {parts}")
            await self.send_response(update, "Ошибка в данных игры")
            return

        answer_index = int(parts[3])  # индекс ответа
        game_id = '_'.join(parts[4:]) if len(parts) > 4 else None

        if not game_id:
            logging.error(f"Ошибка в данных игры: quiz, game_id пустой, parts: {parts}")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        await self.safe_execute(update, context, "quiz_answer", self._handle_quiz_answer, game_id, answer_index)

    async def _handle_quiz_answer(self, update: Update, context: ContextTypes, game_id: str, answer_index: int):
        """Внутренняя обработка ответа в викторине"""
        query = update.callback_query

        if not game_id:
            logging.error("Ошибка в данных игры: quiz, game_id пустой")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        # Проверяем, активна ли сессия
        session = self.game_service.get_game_session(game_id)
        if not session or session.status != "active":
            await self.handle_game_menu(update, context)
            return

        # Отвечаем на вопрос
        result = self.game_service.answer_quiz_question(game_id, answer_index)

        if result['status'] == 'game_over':
            # Игра завершена
            keyboard = [[InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_response(
                update,
                f"🎉 Викторина завершена!\n\n"
                f"Правильных ответов: {result['final_score']}\n"
                f"Получено очков: {result['points']}",
                reply_markup=reply_markup
            )
            self.game_service.end_game_session(game_id)
        else:
            # Продолжаем викторину
            session = self.game_service.get_game_session(game_id)
            if session:
                await self._send_quiz_question(update, session, edit_message=True)

    async def handle_game_menu(self, update: Update, context: ContextTypes):
        """Обработка нажатия на игровое меню"""
        query = update.callback_query
        await query.answer()

        # Для игрового меню не создаем игровую сессию, так как это не игра
        user = update.effective_user

        # Создаем клавиатуру выбора игры
        keyboard = [
            [InlineKeyboardButton("🪨 Камень-ножницы-бумага", callback_data='game_rps_start')],
            [InlineKeyboardButton("❌⭕ Крестики-нолики", callback_data='game_tictactoe_start')],
            [InlineKeyboardButton("🧠 Викторина", callback_data='game_quiz_start')],
            [InlineKeyboardButton("🚢 Морской бой", callback_data='game_battleship_start')],
            # [InlineKeyboardButton("🔢 2048", callback_data='game_2048_start')],
            # [InlineKeyboardButton("🧩 Тетрис", callback_data='game_tetris_start')],
            # [InlineKeyboardButton("🐍 Змейка", callback_data='game_snake_start')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu_help')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.send_response(
            update,
            "🎮 Выберите игру:\n\n"
            "🪨 Камень-ножницы-бумага - классическая игра\n"
            "❌⭕ Крестики-нолики - стратегическая игра\n"
            "🧠 Викторина - проверка знаний\n"
            "🚢 Морской бой - потопи корабли противника\n"
            "🔢 2048 - соединяй числа и достигни 2048\n"
            "🧩 Тетрис - складывай фигуры и заполняй линии\n"
            "🐍 Змейка - управляй змейкой и собирай еду\n\n"
            "За каждую игру вы получаете очки рейтинга!",
            reply_markup=reply_markup
        )

    def _create_tictactoe_keyboard(self, game_id: str) -> InlineKeyboardMarkup:
        """Создание клавиатуры для крестики-нолики"""
        keyboard = []
        if not game_id:
            return InlineKeyboardMarkup([])

        session = self.game_service.get_game_session(game_id)

        if not session:
            return InlineKeyboardMarkup([])

        board = session.data['board']

        # Создаем кнопки для игрового поля 3x3
        for i in range(3):
            row = []
            for j in range(3):
                position = i * 3 + j
                cell_value = board[position]

                if cell_value == ' ':
                    button_text = "⬜"
                    callback_data = f"game_tictactoe_move_{position}_{game_id}"
                elif cell_value == 'X':
                    button_text = "❌"
                    callback_data = f"game_tictactoe_move_{position}_{game_id}"
                else:
                    button_text = "⭕"
                    callback_data = f"game_tictactoe_move_{position}_{game_id}"

                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))

            keyboard.append(row)

        # Добавляем кнопку назад
        keyboard.append([InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')])

        return InlineKeyboardMarkup(keyboard)

    def _format_tictactoe_board(self, board: List[str]) -> str:
        """Форматирование игрового поля"""
        symbols = {' ': '⬜', 'X': '❌', 'O': '⭕'}

        formatted_board = ""
        for i in range(3):
            for j in range(3):
                formatted_board += symbols[board[i * 3 + j]]
            formatted_board += "\n"

        return formatted_board

    async def _send_quiz_question(self, update: Update, session, edit_message: bool = False):
        """Отправка вопроса викторины"""
        current_q = session.data['current_question']
        questions = session.data['questions']

        if current_q >= len(questions):
            await self.send_response(update, "❌ Ошибка: вопросы не найдены")
            return

        question = questions[current_q]

        # Создаем клавиатуру с ответами
        keyboard = []
        for i, answer in enumerate(question['answers']):
            keyboard.append([InlineKeyboardButton(
                answer,
                callback_data=f"game_quiz_answer_{i}_{session.game_id}"
            )])

        keyboard.append([InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        question_text = (
            f"🧠 Викторина - Вопрос {current_q + 1}/{len(questions)}\n\n"
            f"<b>{question['question']}</b>\n\n"
            "Выберите правильный ответ:"
        )

        await self.send_response(
            update,
            question_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    # ===== НОВЫЕ ИГРЫ =====

    async def handle_battleship(self, update: Update, context: ContextTypes):
        """Обработка команды /battleship"""
        await self.safe_execute(update, context, "battleship", self._handle_battleship)

    async def _handle_battleship(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /battleship"""
        user = update.effective_user

        # Создаем игровую сессию
        session = self.game_service.create_game_session('battleship', user.id, update.effective_chat.id)

        if not session or not session.game_id:
            await self.send_response(update, "❌ Ошибка в создании игры")
            return

        # Создаем клавиатуру для игры
        keyboard = self._create_battleship_keyboard(session.game_id)

        await self.send_response(
            update,
            "🚢 Морской бой!\n\n"
            "Потопи все корабли противника!\n"
            "Используй кнопки для стрельбы по координатам.\n\n"
            "Формат: строка_столбец (0-4)",
            reply_markup=keyboard
        )

    async def handle_2048(self, update: Update, context: ContextTypes):
        """Обработка команды /game_2048"""
        await self.safe_execute(update, context, "game_2048", self._handle_2048)

    async def _handle_2048(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /game_2048"""
        user = update.effective_user

        # Создаем игровую сессию
        session = self.game_service.create_game_session('game_2048', user.id, update.effective_chat.id)

        if not session or not session.game_id:
            await self.send_response(update, "❌ Ошибка в создании игры")
            return

        # Создаем клавиатуру для игры
        keyboard = self._create_2048_keyboard(session.game_id)

        await self.send_response(
            update,
            "🔢 2048!\n\n"
            "Соединяй одинаковые числа стрелками!\n"
            "Цель - получить 2048!",
            reply_markup=keyboard
        )

    async def handle_tetris(self, update: Update, context: ContextTypes):
        """Обработка команды /tetris"""
        await self.safe_execute(update, context, "tetris", self._handle_tetris)

    async def _handle_tetris(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /tetris"""
        user = update.effective_user

        # Создаем игровую сессию
        session = self.game_service.create_game_session('tetris', user.id, update.effective_chat.id)

        if not session or not session.game_id:
            await self.send_response(update, "❌ Ошибка в создании игры")
            return

        # Создаем клавиатуру для игры
        keyboard = self._create_tetris_keyboard(session.game_id)

        await self.send_response(
            update,
            "🧩 Тетрис!\n\n"
            "Управляй падающими фигурами!\n"
            "Заполняй линии, чтобы они исчезли!",
            reply_markup=keyboard
        )

    async def handle_snake(self, update: Update, context: ContextTypes):
        """Обработка команды /snake"""
        await self.safe_execute(update, context, "snake", self._handle_snake)

    async def _handle_snake(self, update: Update, context: ContextTypes):
        """Внутренняя обработка команды /snake"""
        user = update.effective_user

        # Создаем игровую сессию
        session = self.game_service.create_game_session('snake', user.id, update.effective_chat.id)

        if not session or not session.game_id:
            await self.send_response(update, "❌ Ошибка в создании игры")
            return

        # Создаем клавиатуру для игры
        keyboard = self._create_snake_keyboard(session.game_id)

        await self.send_response(
            update,
            "🐍 Змейка!\n\n"
            "Управляй змейкой и собирай еду!\n"
            "Не врезайся в стенки и себя!",
            reply_markup=keyboard
        )

    # ===== ОБРАБОТЧИКИ ХОДОВ ДЛЯ НОВЫХ ИГР =====

    async def handle_battleship_shot(self, update: Update, context: ContextTypes):
        """Обработка хода в морском бое"""
        query = update.callback_query
        await query.answer()

        # Парсим координаты
        parts = query.data.split('_')
        logging.debug(f"Парсинг callback_data для battleship: {query.data}, parts: {parts}")

        # Проверяем, является ли это start командой
        if len(parts) == 3 and parts[2] == 'start':
            logging.warning(f"Получена start команда для battleship, игнорируем: {query.data}")
            return

        if len(parts) < 6:
            logging.error(f"Ошибка в данных игры: battleship, len(parts) < 6, parts: {parts}")
            await self.send_response(update, "Ошибка в данных игры")
            return

        try:
            row, col = int(parts[3]), int(parts[4])
            game_id = '_'.join(parts[5:]) if len(parts) > 5 else None
        except (ValueError, IndexError):
            self.logger.error(f"Ошибка в формате данных игры для battleship: parts: {parts}")
            await self.send_response(update, "Ошибка в формате данных игры")
            return

        self.logger.info(f"Обработка хода в battleship: game_id={game_id}, row={row}, col={col}, parts={parts}")
        if not game_id:
            self.logger.error(f"Ошибка в данных игры: battleship, game_id пустой, parts: {parts}")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        await self.safe_execute(update, context, "battleship_shot", self._handle_battleship_shot, game_id, row, col)

    async def _handle_battleship_shot(self, update: Update, context: ContextTypes, game_id: str, row: int, col: int):
        """Внутренняя обработка хода в морском бое"""
        query = update.callback_query

        if not game_id:
            logging.error("Ошибка в данных игры: battleship, game_id пустой")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        # Проверяем, активна ли сессия
        session = self.game_service.get_game_session(game_id)
        if not session or session.status != "active":
            await self.handle_game_menu(update, context)
            return

        # Делаем ход
        result = self.game_service.make_battleship_shot(game_id, row, col)

        if result['status'] == 'win':
            keyboard = self._create_battleship_keyboard(game_id)
            await self.send_response(
                update,
                f"🎉 Поздравляем! Вы победили!\n"
                f"Выстрелов сделано: {result['shots']}\n"
                f"Получено очков: {result['points']}",
                reply_markup=keyboard
            )
            self.game_service.end_game_session(game_id)
        elif result['status'] == 'already_shot':
            # Уже стреляли, просто подтверждаем
            await update.callback_query.answer("В эту клетку уже стреляли!")
        elif result['status'] == 'continue':
            keyboard = self._create_battleship_keyboard(game_id)
            hit_text = "💥 Попадание!" if result['hit'] else "💧 Промах!"
            await self.send_response(
                update,
                f"{hit_text}\nВыстрелов: {result['shots']}\nВаш ход:",
                reply_markup=keyboard
            )

    async def handle_2048_move(self, update: Update, context: ContextTypes):
        """Обработка хода в 2048"""
        query = update.callback_query
        await query.answer()

        # Парсим направление
        parts = query.data.split('_')
        logging.debug(f"Парсинг callback_data для 2048: {query.data}, parts: {parts}")

        # Проверяем, является ли это start командой
        if len(parts) == 3 and parts[2] == 'start':
            logging.warning(f"Получена start команда для 2048, игнорируем: {query.data}")
            return

        if len(parts) < 4:
            self.logger.error(f"Ошибка в данных игры: 2048, len(parts) < 4, parts: {parts}")
            await self.send_response(update, "Ошибка в данных игры")
            return

        direction = parts[3]
        game_id = '_'.join(parts[4:]) if len(parts) > 4 else None

        self.logger.info(f"Обработка хода в 2048: game_id={game_id}, direction={direction}, parts={parts}")
        if not game_id:
            self.logger.error(f"Ошибка в данных игры: 2048, game_id пустой, parts: {parts}")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        await self.safe_execute(update, context, "2048_move", self._handle_2048_move, game_id, direction)

    async def _handle_2048_move(self, update: Update, context: ContextTypes, game_id: str, direction: str):
        """Внутренняя обработка хода в 2048"""
        query = update.callback_query

        if not game_id:
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        # Проверяем, активна ли сессия
        session = self.game_service.get_game_session(game_id)
        if not session or session.status != "active":
            await self.handle_game_menu(update, context)
            return

        # Делаем ход
        result = self.game_service.make_2048_move(game_id, direction)

        if result['status'] == 'win':
            keyboard = self._create_2048_keyboard(game_id)
            await self.send_response(
                update,
                f"🎉 Поздравляем! Вы достигли 2048!\n"
                f"Счет: {result['score']}\n"
                f"Получено очков: {result['points']}",
                reply_markup=keyboard
            )
            self.game_service.end_game_session(game_id)
        elif result['status'] == 'lose':
            keyboard = self._create_2048_keyboard(game_id)
            await self.send_response(
                update,
                f"😞 Игра окончена!\n"
                f"Счет: {result['score']}",
                reply_markup=keyboard
            )
            self.game_service.end_game_session(game_id)
        else:
            last_score = session.data.get('last_score', -1)
            if result['score'] != last_score:
                keyboard = self._create_2048_keyboard(game_id)
                moves_text = f"\nХоды: {result.get('moves', 'N/A')}" if 'moves' in result else ""
                await self.send_response(
                    update,
                    f"Счет: {result['score']}{moves_text}\nВаш ход:",
                    reply_markup=keyboard
                )
                session.data['last_score'] = result['score']
            else:
                await update.callback_query.answer("Нет возможных ходов в этом направлении!")

    async def handle_tetris_move(self, update: Update, context: ContextTypes):
        """Обработка хода в тетрисе"""
        query = update.callback_query
        await query.answer()

        # Парсим действие
        parts = query.data.split('_')
        logging.debug(f"Парсинг callback_data для tetris: {query.data}, parts: {parts}")

        # Проверяем, является ли это start командой
        if len(parts) == 3 and parts[2] == 'start':
            logging.warning(f"Получена start команда для tetris, игнорируем: {query.data}")
            return

        if len(parts) < 4:
            self.logger.error(f"Ошибка в данных игры: tetris, len(parts) < 4, parts: {parts}")
            await self.send_response(update, "Ошибка в данных игры")
            return

        action = parts[3]
        game_id = '_'.join(parts[4:]) if len(parts) > 4 else None

        self.logger.info(f"Обработка хода в tetris: game_id={game_id}, action={action}, parts={parts}")
        if not game_id:
            self.logger.error(f"Ошибка в данных игры: tetris, game_id пустой, parts: {parts}")
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        await self.safe_execute(update, context, "tetris_move", self._handle_tetris_move, game_id, action)

    async def _handle_tetris_move(self, update: Update, context: ContextTypes, game_id: str, action: str):
        """Внутренняя обработка хода в тетрисе"""
        query = update.callback_query

        if not game_id:
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        # Проверяем, активна ли сессия
        session = self.game_service.get_game_session(game_id)
        if not session or session.status != "active":
            await self.handle_game_menu(update, context)
            return

        # Делаем ход
        result = self.game_service.make_tetris_move(game_id, action)

        if result['status'] == 'game_over':
            keyboard = self._create_tetris_keyboard(game_id)
            await self.send_response(
                update,
                f"😞 Игра окончена!\n"
                f"Счет: {result['score']}\n"
                f"Линий очищено: {result['lines_cleared']}",
                reply_markup=keyboard
            )
            self.game_service.end_game_session(game_id)
        else:
            last_score = session.data.get('last_score', -1)
            if result['score'] != last_score:
                keyboard = self._create_tetris_keyboard(game_id)
                level_text = f"\nУровень: {result.get('level', 'N/A')}" if 'level' in result else ""
                await self.send_response(
                    update,
                    f"Счет: {result['score']}\n"
                    f"Линий: {result['lines_cleared']}{level_text}",
                    reply_markup=keyboard
                )
                session.data['last_score'] = result['score']
            else:
                await update.callback_query.answer("Нет изменений!")

    async def handle_snake_move(self, update: Update, context: ContextTypes):
        """Обработка хода в змейке"""
        query = update.callback_query
        await query.answer()

        # Парсим направление
        parts = query.data.split('_')
        logging.debug(f"Парсинг callback_data для snake: {query.data}, parts: {parts}")

        # Проверяем, является ли это start командой
        if len(parts) == 3 and parts[2] == 'start':
            logging.warning(f"Получена start команда для snake, игнорируем: {query.data}")
            return

        if len(parts) < 4:
            self.logger.error(f"Ошибка в данных игры: snake, len(parts) < 4, parts: {parts}")
            await query.edit_message_text("Ошибка в данных игры")
            return

        direction = parts[3]
        game_id = '_'.join(parts[4:]) if len(parts) > 4 else None

        self.logger.info(f"Обработка хода в snake: game_id={game_id}, direction={direction}, parts={parts}")
        if not game_id:
            self.logger.error(f"Ошибка в данных игры: snake, game_id пустой, parts: {parts}")
            await query.edit_message_text("❌ Ошибка в данных игры")
            return

        await self.safe_execute(update, context, "snake_move", self._handle_snake_move, game_id, direction)

    async def _handle_snake_move(self, update: Update, context: ContextTypes, game_id: str, direction: str):
        """Внутренняя обработка хода в змейке"""
        query = update.callback_query

        if not game_id:
            await self.send_response(update, "❌ Ошибка в данных игры")
            return

        # Проверяем, активна ли сессия
        session = self.game_service.get_game_session(game_id)
        if not session or session.status != "active":
            await self.handle_game_menu(update, context)
            return

        # Делаем ход
        result = self.game_service.make_snake_move(game_id, direction)

        if result['status'] == 'game_over':
            keyboard = self._create_snake_keyboard(game_id)
            await self.send_response(
                update,
                f"😞 Игра окончена!\n"
                f"Длина змейки: {result['length']}\n"
                f"Счет: {result['score']}",
                reply_markup=keyboard
            )
            self.game_service.end_game_session(game_id)
        else:
            last_score = session.data.get('last_score', -1)
            if result['score'] != last_score:
                keyboard = self._create_snake_keyboard(game_id)
                await self.send_response(
                    update,
                    f"Длина: {result['length']}\n"
                    f"Счет: {result['score']}\n"
                    f"Ваш ход:",
                    reply_markup=keyboard
                )
                session.data['last_score'] = result['score']
            else:
                await update.callback_query.answer("Нет изменений!")

    # ===== СОЗДАНИЕ КЛАВИАТУР ДЛЯ НОВЫХ ИГР =====

    def _create_battleship_keyboard(self, game_id: str) -> InlineKeyboardMarkup:
        """Создание клавиатуры для морского боя"""
        keyboard = []
        if not game_id:
            return InlineKeyboardMarkup([])

        letters = ['A', 'B', 'C', 'D', 'E']

        # Заголовок
        header_row = [InlineKeyboardButton(" ", callback_data='header')]
        for j in range(5):
            header_row.append(InlineKeyboardButton(str(j), callback_data='header'))
        keyboard.append(header_row)

        # Игровое поле
        session = self.game_service.get_game_session(game_id)
        if session:
            board = session.data['bot_board']
            for i in range(5):
                row = [InlineKeyboardButton(letters[i], callback_data='header')]
                for j in range(5):
                    cell = board[i][j]
                    if cell == '~':
                        text = '🌊'
                        callback_data = f'game_battleship_shot_{i}_{j}_{game_id}'
                    elif cell == '💥':
                        text = '💥'
                        callback_data = f'game_battleship_shot_{i}_{j}_{game_id}'
                    elif cell == '💧':
                        text = '💧'
                        callback_data = f'game_battleship_shot_{i}_{j}_{game_id}'
                    else:
                        text = cell
                        callback_data = f'game_battleship_shot_{i}_{j}_{game_id}'

                    row.append(InlineKeyboardButton(text, callback_data=callback_data))
                keyboard.append(row)

        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("🔄 Новая игра", callback_data='game_battleship_start'),
            InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')
        ])

        return InlineKeyboardMarkup(keyboard)

    def _create_2048_keyboard(self, game_id: str) -> InlineKeyboardMarkup:
        """Создание клавиатуры для 2048"""
        keyboard = []
        if not game_id:
            return InlineKeyboardMarkup([])

        session = self.game_service.get_game_session(game_id)
        if session:
            board = session.data['board']
            for i in range(4):
                row = []
                for j in range(4):
                    cell = board[i][j]
                    text = str(cell) if cell != 0 else ' '
                    row.append(InlineKeyboardButton(text, callback_data=f'game_2048_cell_{i}_{j}_{game_id}'))
                keyboard.append(row)

        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data=f'game_2048_move_left_{game_id}'),
            InlineKeyboardButton("⬆️", callback_data=f'game_2048_move_up_{game_id}'),
            InlineKeyboardButton("⬇️", callback_data=f'game_2048_move_down_{game_id}'),
            InlineKeyboardButton("➡️", callback_data=f'game_2048_move_right_{game_id}')
        ])

        keyboard.append([
            InlineKeyboardButton("🔄 Новая игра", callback_data='game_2048_start'),
            InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')
        ])

        return InlineKeyboardMarkup(keyboard)

    def _create_tetris_keyboard(self, game_id: str) -> InlineKeyboardMarkup:
        """Создание клавиатуры для тетриса"""
        keyboard = []
        if not game_id:
            return InlineKeyboardMarkup([])

        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data=f'game_tetris_move_left_{game_id}'),
            InlineKeyboardButton("🔄", callback_data=f'game_tetris_move_rotate_{game_id}'),
            InlineKeyboardButton("➡️", callback_data=f'game_tetris_move_right_{game_id}')
        ])

        keyboard.append([
            InlineKeyboardButton("⬇️", callback_data=f'game_tetris_move_down_{game_id}'),
            InlineKeyboardButton("🔄 Новая игра", callback_data='game_tetris_start'),
            InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')
        ])

        return InlineKeyboardMarkup(keyboard)

    def _create_snake_keyboard(self, game_id: str) -> InlineKeyboardMarkup:
        """Создание клавиатуры для змейки"""
        keyboard = []
        if not game_id:
            return InlineKeyboardMarkup([])

        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data=f'game_snake_move_left_{game_id}'),
            InlineKeyboardButton("⬆️", callback_data=f'game_snake_move_up_{game_id}'),
            InlineKeyboardButton("⬇️", callback_data=f'game_snake_move_down_{game_id}'),
            InlineKeyboardButton("➡️", callback_data=f'game_snake_move_right_{game_id}')
        ])

        keyboard.append([
            InlineKeyboardButton("🔄 Новая игра", callback_data='game_snake_start'),
            InlineKeyboardButton("⬅️ Назад к играм", callback_data='game_menu')
        ])

        return InlineKeyboardMarkup(keyboard)
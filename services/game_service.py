"""
Сервис управления играми.
Отвечает за бизнес-логику игровых механик.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from core.exceptions import ValidationError
from utils.validators import InputValidator
import random


@dataclass
class GameSession:
    """Игровая сессия"""
    game_id: str
    game_type: str
    player_id: int
    chat_id: int
    status: str = "active"
    created_at: datetime = None
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.data is None:
            self.data = {}


class GameService:
    """
    Сервис для управления игровыми механиками.

    Отвечает за:
    - Управление игровыми сессиями
    - Логику игр (камень-ножницы-бумага, викторина, etc.)
    - Расчет очков за игры
    - Статистику игровых достижений
    """

    def __init__(self, user_repository, score_repository):
        """
        Инициализация сервиса.

        Args:
            user_repository: Репозиторий пользователей
            score_repository: Репозиторий очков и рейтингов
        """
        self.user_repo = user_repository
        self.score_repo = score_repository
        self.logger = logging.getLogger(__name__)

        # Настройки игр
        self.game_settings = {
            'rock_paper_scissors': {
                'points_win': 5,
                'points_draw': 1
            },
            'tic_tac_toe': {
                'points_win': 15,
                'points_draw': 3
            },
            'quiz': {
                'points_correct': 5,
                'max_questions': 10
            },
            'battleship': {
                'points_win': 20,
                'board_size': 5,
                'ships': [3, 2, 1]  # размеры кораблей
            },
            'game_2048': {
                'points_win': 20,
                'board_size': 4,
                'win_value': 2048
            },
            'tetris': {
                'points_per_line': 10,
                'board_width': 10,
                'board_height': 20
            },
            'snake': {
                'points_per_food': 10,
                'board_size': 10,
                'initial_length': 3
            }
        }

        # Вопросы для викторины
        self.quiz_questions = [
            {
                'question': 'Столица Франции?',
                'answers': ['Париж', 'Лондон', 'Берлин', 'Мадрид'],
                'correct': 0
            },
            {
                'question': 'Сколько континентов на Земле?',
                'answers': ['5', '6', '7', '8'],
                'correct': 2
            },
            {
                'question': 'Какой газ составляет большую часть атмосферы?',
                'answers': ['Кислород', 'Азот', 'Углекислый газ', 'Водород'],
                'correct': 1
            },
            {
                'question': 'В каком году был запущен первый искусственный спутник?',
                'answers': ['1955', '1957', '1959', '1961'],
                'correct': 1
            }
        ]

        # Активные игровые сессии
        self.active_sessions = {}

    def create_game_session(self, game_type: str, player_id: int, chat_id: int) -> GameSession:
        """
        Создание новой игровой сессии.

        Args:
            game_type: Тип игры
            player_id: ID игрока
            chat_id: ID чата

        Returns:
            Игровая сессия
        """
        if game_type not in self.game_settings:
            raise ValidationError(f"Неизвестный тип игры: {game_type}")

        import random
        game_id = f"{game_type[:3]}_{random.randint(100000, 999999)}"

        # Проверяем, что game_id не пустой
        if not game_id:
            raise ValidationError(f"Не удалось сгенерировать game_id для игры {game_type}")

        self.logger.info(f"Создан game_id: {game_id} для игры {game_type}")

        session = GameSession(
            game_id=game_id,
            game_type=game_type,
            player_id=player_id,
            chat_id=chat_id,
            status="active"
        )

        # Инициализируем данные игры в зависимости от типа
        if game_type == 'rock_paper_scissors':
            session.data = {
                'player_choice': None,
                'bot_choice': None,
                'result': None
            }
        elif game_type == 'tic_tac_toe':
            session.data = {
                'board': [' '] * 9,
                'current_player': 'X',
                'moves': 0,
                'winner': None
            }
        elif game_type == 'quiz':
            session.data = {
                'current_question': 0,
                'score': 0,
                'questions': random.sample(self.quiz_questions, 3)
            }
        elif game_type == 'battleship':
            session.data = {
                'player_board': [['~'] * 5 for _ in range(5)],
                'bot_board': [['~'] * 5 for _ in range(5)],
                'bot_ships': self._place_battleship_ships(),
                'player_shots': 0,
                'player_hits': 0,
                'game_status': 'active'
            }
        elif game_type == 'game_2048':
            session.data = {
                'board': [[0] * 4 for _ in range(4)],
                'score': 0,
                'moves': 0,
                'game_status': 'active'
            }
            # Добавляем две начальные плитки
            self._add_random_2048_tile(session.data['board'])
            self._add_random_2048_tile(session.data['board'])
        elif game_type == 'tetris':
            session.data = {
                'board': [[0] * 10 for _ in range(20)],
                'current_piece': self._get_random_tetris_piece(),
                'score': 0,
                'lines_cleared': 0,
                'level': 1,
                'game_status': 'active'
            }
        elif game_type == 'snake':
            session.data = {
                'board': [[0] * 10 for _ in range(10)],
                'snake': [(5, 5)],
                'food': None,
                'direction': 'right',
                'score': 0,
                'game_status': 'active'
            }
            # Размещаем первую еду
            session.data['food'] = self._place_snake_food(session.data['board'], session.data['snake'])

        self.active_sessions[game_id] = session
        self.logger.info(f"Сессия сохранена в active_sessions: {repr(game_id)}, активные сессии: {list(self.active_sessions.keys())}")
        return session

    def get_game_session(self, game_id: str) -> Optional[GameSession]:
        """Получение игровой сессии по ID"""
        self.logger.info(f"Поиск сессии для game_id: {repr(game_id)}, активные сессии: {list(self.active_sessions.keys())}")
        session = self.active_sessions.get(game_id)
        if not session:
            # self.logger.error(f"Сессия не найдена для game_id: {repr(game_id)}, активные сессии: {list(self.active_sessions.keys())}")
            return None
        if session.status != "active":
            self.logger.warning(f"Сессия {repr(game_id)} не активна (status: {session.status})")
            return None
        return session

    def end_game_session(self, game_id: str) -> bool:
        """Завершение игровой сессии"""
        self.logger.info(f"Завершение сессии для game_id: {repr(game_id)}, активные сессии: {list(self.active_sessions.keys())}")
        if game_id in self.active_sessions:
            self.active_sessions[game_id].status = "completed"
            del self.active_sessions[game_id]
            self.logger.info(f"Сессия {repr(game_id)} завершена и удалена")
            return True
        self.logger.warning(f"Сессия {repr(game_id)} не найдена для завершения")
        return False

    def play_rock_paper_scissors(self, game_id: str, player_choice: str) -> Dict[str, Any]:
        """
        Игра в камень-ножницы-бумага.

        Args:
            game_id: ID игровой сессии
            player_choice: Выбор игрока (rock, paper, scissors, или на русском: камень, ножницы, бумага)

        Returns:
            Результат игры
        """
        session = self.get_game_session(game_id)
        if not session or session.game_type != 'rock_paper_scissors':
            raise ValidationError("Игра не найдена или неверный тип игры")

        # Mapping для поддержки русского ввода
        choice_mapping = {
            'камень': 'rock',
            'ножницы': 'scissors',
            'бумага': 'paper',
            'rock': 'rock',
            'paper': 'paper',
            'scissors': 'scissors'
        }

        normalized_choice = choice_mapping.get(player_choice.lower(), player_choice)
        valid_choices = ['rock', 'paper', 'scissors']
        if normalized_choice not in valid_choices:
            raise ValidationError(f"Неверный выбор: {player_choice}. Допустимые: камень, ножницы, бумага или rock, paper, scissors")

        # Определяем выбор бота
        bot_choice = random.choice(valid_choices)

        # Определяем результат
        if normalized_choice == bot_choice:
            result = 'draw'
            points = self.game_settings['rock_paper_scissors']['points_draw']
        elif (normalized_choice == 'rock' and bot_choice == 'scissors') or \
              (normalized_choice == 'paper' and bot_choice == 'rock') or \
              (normalized_choice == 'scissors' and bot_choice == 'paper'):
            result = 'win'
            points = self.game_settings['rock_paper_scissors']['points_win']
        else:
            result = 'lose'
            points = 0

        # Обновляем данные сессии
        session.data.update({
            'player_choice': normalized_choice,
            'bot_choice': bot_choice,
            'result': result
        })

        # Начисляем очки игроку
        if points > 0:
            # Здесь будет вызов score_repository для начисления очков
            pass

        return {
            'result': result,
            'player_choice': normalized_choice,
            'bot_choice': bot_choice,
            'points': points
        }

    def make_tic_tac_toe_move(self, game_id: str, position: int) -> Dict[str, Any]:
        """
        Ход в крестики-нолики.

        Args:
            game_id: ID игровой сессии
            position: Позиция хода (0-8)

        Returns:
            Результат хода
        """
        session = self.get_game_session(game_id)
        if not session or session.game_type != 'tic_tac_toe':
            raise ValidationError("Игра не найдена или неверный тип игры")

        if not (0 <= position <= 8):
            raise ValidationError("Неверная позиция хода")

        board = session.data['board']
        if board[position] != ' ':
            # Клетка уже занята, возвращаем текущее состояние
            return {
                'status': 'already_occupied',
                'board': board,
                'points': 0
            }

        # Ход игрока
        board[position] = 'X'
        session.data['moves'] += 1
        session.data['board'] = board

        # Проверяем победу игрока
        winner = self._check_tic_tac_toe_winner(board)
        if winner:
            session.data['winner'] = 'player'
            points = self.game_settings['tic_tac_toe']['points_win']
            return {
                'status': 'player_win',
                'board': board,
                'winner': 'player',
                'points': points
            }

        # Проверяем ничью
        if session.data['moves'] >= 9:
            session.data['winner'] = 'draw'
            points = self.game_settings['tic_tac_toe']['points_draw']
            return {
                'status': 'draw',
                'board': board,
                'winner': 'draw',
                'points': points
            }

        # Ход бота (простая логика - случайный ход)
        available_moves = [i for i, cell in enumerate(board) if cell == ' ']
        if available_moves:
            bot_position = random.choice(available_moves)
            board[bot_position] = 'O'
            session.data['moves'] += 1
            session.data['board'] = board

            # Проверяем победу бота
            winner = self._check_tic_tac_toe_winner(board)
            if winner:
                session.data['winner'] = 'bot'
                return {
                    'status': 'bot_win',
                    'board': board,
                    'winner': 'bot',
                    'points': 0
                }

        return {
            'status': 'continue',
            'board': board,
            'points': 0
        }

    def answer_quiz_question(self, game_id: str, answer_index: int) -> Dict[str, Any]:
        """
        Ответ на вопрос викторины.

        Args:
            game_id: ID игровой сессии
            answer_index: Индекс ответа

        Returns:
            Результат ответа
        """
        session = self.get_game_session(game_id)
        if not session or session.game_type != 'quiz':
            raise ValidationError("Игра не найдена или неверный тип игры")

        current_q = session.data['current_question']
        questions = session.data['questions']

        if current_q >= len(questions):
            raise ValidationError("Все вопросы отвечены")

        question = questions[current_q]
        if not (0 <= answer_index < len(question['answers'])):
            raise ValidationError("Неверный индекс ответа")

        # Проверяем ответ
        is_correct = (answer_index == question['correct'])

        if is_correct:
            session.data['score'] += self.game_settings['quiz']['points_correct']

        # Переходим к следующему вопросу
        session.data['current_question'] += 1
        current_q += 1

        # Проверяем завершение игры
        if current_q >= len(questions):
            final_score = session.data['score']
            return {
                'status': 'game_over',
                'correct': is_correct,
                'final_score': final_score,
                'points': final_score
            }

        return {
            'status': 'continue',
            'correct': is_correct,
            'current_score': session.data['score']
        }

    def _check_tic_tac_toe_winner(self, board: List[str]) -> Optional[str]:
        """Проверка победителя в крестики-нолики"""
        # Проверяем строки
        for i in range(0, 9, 3):
            if board[i] == board[i+1] == board[i+2] != ' ':
                return board[i]

        # Проверяем столбцы
        for i in range(3):
            if board[i] == board[i+3] == board[i+6] != ' ':
                return board[i]

        # Проверяем диагонали
        if board[0] == board[4] == board[8] != ' ':
            return board[0]
        if board[2] == board[4] == board[6] != ' ':
            return board[2]

        return None

    def get_game_statistics(self, user_id: int) -> Dict[str, Any]:
        """Получение игровой статистики пользователя"""
        # Здесь будет получение статистики из базы данных
        return {
            'games_played': 0,
            'games_won': 0,
            'games_lost': 0,
            'total_points': 0,
            'favorite_game': None
        }

    # ===== МОРСКОЙ БОЙ =====

    def make_battleship_shot(self, game_id: str, row: int, col: int) -> Dict[str, Any]:
        """Ход в морском бое"""
        session = self.get_game_session(game_id)
        if not session or session.game_type != 'battleship':
            raise ValidationError("Игра не найдена или неверный тип игры")

        data = session.data
        bot_board = data['bot_board']
        bot_ships = data['bot_ships']

        if not (0 <= row < 5 and 0 <= col < 5):
            raise ValidationError("Неверные координаты")

        if bot_board[row][col] != '~':
            # Уже стреляли, возвращаем текущее состояние
            return {
                'status': 'already_shot',
                'board': bot_board,
                'hit': False,
                'shots': data['player_shots'],
                'points': 0
            }

        # Определяем попадание
        hit = False
        for ship in bot_ships:
            if (row, col) in ship:
                hit = True
                bot_board[row][col] = '💥'
                data['player_hits'] += 1
                break

        if not hit:
            bot_board[row][col] = '💧'

        data['player_shots'] += 1
        session.data = data

        # Проверяем победу
        total_ship_cells = sum(len(ship) for ship in bot_ships)
        if data['player_hits'] >= total_ship_cells:
            data['game_status'] = 'won'
            return {
                'status': 'win',
                'board': bot_board,
                'hit': hit,
                'shots': data['player_shots'],
                'points': self.game_settings['battleship']['points_win']
            }

        return {
            'status': 'continue',
            'board': bot_board,
            'hit': hit,
            'shots': data['player_shots'],
            'points': 0
        }

    def _place_battleship_ships(self) -> List[List[Tuple[int, int]]]:
        """Размещение кораблей бота"""
        ships = []
        ship_sizes = self.game_settings['battleship']['ships'].copy()

        for size in ship_sizes:
            placed = False
            attempts = 0
            while not placed and attempts < 100:
                direction = random.randint(0, 1)  # 0 - горизонтально, 1 - вертикально
                if direction == 0:
                    row = random.randint(0, 4)
                    col = random.randint(0, 4 - size)
                    ship_coords = [(row, col + i) for i in range(size)]
                else:
                    row = random.randint(0, 4 - size)
                    col = random.randint(0, 4)
                    ship_coords = [(row + i, col) for i in range(size)]

                # Проверяем пересечения
                if not any(coord in [c for ship in ships for c in ship] for coord in ship_coords):
                    ships.append(ship_coords)
                    placed = True
                attempts += 1

        return ships

    # ===== ИГРА 2048 =====

    def make_2048_move(self, game_id: str, direction: str) -> Dict[str, Any]:
        """Ход в игре 2048"""
        session = self.get_game_session(game_id)
        if not session or session.game_type != 'game_2048':
            raise ValidationError("Игра не найдена или неверный тип игры")

        data = session.data
        board = data['board']

        valid_directions = ['left', 'right', 'up', 'down']
        if direction not in valid_directions:
            raise ValidationError(f"Неверное направление: {direction}")

        # Сохраняем доску для сравнения
        old_board = [row[:] for row in board]

        # Делаем ход
        moved, score_gained = self._move_2048_board(board, direction)
        data['score'] += score_gained
        data['moves'] += 1

        if moved:
            self._add_random_2048_tile(board)

        # Проверяем победу
        if self._check_2048_win(board):
            data['game_status'] = 'won'
            return {
                'status': 'win',
                'board': board,
                'score': data['score'],
                'moved': moved,
                'points': self.game_settings['game_2048']['points_win']
            }

        # Проверяем поражение
        if not self._can_move_2048(board):
            data['game_status'] = 'lost'
            return {
                'status': 'lose',
                'board': board,
                'score': data['score'],
                'moved': moved,
                'points': 0
            }

        return {
            'status': 'continue',
            'board': board,
            'score': data['score'],
            'moved': moved,
            'moves': data['moves'],
            'points': 0
        }

    def _move_2048_board(self, board: List[List[int]], direction: str) -> Tuple[bool, int]:
        """Движение доски 2048"""
        def move_row_left(row):
            new_row = [num for num in row if num != 0]
            score = 0
            for i in range(len(new_row) - 1):
                if new_row[i] == new_row[i + 1]:
                    new_row[i] *= 2
                    score += new_row[i]
                    new_row[i + 1] = 0
            new_row = [num for num in new_row if num != 0]
            return new_row + [0] * (4 - len(new_row)), score

        moved = False
        total_score = 0

        if direction == 'left':
            for i in range(4):
                old_row = board[i][:]
                board[i], score = move_row_left(board[i])
                if board[i] != old_row:
                    moved = True
                total_score += score
        elif direction == 'right':
            for i in range(4):
                old_row = board[i][::-1]
                new_row, score = move_row_left(old_row)
                board[i] = new_row[::-1]
                if board[i] != old_row[::-1]:
                    moved = True
                total_score += score
        elif direction == 'up':
            for j in range(4):
                col = [board[i][j] for i in range(4)]
                old_col = col[:]
                new_col, score = move_row_left(col)
                for i in range(4):
                    board[i][j] = new_col[i]
                if new_col != old_col:
                    moved = True
                total_score += score
        elif direction == 'down':
            for j in range(4):
                col = [board[i][j] for i in range(3, -1, -1)]
                old_col = col[:]
                new_col, score = move_row_left(col)
                for i in range(3, -1, -1):
                    board[3 - i][j] = new_col[i]
                if new_col != old_col:
                    moved = True
                total_score += score

        return moved, total_score

    def _add_random_2048_tile(self, board: List[List[int]]):
        """Добавление случайной плитки"""
        empty_cells = [(i, j) for i in range(4) for j in range(4) if board[i][j] == 0]
        if empty_cells:
            i, j = random.choice(empty_cells)
            board[i][j] = 2 if random.random() < 0.9 else 4

    def _check_2048_win(self, board: List[List[int]]) -> bool:
        """Проверка победы в 2048"""
        return any(2048 in row for row in board)

    def _can_move_2048(self, board: List[List[int]]) -> bool:
        """Проверка возможности хода"""
        for i in range(4):
            for j in range(4):
                if board[i][j] == 0:
                    return True
                if i > 0 and board[i][j] == board[i-1][j]:
                    return True
                if j > 0 and board[i][j] == board[i][j-1]:
                    return True
        return False

    # ===== ТЕТРИС =====

    def make_tetris_move(self, game_id: str, action: str) -> Dict[str, Any]:
        """Ход в тетрисе"""
        session = self.get_game_session(game_id)
        if not session or session.game_type != 'tetris':
            raise ValidationError("Игра не найдена или неверный тип игры")

        data = session.data
        board = data['board']
        piece = data['current_piece']

        if action == 'left' and piece['x'] > 0:
            piece['x'] -= 1
            if not self._is_valid_tetris_position(board, piece):
                piece['x'] += 1
        elif action == 'right' and piece['x'] < 10 - len(piece['shape'][0]):
            piece['x'] += 1
            if not self._is_valid_tetris_position(board, piece):
                piece['x'] -= 1
        elif action == 'down':
            piece['y'] += 1
            if not self._is_valid_tetris_position(board, piece):
                piece['y'] -= 1
                # Фиксируем фигуру
                self._place_tetris_piece(board, piece)
                lines_cleared = self._clear_tetris_lines(board)
                data['score'] += lines_cleared * self.game_settings['tetris']['points_per_line']
                data['lines_cleared'] += lines_cleared

                # Создаем новую фигуру
                piece = self._get_random_tetris_piece()
                if not self._is_valid_tetris_position(board, piece):
                    data['game_status'] = 'game_over'
                    return {
                        'status': 'game_over',
                        'board': board,
                        'score': data['score'],
                        'lines_cleared': data['lines_cleared'],
                        'points': 0
                    }
                data['current_piece'] = piece
        elif action == 'rotate':
            old_shape = piece['shape'][:]
            piece['shape'] = list(zip(*piece['shape'][::-1]))
            if not self._is_valid_tetris_position(board, piece):
                piece['shape'] = old_shape

        return {
            'status': 'continue',
            'board': board,
            'piece': piece,
            'score': data['score'],
            'lines_cleared': data['lines_cleared'],
            'level': data['level'],
            'points': 0
        }

    def _is_valid_tetris_position(self, board: List[List[int]], piece: Dict) -> bool:
        """Проверка валидности позиции тетрис-фигуры"""
        for i, row in enumerate(piece['shape']):
            for j, cell in enumerate(row):
                if cell:
                    x, y = piece['x'] + j, piece['y'] + i
                    if x < 0 or x >= 10 or y >= 20 or (y >= 0 and board[y][x] != 0):
                        return False
        return True

    def _place_tetris_piece(self, board: List[List[int]], piece: Dict):
        """Размещение тетрис-фигуры на доске"""
        for i, row in enumerate(piece['shape']):
            for j, cell in enumerate(row):
                if cell:
                    x, y = piece['x'] + j, piece['y'] + i
                    if 0 <= y < 20 and 0 <= x < 10:
                        board[y][x] = 1

    def _clear_tetris_lines(self, board: List[List[int]]) -> int:
        """Очистка заполненных линий"""
        lines_cleared = 0
        y = 19
        while y >= 0:
            if all(board[y]):
                del board[y]
                board.insert(0, [0] * 10)
                lines_cleared += 1
            else:
                y -= 1
        return lines_cleared

    def _get_random_tetris_piece(self) -> Dict:
        """Получение случайной тетрис-фигуры"""
        pieces = [
            {'shape': [[1, 1, 1, 1]], 'x': 3, 'y': 0},  # I
            {'shape': [[1, 1], [1, 1]], 'x': 4, 'y': 0},  # O
            {'shape': [[1, 0, 0], [1, 1, 1]], 'x': 3, 'y': 0},  # J
            {'shape': [[0, 0, 1], [1, 1, 1]], 'x': 3, 'y': 0},  # L
            {'shape': [[0, 1, 1], [1, 1, 0]], 'x': 3, 'y': 0},  # S
            {'shape': [[1, 1, 0], [0, 1, 1]], 'x': 3, 'y': 0},  # Z
            {'shape': [[0, 1, 0], [1, 1, 1]], 'x': 3, 'y': 0},  # T
        ]
        return random.choice(pieces)

    # ===== ЗМЕЙКА =====

    def make_snake_move(self, game_id: str, direction: str) -> Dict[str, Any]:
        """Ход в змейке"""
        session = self.get_game_session(game_id)
        if not session or session.game_type != 'snake':
            raise ValidationError("Игра не найдена или неверный тип игры")

        data = session.data
        snake = data['snake']
        food = data['food']
        current_direction = data['direction']

        # Проверяем допустимость направления
        opposites = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        if direction == opposites.get(current_direction):
            raise ValidationError("Нельзя двигаться в противоположном направлении")

        # Вычисляем новую голову
        head = snake[0]
        if direction == 'up':
            new_head = (head[0] - 1, head[1])
        elif direction == 'down':
            new_head = (head[0] + 1, head[1])
        elif direction == 'left':
            new_head = (head[0], head[1] - 1)
        elif direction == 'right':
            new_head = (head[0], head[1] + 1)
        else:
            raise ValidationError(f"Неверное направление: {direction}")

        # Проверяем столкновения
        if (new_head[0] < 0 or new_head[0] >= 10 or
            new_head[1] < 0 or new_head[1] >= 10 or
            new_head in snake):
            data['game_status'] = 'game_over'
            return {
                'status': 'game_over',
                'snake': snake,
                'food': food,
                'score': data['score'],
                'length': len(snake),
                'points': 0
            }

        # Добавляем новую голову
        snake.insert(0, new_head)
        data['direction'] = direction

        # Проверяем еду
        if new_head == food:
            data['score'] += self.game_settings['snake']['points_per_food']
            food = self._place_snake_food(data['board'], snake)
            data['food'] = food
        else:
            # Удаляем хвост если не съели еду
            snake.pop()

        return {
            'status': 'continue',
            'snake': snake,
            'food': food,
            'score': data['score'],
            'length': len(snake),
            'points': 0
        }

    def _place_snake_food(self, board: List[List[int]], snake: List[Tuple[int, int]]) -> Tuple[int, int]:
        """Размещение еды для змейки"""
        empty_cells = [(i, j) for i in range(10) for j in range(10) if (i, j) not in snake]
        if empty_cells:
            return random.choice(empty_cells)
        return None

    def cleanup_old_sessions(self, max_age_minutes: int = 30):
        """Очистка старых игровых сессий"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=max_age_minutes)

        to_remove = []
        for game_id, session in self.active_sessions.items():
            if session.created_at < cutoff_time:
                to_remove.append(game_id)

        for game_id in to_remove:
            del self.active_sessions[game_id]
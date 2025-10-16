import logging
import random
import requests
import os
import asyncio
import tempfile
import subprocess
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, InlineQueryHandler, ChatMemberHandler
from database_sqlite import Database
from config_local import BOT_TOKEN, OPENWEATHER_API_KEY, NEWS_API_KEY, ADMIN_IDS
from messages import *

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
    print("[+] Speech recognition library loaded successfully")
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("[-] Speech recognition library not available")
    print("  To install: pip install SpeechRecognition")
    print("  Alternative: pip install speech_recognition")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
    print("[+] Pydub library loaded successfully")
except ImportError:
    PYDUB_AVAILABLE = False
    print("[-] Pydub library not available")
    print("  To install: pip install pydub")

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
        # Система отслеживания приветственных сообщений
        self.welcome_messages = {}  # {chat_id: {'message_id': int, 'timestamp': datetime}}
        self.cleanup_task = None

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
        self.application.add_handler(CommandHandler("donate", self.donate))
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
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
        self.application.add_handler(ChatMemberHandler(self.handle_new_chat_members, ChatMemberHandler.CHAT_MEMBER))

        # Инлайновые запросы
        self.application.add_handler(InlineQueryHandler(self.handle_inline_query))

        # Callback queries для игр
        from telegram.ext import CallbackQueryHandler
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    def start_cleanup_task(self):
        """Запуск задачи очистки приветственных сообщений"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self.cleanup_welcome_messages())

    async def cleanup_welcome_messages(self):
        """Периодическая очистка устаревших приветственных сообщений"""
        while True:
            try:
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
                await self.delete_expired_welcome_messages()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Ошибка при очистке приветственных сообщений: {e}")

    async def delete_expired_welcome_messages(self):
        """Удаление просроченных приветственных сообщений"""
        current_time = datetime.now()
        expired_chats = []

        for chat_id, message_info in self.welcome_messages.items():
            message_time = message_info['timestamp']
            if current_time - message_time > timedelta(minutes=2):
                try:
                    await self.application.bot.delete_message(chat_id, message_info['message_id'])
                    expired_chats.append(chat_id)
                except Exception as e:
                    print(f"Не удалось удалить приветственное сообщение в чате {chat_id}: {e}")
                    expired_chats.append(chat_id)

        # Удаляем записи о просроченных сообщениях
        for chat_id in expired_chats:
            self.welcome_messages.pop(chat_id, None)

    async def delete_welcome_message(self, chat_id):
        """Удаление приветственного сообщения для конкретного чата"""
        if chat_id in self.welcome_messages:
            try:
                message_info = self.welcome_messages[chat_id]
                await self.application.bot.delete_message(chat_id, message_info['message_id'])
            except Exception as e:
                print(f"Не удалось удалить приветственное сообщение в чате {chat_id}: {e}")
            finally:
                self.welcome_messages.pop(chat_id, None)

    async def set_welcome_message(self, chat_id, message_id):
        """Сохранение информации о приветственном сообщении"""
        self.welcome_messages[chat_id] = {
            'message_id': message_id,
            'timestamp': datetime.now()
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        # Запускаем задачу очистки приветственных сообщений при первом использовании
        if self.cleanup_task is None or self.cleanup_task.done():
            self.start_cleanup_task()

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
                achievements = db.get_user_achievements(target_user_id)
                total_donations = db.get_total_donations(target_user_id)
                if user_info:
                    # Формируем строку значков
                    badge_str = ""
                    for achievement_type, _ in achievements:
                        if achievement_type in ACHIEVEMENT_BADGES:
                            badge_str += ACHIEVEMENT_BADGES[achievement_type] + " "

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
{f"🏆 Достижения: {badge_str.strip()}" if badge_str else ""}
{f"💰 Всего донатов: {total_donations} RUB" if total_donations > 0 else ""}
                    """
                else:
                    info_text = f"Пользователь с ID {target_user_id} не найден."
            except ValueError:
                info_text = f"Неверный формат ID пользователя: {target_user}"
        else:
            # Обычный пользователь запрашивает свою информацию
            db.add_user(user.id, user.username, user.first_name, user.last_name)
            user_info = db.get_user_info(user.id)
            achievements = db.get_user_achievements(user.id)
            total_donations = db.get_total_donations(user.id)

            if user_info:
                # Формируем строку значков
                badge_str = ""
                achievement_list = []
                for achievement_type, unlocked_at in achievements:
                    if achievement_type in ACHIEVEMENT_BADGES:
                        badge_str += ACHIEVEMENT_BADGES[achievement_type] + " "
                        achievement_list.append(f"{ACHIEVEMENT_BADGES[achievement_type]} {achievement_type.replace('_', ' ').title()}")

                # Создаем список достижений отдельно
                achievements_text = ""
                if achievement_list:
                    achievements_text = f"\n📋 Список достижений:\n" + '\n'.join(achievement_list)

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
{f"🏆 Достижения: {badge_str.strip()}" if badge_str else ""}
{f"💰 Всего донатов: {total_donations} RUB" if total_donations > 0 else ""}
{achievements_text}
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

        # Валидация города
        if not city or len(city.strip()) < 2:
            await update.message.reply_text("❌ Название города должно содержать минимум 2 символа")
            return

        # Ограничиваем длину названия города для безопасности
        if len(city) > 50:
            await update.message.reply_text("❌ Название города слишком длинное (максимум 50 символов)")
            return

        try:
            # Добавляем таймаут для запроса
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"

            # Создаем сессию с таймаутом
            import requests
            response = requests.get(url, timeout=10)

            # Проверяем статус код
            if response.status_code == 401:
                await update.message.reply_text("❌ Ошибка API: неверный ключ погоды")
                return
            elif response.status_code == 429:
                await update.message.reply_text("❌ Превышен лимит запросов к API погоды. Попробуйте позже.")
                return
            elif response.status_code >= 500:
                await update.message.reply_text("❌ Сервер погоды временно недоступен. Попробуйте позже.")
                return
            elif response.status_code != 200:
                await update.message.reply_text("❌ Ошибка при получении данных о погоде")
                return

            data = response.json()

            if data.get('cod') == 200:
                # Проверяем, что все необходимые данные присутствуют
                if 'name' not in data or 'main' not in data or 'weather' not in data:
                    await update.message.reply_text("❌ Неполные данные о погоде от сервера")
                    return

                weather_text = WEATHER_MESSAGES['weather_info'].format(
                    city=data['name'],
                    temp=data['main']['temp'],
                    feels_like=data['main']['feels_like'],
                    humidity=data['main']['humidity'],
                    description=data['weather'][0]['description']
                )
                await update.message.reply_text(weather_text, parse_mode='HTML')
            else:
                # Обработка различных кодов ошибок от API
                if data.get('cod') == '404':
                    await update.message.reply_text(f"❌ Город '{city}' не найден")
                elif data.get('cod') == '401':
                    await update.message.reply_text("❌ Ошибка авторизации API погоды")
                else:
                    await update.message.reply_text(f"❌ Ошибка API погоды: {data.get('message', 'Неизвестная ошибка')}")

        except requests.exceptions.Timeout:
            await update.message.reply_text("❌ Превышено время ожидания ответа от сервера погоды. Попробуйте позже.")
        except requests.exceptions.ConnectionError:
            await update.message.reply_text("❌ Ошибка подключения к серверу погоды. Проверьте интернет-соединение.")
        except requests.exceptions.RequestException as e:
            await update.message.reply_text(f"❌ Ошибка сети при получении погоды: {str(e)[:100]}")
        except (KeyError, ValueError, TypeError) as e:
            await update.message.reply_text(f"❌ Ошибка обработки данных погоды: {str(e)[:100]}")
        except Exception as e:
            print(f"Неожиданная ошибка в weather: {e}")
            await update.message.reply_text("❌ Неожиданная ошибка при получении погоды. Попробуйте позже.")

    async def news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получить новости"""
        if not NEWS_API_KEY:
            await update.message.reply_text(NEWS_MESSAGES['no_api_key'])
            return

        try:
            # Добавляем таймаут для запроса
            url = f"https://newsapi.org/v2/top-headlines?country=ru&apiKey={NEWS_API_KEY}"

            # Создаем сессию с таймаутом
            response = requests.get(url, timeout=10)

            # Проверяем статус код
            if response.status_code == 401:
                await update.message.reply_text("❌ Ошибка API: неверный ключ новостей")
                return
            elif response.status_code == 429:
                await update.message.reply_text("❌ Превышен лимит запросов к API новостей. Попробуйте позже.")
                return
            elif response.status_code >= 500:
                await update.message.reply_text("❌ Сервер новостей временно недоступен. Попробуйте позже.")
                return
            elif response.status_code != 200:
                await update.message.reply_text("❌ Ошибка при получении новостей")
                return

            data = response.json()

            if data.get('status') == 'ok' and data.get('articles'):
                # Проверяем, что статьи содержат необходимые поля
                articles = data['articles'][:5]  # Берем только первые 5
                valid_articles = []

                for article in articles:
                    if article.get('title') and article.get('url'):
                        valid_articles.append(article)

                if not valid_articles:
                    await update.message.reply_text("❌ Новости получены, но не содержат корректных данных")
                    return

                news_text = NEWS_MESSAGES['news_title']
                for i, article in enumerate(valid_articles, 1):
                    # Ограничиваем длину заголовка для безопасности
                    title = article['title'][:200] if len(article['title']) > 200 else article['title']
                    url = article['url'][:500] if len(article['url']) > 500 else article['url']  # Ограничиваем URL
                    news_text += f"{i}. {title}\n{url}\n\n"

                # Ограничиваем общую длину сообщения
                if len(news_text) > 4000:
                    news_text = news_text[:3997] + "..."

                await update.message.reply_text(news_text, parse_mode='HTML')
            else:
                # Обработка различных ошибок от API
                if data.get('status') == 'error':
                    error_code = data.get('code', 'unknown')
                    error_message = data.get('message', 'Неизвестная ошибка')

                    if error_code == 'apiKeyInvalid':
                        await update.message.reply_text("❌ Ошибка API: неверный ключ новостей")
                    elif error_code == 'rateLimited':
                        await update.message.reply_text("❌ Превышен лимит запросов к API новостей")
                    elif error_code == 'sourcesUnavailable':
                        await update.message.reply_text("❌ Источники новостей недоступны")
                    else:
                        await update.message.reply_text(f"❌ Ошибка API новостей: {error_message}")
                else:
                    await update.message.reply_text(NEWS_MESSAGES['news_not_found'])

        except requests.exceptions.Timeout:
            await update.message.reply_text("❌ Превышено время ожидания ответа от сервера новостей. Попробуйте позже.")
        except requests.exceptions.ConnectionError:
            await update.message.reply_text("❌ Ошибка подключения к серверу новостей. Проверьте интернет-соединение.")
        except requests.exceptions.RequestException as e:
            await update.message.reply_text(f"❌ Ошибка сети при получении новостей: {str(e)[:100]}")
        except (KeyError, ValueError, TypeError) as e:
            await update.message.reply_text(f"❌ Ошибка обработки данных новостей: {str(e)[:100]}")
        except Exception as e:
            print(f"Неожиданная ошибка в news: {e}")
            await update.message.reply_text("❌ Неожиданная ошибка при получении новостей. Попробуйте позже.")

    async def translate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перевод текста"""
        if len(context.args) < 2:
            await update.message.reply_text(TRANSLATE_MESSAGES['usage'])
            return

        text = ' '.join(context.args[:-1])
        target_lang = context.args[-1]

        # Валидация входных данных
        if not text or not text.strip():
            await update.message.reply_text("❌ Текст для перевода не может быть пустым")
            return

        if not target_lang or len(target_lang) != 2:
            await update.message.reply_text("❌ Укажите правильный код языка (например: en, ru, de)")
            return

        # Ограничиваем длину текста для безопасности и производительности
        if len(text) > 1000:
            await update.message.reply_text("❌ Текст слишком длинный для перевода (максимум 1000 символов)")
            return

        # Простой перевод с помощью Google Translate API (нужен API ключ)
        try:
            # В реальном проекте используйте Google Translate API или другой сервис
            # Заглушка для демонстрации - в продакшене нужно реализовать реальный перевод
            await update.message.reply_text(
                f"🔄 Функция перевода: '{text[:50]}{'...' if len(text) > 50 else ''}' на {target_lang}\n\n"
                f"💡 В текущей версии бота перевод недоступен. Интегрируйте Google Translate API или другой сервис перевода."
            )
        except Exception as e:
            print(f"Ошибка в translate: {e}")
            await update.message.reply_text("❌ Ошибка при переводе текста. Попробуйте позже.")

    async def play_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запустить мини-игру"""
        keyboard = [
            [InlineKeyboardButton("Камень-ножницы-бумага", callback_data='game_rps')],
            [InlineKeyboardButton("Крестики-нолики", callback_data='game_tic_tac_toe')],
            [InlineKeyboardButton("Викторина", callback_data='game_quiz')],
            [InlineKeyboardButton("Морской бой", callback_data='game_battleship')],
            [InlineKeyboardButton("2048", callback_data='game_2048')],
            [InlineKeyboardButton("Тетрис", callback_data='game_tetris')],
            [InlineKeyboardButton("Змейка", callback_data='game_snake')],
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
        elif query.data == 'game_2048':
            await self.start_2048_game(query, context)
        elif query.data == 'game_tetris':
            await self.start_tetris_game(query, context)
        elif query.data == 'game_snake':
            await self.start_snake_game(query, context)
        elif query.data.startswith('bs_'):
            await self.handle_battleship_shot(query, context)
        elif query.data.startswith('2048_'):
            await self.handle_2048_move(query, context)
        elif query.data.startswith('tetris_'):
            await self.handle_tetris_move(query, context)
        elif query.data.startswith('snake_'):
            await self.handle_snake_move(query, context)
        elif query.data.startswith('rps_'):
            await self.handle_rps(query, context)
        elif query.data.startswith('tictactoe_'):
            await self.handle_tic_tac_toe_move(query, context)
        elif query.data.startswith('quiz_'):
            await self.handle_quiz_answer(query, context)
        elif query.data.startswith('confirm_schedule_'):
            await self.confirm_schedule_post(query, context)
        elif query.data == 'edit_text':
            await self.edit_schedule_text(query, context)
        elif query.data == 'add_image':
            await self.add_schedule_image(query, context)
        elif query.data == 'cancel_schedule':
            await self.cancel_schedule_post(query, context)
        elif query.data.startswith('donate_'):
            await self.handle_donation_callback(query, context)


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

        user_id_str = context.args[0]
        reason = ' '.join(context.args[1:])

        # Валидация ID пользователя
        try:
            user_id = int(user_id_str)
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя. Должен быть числом.")
            return

        # Валидация причины
        if not reason or not reason.strip():
            await update.message.reply_text("❌ Укажите причину бана")
            return

        if len(reason) > 500:
            await update.message.reply_text("❌ Причина слишком длинная (максимум 500 символов)")
            return

        # Проверка, что пользователь не пытается забанить себя
        if user_id == update.effective_user.id:
            await update.message.reply_text("❌ Вы не можете забанить самого себя")
            return

        # Проверка, что пользователь не пытается забанить бота
        if user_id == context.bot.id:
            await update.message.reply_text("❌ Вы не можете забанить бота")
            return

        try:
            await update.effective_chat.ban_member(user_id)
            await update.message.reply_text(MODERATION_MESSAGES['user_banned'].format(user_id=user_id, reason=reason))
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при бане пользователя: {str(e)[:100]}")

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

        user_id_str = context.args[0]
        time_str = context.args[1]

        # Валидация ID пользователя
        try:
            user_id = int(user_id_str)
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя. Должен быть числом.")
            return

        # Валидация времени
        try:
            mute_time = int(time_str)
        except ValueError:
            await update.message.reply_text("❌ Время должно быть числом в секундах.")
            return

        # Проверка диапазона времени
        if mute_time < 1:
            await update.message.reply_text("❌ Время должно быть положительным числом.")
            return

        if mute_time > 365 * 24 * 3600:  # Максимум 1 год
            await update.message.reply_text("❌ Время не может превышать 1 год (31536000 секунд).")
            return

        # Проверка, что пользователь не пытается заглушить себя
        if user_id == update.effective_user.id:
            await update.message.reply_text("❌ Вы не можете заглушить самого себя")
            return

        # Проверка, что пользователь не пытается заглушить бота
        if user_id == context.bot.id:
            await update.message.reply_text("❌ Вы не можете заглушить бота")
            return

        from datetime import datetime, timedelta
        until_date = datetime.now() + timedelta(seconds=mute_time)

        try:
            await update.effective_chat.restrict_member(
                user_id,
                until_date=until_date,
                can_send_messages=False
            )
            await update.message.reply_text(MODERATION_MESSAGES['user_muted'].format(user_id=user_id, time=mute_time))
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при заглушке пользователя: {str(e)[:100]}")

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

        user_id_str = context.args[0]
        reason = ' '.join(context.args[1:])

        # Валидация ID пользователя
        try:
            user_id = int(user_id_str)
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя. Должен быть числом.")
            return

        # Валидация причины
        if not reason or not reason.strip():
            await update.message.reply_text("❌ Укажите причину кика")
            return

        if len(reason) > 500:
            await update.message.reply_text("❌ Причина слишком длинная (максимум 500 символов)")
            return

        # Проверка, что пользователь не пытается кикнуть себя
        if user_id == update.effective_user.id:
            await update.message.reply_text("❌ Вы не можете кикнуть самого себя")
            return

        # Проверка, что пользователь не пытается кикнуть бота
        if user_id == context.bot.id:
            await update.message.reply_text("❌ Вы не можете кикнуть бота")
            return

        try:
            await update.effective_chat.ban_member(user_id)
            await update.effective_chat.unban_member(user_id)  # Разбан сразу после бана = кик
            await update.message.reply_text(MODERATION_MESSAGES['user_kicked'].format(user_id=user_id, reason=reason))
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при кике пользователя: {str(e)[:100]}")

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

        user_id_str = context.args[0]
        reason = ' '.join(context.args[1:])

        # Валидация ID пользователя
        try:
            user_id = int(user_id_str)
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя. Должен быть числом.")
            return

        # Валидация причины
        if not reason or not reason.strip():
            await update.message.reply_text("❌ Укажите причину предупреждения")
            return

        if len(reason) > 500:
            await update.message.reply_text("❌ Причина слишком длинная (максимум 500 символов)")
            return

        # Проверка, что пользователь не пытается выдать предупреждение себе
        if user_id == update.effective_user.id:
            await update.message.reply_text("❌ Вы не можете выдать предупреждение самому себе")
            return

        # Проверка, что пользователь не пытается выдать предупреждение боту
        if user_id == context.bot.id:
            await update.message.reply_text("❌ Вы не можете выдать предупреждение боту")
            return

        try:
            db.add_warning(user_id, reason, update.effective_user.id)
            await update.message.reply_text(MODERATION_MESSAGES['warning_issued'].format(user_id=user_id, reason=reason))
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при выдаче предупреждения: {str(e)[:100]}")

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

        # Валидация имени файла
        if not csv_file or not csv_file.strip():
            await update.message.reply_text("❌ Укажите имя CSV файла")
            return

        # Проверка на потенциально опасные символы в имени файла
        import re
        if not re.match(r'^[a-zA-Z0-9._\-/\s]+$', csv_file):
            await update.message.reply_text("❌ Имя файла содержит недопустимые символы")
            return

        # Ограничение длины имени файла
        if len(csv_file) > 255:
            await update.message.reply_text("❌ Имя файла слишком длинное (максимум 255 символов)")
            return

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

        # Парсинг времени и текста - исправляем обработку аргументов
        args = context.args if hasattr(context, 'args') else []
        if not args:
            await update.message.reply_text(SCHEDULER_MESSAGES['usage_schedule'])
            return

        time_str = args[0]
        text = ' '.join(args[1:])

        # Валидация текста поста
        if not text or not text.strip():
            await update.message.reply_text("❌ Текст поста не может быть пустым")
            return

        if len(text) > 4000:
            await update.message.reply_text("❌ Текст поста слишком длинный (максимум 4000 символов)")
            return

        # Валидация времени
        if not time_str or not time_str.strip():
            await update.message.reply_text("❌ Укажите время публикации")
            return

        if len(time_str) > 100:
            await update.message.reply_text("❌ Строка времени слишком длинная")
            return

        try:
            schedule_time = self.parse_schedule_time(time_str)
        except ValueError as e:
            await update.message.reply_text(f"❌ Ошибка формата времени: {str(e)[:100]}")
            return

        if schedule_time <= datetime.now():
            await update.message.reply_text(SCHEDULER_MESSAGES['time_in_past'])
            return

        # Проверка, что время не слишком далеко в будущем (максимум 1 год)
        max_future_time = datetime.now() + timedelta(days=365)
        if schedule_time > max_future_time:
            await update.message.reply_text("❌ Время публикации не может быть больше чем через 1 год")
            return

        # Показываем предварительный просмотр поста
        preview_text = f"""
📝 <b>Предварительный просмотр поста:</b>

📅 <b>Время публикации:</b> {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}

📋 <b>Текст поста:</b>
{text}

❓ Что вы хотите сделать?
        """

        keyboard = [
            [InlineKeyboardButton("✅ Опубликовать сейчас", callback_data=f'confirm_schedule_{schedule_time.strftime("%Y%m%d_%H%M%S")}_{len(text)}')],
            [InlineKeyboardButton("📝 Изменить текст", callback_data='edit_text')],
            [InlineKeyboardButton("🖼 Добавить картинку", callback_data='add_image')],
            [InlineKeyboardButton("❌ Отменить", callback_data='cancel_schedule')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Сохраняем данные для подтверждения в user_data
        context.user_data['schedule_draft'] = {
            'time_str': time_str,
            'text': text,
            'schedule_time': schedule_time,
            'chat_id': update.effective_chat.id,
            'created_by': user.id
        }

        await update.message.reply_text(preview_text, parse_mode='HTML', reply_markup=reply_markup)

    async def list_posts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список запланированных постов"""
        user = update.effective_user

        # Проверка прав администратора
        if not await self.is_admin(update.effective_chat, user.id):
            await update.message.reply_text(SCHEDULER_MESSAGES['no_permission_view'])
            return

        posts = db.get_scheduled_posts(chat_id=update.effective_chat.id)
        print(f"DEBUG: Found {len(posts)} posts for chat {update.effective_chat.id}")  # Отладочная информация

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

        post_id_str = context.args[0]

        # Валидация ID поста
        try:
            post_id = int(post_id_str)
        except ValueError:
            await update.message.reply_text("❌ ID поста должен быть числом")
            return

        # Проверка диапазона ID
        if post_id < 1:
            await update.message.reply_text("❌ ID поста должен быть положительным числом")
            return

        if post_id > 999999999:  # Разумный максимум для SQLite
            await update.message.reply_text("❌ ID поста слишком большой")
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

        post_id_str = context.args[0]

        # Валидация ID поста
        try:
            post_id = int(post_id_str)
        except ValueError:
            await update.message.reply_text("❌ ID поста должен быть числом")
            return

        # Проверка диапазона ID
        if post_id < 1:
            await update.message.reply_text("❌ ID поста должен быть положительным числом")
            return

        if post_id > 999999999:  # Разумный максимум для SQLite
            await update.message.reply_text("❌ ID поста слишком большой")
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
        # Сначала проверяем по списку ADMIN_IDS
        if user_id in ADMIN_IDS:
            return True

        # Затем проверяем статус в чате
        try:
            member = await chat.get_member(user_id)
            return member.status in ['administrator', 'creator']
        except:
            return False

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user

        # Проверяем, ждет ли пользователь редактирования текста поста
        if context.user_data.get('waiting_for_text_edit'):
            await self.handle_text_edit(update, context)
            return

        # Проверяем, ждет ли пользователь ввода суммы доната
        if context.user_data.get('waiting_for_donation_amount'):
            await self.handle_donation_amount_input(update, context)
            return

        message_text = update.message.text.lower()

        # Автофильтр нецензурной лексики
        if self.check_profanity(message_text):
            await self.handle_profanity_violation(update, user)
            return

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

    async def handle_text_edit(self, update, context):
        """Обработка редактирования текста поста"""
        new_text = update.message.text

        draft = context.user_data.get('schedule_draft')
        if draft:
            draft['text'] = new_text
            context.user_data['schedule_draft'] = draft

            # Показываем обновленный предварительный просмотр
            preview_text = f"""
📝 <b>Текст обновлен! Предварительный просмотр:</b>

📅 <b>Время публикации:</b> {draft['schedule_time'].strftime('%Y-%m-%d %H:%M:%S')}

📋 <b>Новый текст поста:</b>
{new_text}

❓ Что вы хотите сделать?
            """

            keyboard = [
                [InlineKeyboardButton("✅ Опубликовать сейчас", callback_data=f'confirm_schedule_{draft["schedule_time"].strftime("%Y%m%d_%H%M%S")}_{len(new_text)}')],
                [InlineKeyboardButton("📝 Изменить текст еще раз", callback_data='edit_text')],
                [InlineKeyboardButton("🖼 Добавить картинку", callback_data='add_image')],
                [InlineKeyboardButton("❌ Отменить", callback_data='cancel_schedule')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(preview_text, parse_mode='HTML', reply_markup=reply_markup)

        context.user_data.pop('waiting_for_text_edit', None)

    async def handle_donation_amount_input(self, update, context):
        """Обработка ввода суммы доната"""
        try:
            amount = float(update.message.text.strip())
            if amount <= 0:
                raise ValueError()

            user = update.effective_user

            # Сохраняем донат в базу данных
            if db.add_donation(user.id, amount):
                points = int(amount // 100)
                await update.message.reply_text(
                    DONATION_MESSAGES['donate_success'].format(
                        amount=amount,
                        currency='RUB',
                        points=points
                    ),
                    parse_mode='HTML'
                )

                # Проверяем достижения
                current_year = datetime.now().year
                total_yearly = db.get_total_donations(user.id, current_year)
                achievements = db.check_and_unlock_achievements(user.id, donations=total_yearly)

                # Сообщаем о новых достижениях
                for achievement in achievements:
                    if achievement in ACHIEVEMENT_MESSAGES:
                        await update.effective_chat.send_message(
                            ACHIEVEMENT_MESSAGES[achievement].format(name=user.first_name),
                            parse_mode='HTML'
                        )
            else:
                await update.message.reply_text(DONATION_MESSAGES['donate_error'])

        except ValueError:
            await update.message.reply_text("❌ Неверная сумма! Введите положительное число.")

        context.user_data.pop('waiting_for_donation_amount', None)

    async def handle_new_chat_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка новых участников чата"""
        chat_id = update.effective_chat.id

        # Удаляем предыдущее приветственное сообщение, если оно есть
        await self.delete_welcome_message(chat_id)

        # Создаем новое приветственное сообщение с правилами и кнопками донатов
        welcome_text = self.get_welcome_message_with_rules()

        # Создаем клавиатуру с кнопками донатов
        donation_keyboard = [
            [InlineKeyboardButton("💰 100 ₽", callback_data='donate_100')],
            [InlineKeyboardButton("💰 500 ₽", callback_data='donate_500')],
            [InlineKeyboardButton("💰 1000 ₽", callback_data='donate_1000')],
            [InlineKeyboardButton("🎯 Помощь", callback_data='cmd_help')]
        ]
        reply_markup = InlineKeyboardMarkup(donation_keyboard)

        try:
            message = await update.effective_chat.send_message(welcome_text, parse_mode='HTML', reply_markup=reply_markup)
            # Сохраняем информацию о сообщении для автодаления
            await self.set_welcome_message(chat_id, message.message_id)

            # Обрабатываем каждого нового участника
            for member in update.chat_member.new_chat_members:
                db.add_user(member.id, member.username, member.first_name, member.last_name)

                # Начисление очков за вступление в чат
                db.update_score(member.id, SCORE_VALUES['join_chat'])

                # Обновление репутации за вступление в чат
                db.update_reputation(member.id, SCORE_VALUES['reputation_per_message'])

        except Exception as e:
            print(f"Ошибка при отправке приветственного сообщения: {e}")

    def get_welcome_message_with_rules(self):
        """Генерация приветственного сообщения с правилами группы"""
        welcome_text = """🎉 <b>Добро пожаловать в нашу группу!</b>

👋 Приветствуем всех новых участников!

📋 <b>Правила нашей группы:</b>
• Соблюдайте уважительное общение
• Не используйте нецензурную лексику
• Спам и реклама запрещены
• Уважайте мнение других участников
• Используйте /help для получения справки о командах бота

🎮 В группе работает система рейтингов и игр!
🏆 Используйте /rank для просмотра вашего рейтинга

💰 <b>Поддержите проект:</b>
Если вам нравится бот, вы можете поддержать его развитие!"""
        return welcome_text

    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка инлайновых запросов"""
        query = update.inline_query.query

        results = []

        try:
            if query.startswith('weather'):
                city = query.split(' ', 1)[1] if len(query.split(' ', 1)) > 1 else 'Moscow'

                # Валидация города
                if not city or len(city.strip()) < 2:
                    results.append(InlineQueryResultArticle(
                        id='1',
                        title="Ошибка",
                        input_message_content=InputTextMessageContent("Название города должно содержать минимум 2 символа")
                    ))
                elif len(city) > 50:
                    results.append(InlineQueryResultArticle(
                        id='1',
                        title="Ошибка",
                        input_message_content=InputTextMessageContent("Название города слишком длинное")
                    ))
                elif OPENWEATHER_API_KEY:
                    try:
                        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
                        response = requests.get(url, timeout=5)

                        if response.status_code == 200:
                            data = response.json()
                            if data.get('cod') == 200:
                                weather_text = f"Погода в {data['name']}:\nТемпература: {data['main']['temp']}°C\nОщущается как: {data['main']['feels_like']}°C\nВлажность: {data['main']['humidity']}%\nОписание: {data['weather'][0]['description']}"
                                results.append(InlineQueryResultArticle(
                                    id='1',
                                    title=f"Погода в {city}",
                                    input_message_content=InputTextMessageContent(weather_text)
                                ))
                            else:
                                results.append(InlineQueryResultArticle(
                                    id='1',
                                    title="Город не найден",
                                    input_message_content=InputTextMessageContent(f"Город '{city}' не найден")
                                ))
                        else:
                            results.append(InlineQueryResultArticle(
                                id='1',
                                title="Ошибка API",
                                input_message_content=InputTextMessageContent("Ошибка при получении погоды")
                            ))
                    except Exception:
                        results.append(InlineQueryResultArticle(
                            id='1',
                            title="Ошибка сети",
                            input_message_content=InputTextMessageContent("Ошибка подключения к серверу погоды")
                        ))
                else:
                    results.append(InlineQueryResultArticle(
                        id='1',
                        title="API недоступен",
                        input_message_content=InputTextMessageContent("API погоды не настроен")
                    ))

            elif query.startswith('translate'):
                # Базовая заглушка для перевода
                text_parts = query.split(' ', 2)
                if len(text_parts) >= 3:
                    text = text_parts[1]
                    lang = text_parts[2]

                    if text and lang and len(text) <= 500 and len(lang) == 2:
                        result_text = f"Перевод '{text[:50]}{'...' if len(text) > 50 else ''}' на {lang}\n[Функция перевода недоступна в текущей версии]"
                        results.append(InlineQueryResultArticle(
                            id='1',
                            title=f"Перевод на {lang}",
                            input_message_content=InputTextMessageContent(result_text)
                        ))
                    else:
                        results.append(InlineQueryResultArticle(
                            id='1',
                            title="Ошибка",
                            input_message_content=InputTextMessageContent("Использование: текст для перевода")
                        ))
                else:
                    results.append(InlineQueryResultArticle(
                        id='1',
                        title="Использование",
                        input_message_content=InputTextMessageContent("Использование: weather [город] или translate [текст] [язык]")
                    ))

            await update.inline_query.answer(results)

        except Exception as e:
            print(f"Ошибка при обработке инлайнового запроса: {e}")
            # Пустой ответ в случае ошибки
            await update.inline_query.answer([])

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

        await query.edit_message_text(HELP_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    async def show_games_menu(self, query):
        """Показать меню выбора игр"""
        keyboard = [
            [InlineKeyboardButton("Камень-ножницы-бумага", callback_data='game_rps')],
            [InlineKeyboardButton("Крестики-нолики", callback_data='game_tic_tac_toe')],
            [InlineKeyboardButton("Викторина", callback_data='game_quiz')],
            [InlineKeyboardButton("Морской бой", callback_data='game_battleship')],
            [InlineKeyboardButton("2048", callback_data='game_2048')],
            [InlineKeyboardButton("Тетрис", callback_data='game_tetris')],
            [InlineKeyboardButton("Змейка", callback_data='game_snake')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(GAME_MESSAGES['select_game'], reply_markup=reply_markup)

    async def confirm_schedule_post(self, query, context):
        """Подтверждение и добавление поста в расписание"""
        try:
            draft = context.user_data.get('schedule_draft')
            if not draft:
                await query.edit_message_text("❌ Данные поста не найдены. Попробуйте создать пост заново.")
                return

            # Добавление поста в базу данных
            post_id = db.add_scheduled_post(
                chat_id=draft['chat_id'],
                text=draft['text'],
                schedule_time=draft['schedule_time'].strftime('%Y-%m-%d %H:%M:%S'),
                created_by=draft['created_by']
            )

            if post_id:
                await query.edit_message_text(
                    f"✅ Пост успешно запланирован!\n\n📅 Время публикации: {draft['schedule_time'].strftime('%Y-%m-%d %H:%M:%S')}\n📝 Текст: {draft['text'][:50]}{'...' if len(draft['text']) > 50 else ''}\n🆔 ID поста: {post_id}"
                )
            else:
                await query.edit_message_text("❌ Ошибка при сохранении поста в базу данных.")

            # Очищаем черновик
            context.user_data.pop('schedule_draft', None)

        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при планировании поста: {str(e)}")

    async def edit_schedule_text(self, query, context):
        """Редактирование текста поста"""
        draft = context.user_data.get('schedule_draft')
        if not draft:
            await query.edit_message_text("❌ Данные поста не найдены.")
            return

        await query.edit_message_text(
            "📝 Отправьте новый текст для поста в ответ на это сообщение.\n\nТекущий текст:\n" + draft['text'],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отменить", callback_data='cancel_schedule')]])
        )

        # Устанавливаем флаг ожидания нового текста
        context.user_data['waiting_for_text_edit'] = True

    async def add_schedule_image(self, query, context):
        """Добавление картинки к посту"""
        draft = context.user_data.get('schedule_draft')
        if not draft:
            await query.edit_message_text("❌ Данные поста не найдены.")
            return

        await query.edit_message_text(
            "🖼 Отправьте картинку для поста в ответ на это сообщение.\n\nТекущий текст:\n" + draft['text'],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отменить", callback_data='cancel_schedule')]])
        )

        # Устанавливаем флаг ожидания картинки
        context.user_data['waiting_for_image'] = True

    async def cancel_schedule_post(self, query, context):
        """Отмена планирования поста"""
        context.user_data.pop('schedule_draft', None)
        context.user_data.pop('waiting_for_text_edit', None)
        context.user_data.pop('waiting_for_image', None)

        await query.edit_message_text("❌ Планирование поста отменено.")

    # ===== НОВЫЕ ИГРЫ =====

    async def start_2048_game(self, query, context):
        """Запуск игры 2048"""
        # Инициализация поля 4x4
        board = [[0 for _ in range(4)] for _ in range(4)]

        # Добавляем два начальных числа
        self.add_random_tile(board)
        self.add_random_tile(board)

        context.user_data['2048_board'] = board
        context.user_data['2048_score'] = 0

        keyboard = self.create_2048_keyboard(board, 0)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(GAME_MESSAGES['2048_start'], reply_markup=reply_markup, parse_mode='HTML')

    async def start_tetris_game(self, query, context):
        """Запуск игры Тетрис"""
        # Инициализация поля 10x20 (ширина x высота)
        board = [[0 for _ in range(10)] for _ in range(20)]
        current_piece = self.get_random_tetris_piece()
        context.user_data['tetris_board'] = board
        context.user_data['tetris_current_piece'] = current_piece
        context.user_data['tetris_score'] = 0
        context.user_data['tetris_lines'] = 0

        keyboard = self.create_tetris_keyboard(board, current_piece, 0, 0)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(GAME_MESSAGES['tetris_start'], reply_markup=reply_markup, parse_mode='HTML')

    async def start_snake_game(self, query, context):
        """Запуск игры Змейка"""
        # Инициализация поля 10x10
        board = [[0 for _ in range(10)] for _ in range(10)]
        snake = [(5, 5)]  # Начальная позиция змейки
        food = self.place_food(board, snake)
        direction = 'right'

        context.user_data['snake_board'] = board
        context.user_data['snake_body'] = snake
        context.user_data['snake_food'] = food
        context.user_data['snake_direction'] = direction
        context.user_data['snake_score'] = 0

        keyboard = self.create_snake_keyboard(board, snake, food, 0)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(GAME_MESSAGES['snake_start'], reply_markup=reply_markup, parse_mode='HTML')

    async def handle_2048_move(self, query, context):
        """Обработка ходов в игре 2048"""
        move = query.data.split('_')[1]

        board = context.user_data.get('2048_board')
        score = context.user_data.get('2048_score', 0)

        if not board:
            await query.answer("Игра не найдена")
            return

        moved, new_score = self.move_2048(board, move)
        score += new_score

        if moved:
            self.add_random_tile(board)
            context.user_data['2048_score'] = score

            # Проверяем победу
            if self.check_2048_win(board):
                db.update_score(query.from_user.id, 20)
                keyboard = self.create_2048_keyboard(board, score, game_over=True)
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(GAME_MESSAGES['2048_win'], reply_markup=reply_markup)
                return

            # Проверяем окончание игры
            if not self.can_move_2048(board):
                keyboard = self.create_2048_keyboard(board, score, game_over=True)
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(GAME_MESSAGES['2048_game_over'], reply_markup=reply_markup)
                return

            keyboard = self.create_2048_keyboard(board, score)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(GAME_MESSAGES['2048_start'], reply_markup=reply_markup, parse_mode='HTML')
        else:
            await query.answer("Невозможный ход!")

    async def handle_tetris_move(self, query, context):
        """Обработка ходов в игре Тетрис"""
        move = query.data.split('_')[1]

        board = context.user_data.get('tetris_board')
        piece = context.user_data.get('tetris_current_piece')
        score = context.user_data.get('tetris_score', 0)
        lines = context.user_data.get('tetris_lines', 0)

        if not board or not piece:
            await query.answer("Игра не найдена")
            return

        # Обработка движений
        if move == 'left':
            piece['x'] -= 1
            if not self.is_valid_position(board, piece):
                piece['x'] += 1
        elif move == 'right':
            piece['x'] += 1
            if not self.is_valid_position(board, piece):
                piece['x'] -= 1
        elif move == 'down':
            piece['y'] += 1
            if not self.is_valid_position(board, piece):
                piece['y'] -= 1
                # Фиксируем фигуру и создаем новую
                self.place_piece(board, piece)
                lines_cleared = self.clear_lines(board)
                score += lines_cleared * 10
                lines += lines_cleared

                new_piece = self.get_random_tetris_piece()
                if not self.is_valid_position(board, new_piece):
                    # Игра окончена
                    keyboard = self.create_tetris_keyboard(board, piece, score, lines, game_over=True)
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(GAME_MESSAGES['tetris_game_over'].format(score=score), reply_markup=reply_markup)
                    return
                piece = new_piece
        elif move == 'rotate':
            old_shape = piece['shape'][:]
            piece['shape'] = list(zip(*piece['shape'][::-1]))
            if not self.is_valid_position(board, piece):
                piece['shape'] = old_shape

        context.user_data['tetris_current_piece'] = piece
        context.user_data['tetris_score'] = score
        context.user_data['tetris_lines'] = lines

        keyboard = self.create_tetris_keyboard(board, piece, score, lines)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(GAME_MESSAGES['tetris_start'], reply_markup=reply_markup, parse_mode='HTML')

    async def handle_snake_move(self, query, context):
        """Обработка движений в игре Змейка"""
        new_direction = query.data.split('_')[1]

        board = context.user_data.get('snake_board')
        snake = context.user_data.get('snake_body')
        food = context.user_data.get('snake_food')
        direction = context.user_data.get('snake_direction', 'right')
        score = context.user_data.get('snake_score', 0)

        if not board or not snake:
            await query.answer("Игра не найдена")
            return

        # Не позволяем двигаться в обратном направлении
        opposites = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        if new_direction == opposites.get(direction):
            await query.answer("Невозможное направление!")
            return

        # Двигаем змейку
        head = snake[0]
        if new_direction == 'up':
            new_head = (head[0] - 1, head[1])
        elif new_direction == 'down':
            new_head = (head[0] + 1, head[1])
        elif new_direction == 'left':
            new_head = (head[0], head[1] - 1)
        elif new_direction == 'right':
            new_head = (head[0], head[1] + 1)

        # Проверяем столкновения
        if (new_head[0] < 0 or new_head[0] >= 10 or
            new_head[1] < 0 or new_head[1] >= 10 or
            new_head in snake):
            # Игра окончена
            db.update_score(query.from_user.id, score)
            keyboard = self.create_snake_keyboard(board, snake, food, score, game_over=True)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(GAME_MESSAGES['snake_game_over'].format(length=len(snake), score=score), reply_markup=reply_markup)
            return

        snake.insert(0, new_head)

        # Проверяем еду
        if new_head == food:
            score += 10
            food = self.place_food(board, snake)
        else:
            snake.pop()  # Удаляем хвост

        context.user_data['snake_body'] = snake
        context.user_data['snake_food'] = food
        context.user_data['snake_direction'] = new_direction
        context.user_data['snake_score'] = score

        keyboard = self.create_snake_keyboard(board, snake, food, score)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(GAME_MESSAGES['snake_start'], reply_markup=reply_markup, parse_mode='HTML')

    # ===== ДОНАТЫ И ДОСТИЖЕНИЯ =====

    async def donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда доната"""
        keyboard = [
            [InlineKeyboardButton("100 ₽", callback_data='donate_100')],
            [InlineKeyboardButton("500 ₽", callback_data='donate_500')],
            [InlineKeyboardButton("1000 ₽", callback_data='donate_1000')],
            [InlineKeyboardButton("2500 ₽", callback_data='donate_2500')],
            [InlineKeyboardButton("5000 ₽", callback_data='donate_5000')],
            [InlineKeyboardButton("Другая сумма", callback_data='donate_custom')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            DONATION_MESSAGES['donate_welcome'],
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых сообщений"""
        user = update.effective_user
        voice = update.message.voice

        # Добавление пользователя в базу данных
        db.add_user(user.id, user.username, user.first_name, user.last_name)

        # Начисление очков за голосовое сообщение
        db.update_score(user.id, SCORE_VALUES['message'])

        duration = voice.duration

        # Попытка транскрибации голосового сообщения
        transcription = await self.transcribe_voice_message(voice, update)

        await update.message.reply_text(
            f"🎤 Голосовое сообщение от {user.first_name} ({duration} сек)\n\n"
            f"🔄 Транскрибация: {transcription}\n\n"
            f"💡 +1 очко за активность!",
            reply_to_message_id=update.message.message_id
        )

    async def transcribe_voice_message(self, voice, update):
        """Транскрибация голосового сообщения с использованием speech recognition"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return "[Speech Recognition не установлен. Установите: pip install SpeechRecognition]"

        try:
            # Создаем временный файл для загрузки аудио
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
                temp_ogg_path = temp_ogg.name

            # Скачиваем голосовое сообщение
            voice_file = await voice.get_file()
            await voice_file.download_to_drive(temp_ogg_path)

            # Конвертируем OGG в WAV для speech_recognition
            temp_wav_path = temp_ogg_path.replace('.ogg', '.wav')

            if PYDUB_AVAILABLE:
                # Используем pydub для конвертации
                audio = AudioSegment.from_ogg(temp_ogg_path)
                audio.export(temp_wav_path, format='wav')
            else:
                # Используем ffmpeg для конвертации (если доступен)
                try:
                    subprocess.run([
                        'ffmpeg', '-i', temp_ogg_path, '-acodec', 'pcm_s16le',
                        '-ar', '16000', '-ac', '1', temp_wav_path
                    ], check=True, capture_output=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Очищаем временные файлы и возвращаем ошибку
                    os.unlink(temp_ogg_path)
                    return "[невозможно конвертировать аудио - установите ffmpeg или pydub]\n💡 Для полной работы: pip install SpeechRecognition pydub ffmpeg-python"

            # Распознавание речи
            recognizer = sr.Recognizer()

            with sr.AudioFile(temp_wav_path) as source:
                audio_data = recognizer.record(source)

                # Пробуем разные API для распознавания
                try:
                    # Сначала пробуем Google Speech Recognition (бесплатно)
                    text = recognizer.recognize_google(audio_data, language='ru-RU')
                    return text
                except sr.UnknownValueError:
                    return "[не удалось распознать речь]"
                except sr.RequestError:
                    # Если Google API недоступен, пробуем Sphinx (локальный, но менее точный)
                    try:
                        text = recognizer.recognize_sphinx(audio_data, language='ru-RU')
                        return text
                    except sr.UnknownValueError:
                        return "[не удалось распознать речь (локально)]"
                    except sr.RequestError:
                        return "[сервисы распознавания речи недоступны]"

        except Exception as e:
            print(f"Ошибка при транскрибации: {e}")
            return "[ошибка при обработке голосового сообщения]"

        finally:
            # Очищаем временные файлы
            try:
                if 'temp_ogg_path' in locals():
                    os.unlink(temp_ogg_path)
                if 'temp_wav_path' in locals():
                    os.unlink(temp_wav_path)
            except:
                pass

    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ИГР =====

    def add_random_tile(self, board):
        """Добавляет случайную плитку (2 или 4) в пустую клетку"""
        empty_cells = [(i, j) for i in range(4) for j in range(4) if board[i][j] == 0]
        if empty_cells:
            i, j = random.choice(empty_cells)
            board[i][j] = 2 if random.random() < 0.9 else 4

    def move_2048(self, board, direction):
        """Двигает плитки в указанном направлении"""
        def move_row_left(row):
            """Двигает строку влево"""
            new_row = [i for i in row if i != 0]
            for i in range(len(new_row) - 1):
                if new_row[i] == new_row[i + 1]:
                    new_row[i] *= 2
                    new_row[i + 1] = 0
            new_row = [i for i in new_row if i != 0]
            return new_row + [0] * (4 - len(new_row))

        moved = False
        score = 0

        if direction == 'left':
            for i in range(4):
                old_row = board[i][:]
                board[i] = move_row_left(board[i])
                if board[i] != old_row:
                    moved = True
        elif direction == 'right':
            for i in range(4):
                old_row = board[i][:]
                board[i] = move_row_left(board[i][::-1])[::-1]
                if board[i] != old_row:
                    moved = True
        elif direction == 'up':
            for j in range(4):
                col = [board[i][j] for i in range(4)]
                old_col = col[:]
                new_col = move_row_left(col)
                for i in range(4):
                    board[i][j] = new_col[i]
                if new_col != old_col:
                    moved = True
        elif direction == 'down':
            for j in range(4):
                col = [board[i][j] for i in range(4)]
                old_col = col[:]
                new_col = move_row_left(col[::-1])[::-1]
                for i in range(4):
                    board[i][j] = new_col[i]
                if new_col != old_col:
                    moved = True

        return moved, score

    def can_move_2048(self, board):
        """Проверяет, возможны ли ходы"""
        for i in range(4):
            for j in range(4):
                if board[i][j] == 0:
                    return True
                if i > 0 and board[i][j] == board[i-1][j]:
                    return True
                if j > 0 and board[i][j] == board[i][j-1]:
                    return True
        return False

    def check_2048_win(self, board):
        """Проверяет победу (наличие 2048)"""
        return any(2048 in row for row in board)

    def create_2048_keyboard(self, board, score, game_over=False):
        """Создает клавиатуру для игры 2048"""
        keyboard = []
        for i in range(4):
            row = []
            for j in range(4):
                cell = board[i][j]
                text = str(cell) if cell != 0 else ' '
                row.append(InlineKeyboardButton(text, callback_data=f'2048_cell_{i}_{j}'))
            keyboard.append(row)

        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data='2048_left'),
            InlineKeyboardButton("⬆️", callback_data='2048_up'),
            InlineKeyboardButton("⬇️", callback_data='2048_down'),
            InlineKeyboardButton("➡️", callback_data='2048_right')
        ])

        keyboard.append([
            InlineKeyboardButton("🔄 Новая игра", callback_data='game_2048'),
            InlineKeyboardButton("⬅️ Назад к играм", callback_data='cmd_play_game')
        ])

        return keyboard

    def get_random_tetris_piece(self):
        """Возвращает случайную тетрис-фигуру"""
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

    def is_valid_position(self, board, piece):
        """Проверяет, можно ли разместить фигуру в данной позиции"""
        for i, row in enumerate(piece['shape']):
            for j, cell in enumerate(row):
                if cell:
                    x, y = piece['x'] + j, piece['y'] + i
                    if (x < 0 or x >= 10 or y >= 20 or
                        (y >= 0 and board[y][x] != 0)):
                        return False
        return True

    def place_piece(self, board, piece):
        """Размещает фигуру на поле"""
        for i, row in enumerate(piece['shape']):
            for j, cell in enumerate(row):
                if cell:
                    x, y = piece['x'] + j, piece['y'] + i
                    if 0 <= y < 20 and 0 <= x < 10:
                        board[y][x] = 1

    def clear_lines(self, board):
        """Очищает заполненные линии"""
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

    def create_tetris_keyboard(self, board, piece, score, lines, game_over=False):
        """Создает клавиатуру для игры Тетрис"""
        # Упрощенная визуализация - показываем только нижнюю часть поля
        display_board = board[-10:] if len(board) > 10 else board

        keyboard = []
        for row in display_board:
            display_row = []
            for cell in row:
                text = '⬛' if cell else '⬜'
                display_row.append(InlineKeyboardButton(text, callback_data='tetris_display'))
            keyboard.append(display_row)

        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data='tetris_left'),
            InlineKeyboardButton("🔄", callback_data='tetris_rotate'),
            InlineKeyboardButton("➡️", callback_data='tetris_right')
        ])
        keyboard.append([
            InlineKeyboardButton("⬇️", callback_data='tetris_down'),
            InlineKeyboardButton("🔄 Новая игра", callback_data='game_tetris'),
            InlineKeyboardButton("⬅️ Назад к играм", callback_data='cmd_play_game')
        ])

        return keyboard

    def place_food(self, board, snake):
        """Размещает еду в случайной свободной клетке"""
        empty_cells = [(i, j) for i in range(10) for j in range(10) if (i, j) not in snake]
        if empty_cells:
            return random.choice(empty_cells)
        return None

    def create_snake_keyboard(self, board, snake, food, score, game_over=False):
        """Создает клавиатуру для игры Змейка"""
        keyboard = []
        for i in range(10):
            row = []
            for j in range(10):
                if (i, j) == food:
                    text = '🍎'
                elif (i, j) in snake:
                    text = '🟢' if (i, j) == snake[0] else '🟩'
                else:
                    text = '⬜'
                row.append(InlineKeyboardButton(text, callback_data=f'snake_cell_{i}_{j}'))
            keyboard.append(row)

        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data='snake_left'),
            InlineKeyboardButton("⬆️", callback_data='snake_up'),
            InlineKeyboardButton("⬇️", callback_data='snake_down'),
            InlineKeyboardButton("➡️", callback_data='snake_right')
        ])

        keyboard.append([
            InlineKeyboardButton("🔄 Новая игра", callback_data='game_snake'),
            InlineKeyboardButton("⬅️ Назад к играм", callback_data='cmd_play_game')
        ])

        return keyboard

    def check_profanity(self, text):
        """Проверка текста на наличие нецензурной лексики"""
        text_lower = text.lower()
        for word in PROFANITY_WORDS:
            if word in text_lower:
                return True
        return False

    async def handle_profanity_violation(self, update, user):
        """Обработка нарушения с нецензурной лексикой"""
        # Удаление сообщения с матом
        try:
            await update.message.delete()
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")

        # Отправка предупреждения в чат
        username = user.username if user.username else user.first_name
        await update.effective_chat.send_message(
            MODERATION_MESSAGES['profanity_detected'].format(username=username),
            parse_mode='HTML'
        )

        # Начисление предупреждения пользователю
        db.add_warning(user.id, "Нецензурная лексика", 0)  # 0 - системное предупреждение

    async def handle_donation_callback(self, query, context):
        """Обработка callback'ов донатов"""
        await query.answer()

        amount_str = query.data.split('_')[1]
        if amount_str == 'custom':
            # Запрос ввода суммы
            await query.edit_message_text(
                "💰 Введите сумму доната в рублях:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data='donate_cancel')]])
            )
            context.user_data['waiting_for_donation_amount'] = True
            return

        try:
            amount = float(amount_str)
            user = query.from_user

            # Сохраняем донат в базу данных
            if db.add_donation(user.id, amount):
                points = int(amount // 100)
                await query.edit_message_text(
                    DONATION_MESSAGES['donate_success'].format(
                        amount=amount,
                        currency='RUB',
                        points=points
                    ),
                    parse_mode='HTML'
                )

                # Проверяем достижения
                current_year = datetime.now().year
                total_yearly = db.get_total_donations(user.id, current_year)
                achievements = db.check_and_unlock_achievements(user.id, donations=total_yearly)

                # Сообщаем о новых достижениях
                for achievement in achievements:
                    if achievement in ACHIEVEMENT_MESSAGES:
                        await query.message.chat.send_message(
                            ACHIEVEMENT_MESSAGES[achievement].format(name=user.first_name),
                            parse_mode='HTML'
                        )
            else:
                await query.edit_message_text(DONATION_MESSAGES['donate_error'])

        except ValueError:
            await query.edit_message_text("❌ Неверная сумма!")

    def run(self):
        """Запуск бота"""
        print("Bot started!")
        self.application.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()
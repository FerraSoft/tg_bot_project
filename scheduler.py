#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Планировщик публикации постов по расписанию
"""

import asyncio
import logging
import time
import os
import sys
from datetime import datetime
from telegram import Bot
from database_sqlite import Database
from config_local import BOT_TOKEN
from messages import TECH_MESSAGES, SCHEDULER_CONFIG

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PostScheduler:
    def __init__(self):
        self.db = Database()
        self.bot = Bot(token=BOT_TOKEN)
        self.running = False

    async def start(self):
        """Запуск планировщика"""
        self.running = True
        logger.info(TECH_MESSAGES['scheduler_started'])

        while self.running:
            try:
                await self.check_and_publish_posts()
                await asyncio.sleep(SCHEDULER_CONFIG['check_interval'])  # Проверка каждые 30 секунд
            except Exception as e:
                logger.error(TECH_MESSAGES['scheduler_error'].format(error=e))
                await asyncio.sleep(60)  # При ошибке ждем минуту

    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        logger.info(TECH_MESSAGES['scheduler_stopped'])

    async def check_and_publish_posts(self):
        """Проверка и публикация постов по расписанию"""
        try:
            # Получаем посты, готовые к публикации
            pending_posts = self.db.get_pending_posts()

            for post in pending_posts:
                post_id, chat_id, text, image_path = post

                try:
                    # Публикуем пост
                    if image_path and os.path.exists(image_path):
                        with open(image_path, 'rb') as photo:
                            await self.bot.send_photo(chat_id, photo, caption=text)
                    else:
                        await self.bot.send_message(chat_id, text)

                    # Отмечаем пост как опубликованный
                    self.db.mark_post_published(post_id)

                    logger.info(TECH_MESSAGES['post_published'].format(post_id=post_id, chat_id=chat_id))

                except Exception as e:
                    logger.error(TECH_MESSAGES['post_publish_error'].format(post_id=post_id, error=e))

        except Exception as e:
            logger.error(TECH_MESSAGES['posts_check_error'].format(error=e))

async def main():
    """Главная функция"""
    scheduler = PostScheduler()

    try:
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        await scheduler.stop()
        scheduler.db.close()

if __name__ == "__main__":
    asyncio.run(main())
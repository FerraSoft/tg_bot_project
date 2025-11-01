"""
Сервисы AI для интеграции с различными платформами.
Реализует уникальную фику "Мульти-помощник с российскими AI".
"""

import os
import json
import asyncio
import logging
import aiohttp
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import time

from config import GIGACHAT_API_KEY, YANDEX_API_KEY, YANDEX_FOLDER_ID, MAX_API_TOKEN


class AIService(ABC):
    """
    Абстрактный базовый класс для AI сервисов.
    Определяет общий интерфейс для всех AI интеграций.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.cache = {}
        self.cache_ttl = config.get('cache_ttl', 3600)  # 1 час по умолчанию

    @abstractmethod
    async def generate_response(self, query: str, user_id: int = None, **kwargs) -> str:
        """
        Генерация ответа на запрос пользователя.

        Args:
            query: Запрос пользователя
            user_id: ID пользователя (для персонализации)
            **kwargs: Дополнительные параметры

        Returns:
            Ответ AI
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Проверка доступности сервиса.

        Returns:
            True если сервис доступен
        """
        pass

    def _get_cache_key(self, query: str, user_id: int = None) -> str:
        """Генерация ключа кеша"""
        return f"{self.name}:{user_id or 'anonymous'}:{hash(query)}"

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Получение ответа из кеша"""
        if cache_key in self.cache:
            timestamp, response = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return response
            else:
                del self.cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: str):
        """Сохранение ответа в кеш"""
        self.cache[cache_key] = (time.time(), response)


class GigaChatService(AIService):
    """
    Сервис интеграции с GigaChat.
    Специализируется на интеллектуальных ответах и генерации контента.
    """

    def __init__(self):
        config = {
            'api_key': GIGACHAT_API_KEY,
            'base_url': 'https://gigachat.devices.sberbank.ru/api/v1',
            'max_tokens': 1000,
            'temperature': 0.7,
            'cache_ttl': 3600
        }
        super().__init__('gigachat', config)
        self.access_token = None
        self.token_expires = None

    async def _get_access_token(self) -> str:
        """Получение токена доступа для GigaChat API"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json',
                    'RqUID': str(datetime.now().timestamp())
                }

                data = {
                    'scope': 'GIGACHAT_API_PERS'
                }

                auth = aiohttp.BasicAuth(self.config['api_key'], '')

                async with session.post(
                    f"{self.config['base_url']}/oauth",
                    headers=headers,
                    data=data,
                    auth=auth
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.access_token = result['access_token']
                        # Токен действует 30 минут
                        self.token_expires = datetime.now() + timedelta(minutes=30)
                        return self.access_token
                    else:
                        self.logger.error(f"Ошибка получения токена GigaChat: {response.status}")
                        return None

        except Exception as e:
            self.logger.error(f"Ошибка при получении токена GigaChat: {e}")
            return None

    async def generate_response(self, query: str, user_id: int = None, **kwargs) -> str:
        """
        Генерация ответа через GigaChat.

        Args:
            query: Запрос пользователя
            user_id: ID пользователя
            **kwargs: Дополнительные параметры

        Returns:
            Ответ GigaChat
        """
        # Проверка кеша
        cache_key = self._get_cache_key(query, user_id)
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached

        token = await self._get_access_token()
        if not token:
            return "Извините, сервис GigaChat временно недоступен."

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }

                payload = {
                    'model': 'GigaChat',
                    'messages': [
                        {
                            'role': 'user',
                            'content': query
                        }
                    ],
                    'max_tokens': self.config['max_tokens'],
                    'temperature': self.config['temperature']
                }

                async with session.post(
                    f"{self.config['base_url']}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result['choices'][0]['message']['content']

                        # Кешируем результат
                        self._cache_response(cache_key, response_text)

                        return response_text
                    else:
                        self.logger.error(f"Ошибка GigaChat API: {response.status}")
                        return "Извините, произошла ошибка при обработке запроса."

        except Exception as e:
            self.logger.error(f"Ошибка при запросе к GigaChat: {e}")
            return "Извините, сервис временно недоступен."

    async def is_available(self) -> bool:
        """Проверка доступности GigaChat"""
        token = await self._get_access_token()
        return token is not None


class YandexGPTService(AIService):
    """
    Сервис интеграции с YandexGPT.
    Специализируется на персонализированных рекомендациях и анализе.
    """

    def __init__(self):
        config = {
            'api_key': YANDEX_API_KEY,
            'folder_id': YANDEX_FOLDER_ID,
            'base_url': 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
            'max_tokens': 1000,
            'temperature': 0.7,
            'cache_ttl': 3600
        }
        super().__init__('yandexgpt', config)

    async def generate_response(self, query: str, user_id: int = None, **kwargs) -> str:
        """
        Генерация ответа через YandexGPT.

        Args:
            query: Запрос пользователя
            user_id: ID пользователя для персонализации
            **kwargs: Дополнительные параметры

        Returns:
            Ответ YandexGPT
        """
        # Проверка кеша
        cache_key = self._get_cache_key(query, user_id)
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached

        if not self.config['api_key'] or not self.config['folder_id']:
            return "Извините, сервис YandexGPT временно недоступен."

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Api-Key {self.config["api_key"]}',
                    'Content-Type': 'application/json'
                }

                # Добавляем персонализацию на основе user_id
                personalized_query = query
                if user_id:
                    personalized_query = f"Пользователь ID: {user_id}. {query}"

                payload = {
                    'modelUri': f'gpt://{self.config["folder_id"]}/yandexgpt-lite',
                    'completionOptions': {
                        'stream': False,
                        'temperature': self.config['temperature'],
                        'maxTokens': self.config['max_tokens']
                    },
                    'messages': [
                        {
                            'role': 'user',
                            'text': personalized_query
                        }
                    ]
                }

                async with session.post(
                    self.config['base_url'],
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result['result']['alternatives'][0]['message']['text']

                        # Кешируем результат
                        self._cache_response(cache_key, response_text)

                        return response_text
                    else:
                        self.logger.error(f"Ошибка YandexGPT API: {response.status}")
                        return "Извините, произошла ошибка при обработке запроса."

        except Exception as e:
            self.logger.error(f"Ошибка при запросе к YandexGPT: {e}")
            return "Извините, сервис временно недоступен."

    async def is_available(self) -> bool:
        """Проверка доступности YandexGPT"""
        return bool(self.config['api_key'] and self.config['folder_id'])


class MAXService(AIService):
    """
    Сервис интеграции с MAX (max.ru).
    Уникальная фишка проекта - интеграция с российским мессенджером.
    """

    def __init__(self):
        config = {
            'api_token': MAX_API_TOKEN,
            'base_url': 'https://api.max.ru/v1',
            'max_tokens': 1000,
            'temperature': 0.7,
            'cache_ttl': 3600
        }
        super().__init__('max', config)

    async def generate_response(self, query: str, user_id: int = None, **kwargs) -> str:
        """
        Генерация ответа через MAX интеграцию.
        Поскольку MAX - это мессенджер, здесь мы можем реализовать
        интеллектуальную обработку сообщений или перенаправление.

        Args:
            query: Запрос пользователя
            user_id: ID пользователя
            **kwargs: Дополнительные параметры

        Returns:
            Ответ через MAX интеграцию
        """
        # Проверка кеша
        cache_key = self._get_cache_key(query, user_id)
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached

        if not self.config['api_token']:
            return "Извините, интеграция с MAX временно недоступна."

        try:
            # В реальной реализации здесь будет интеграция с MAX API
            # Пока возвращаем симуляцию ответа
            response_text = f"💬 MAX AI: {query} (интеграция в разработке)"

            # Для демонстрации возвращаем полезный ответ
            if "привет" in query.lower():
                response_text = "Привет! Я - ваш помощник через MAX. Как я могу помочь?"
            elif "помощь" in query.lower():
                response_text = "Я интегрирован с MAX мессенджером. Могу помочь с вопросами, используя российские AI технологии."
            else:
                response_text = f"Ваш запрос обработан через MAX: '{query}'. Интеграция позволяет использовать единый интерфейс для разных платформ."

            # Кешируем результат
            self._cache_response(cache_key, response_text)

            return response_text

        except Exception as e:
            self.logger.error(f"Ошибка при работе с MAX интеграцией: {e}")
            return "Извините, произошла ошибка в интеграции с MAX."

    async def is_available(self) -> bool:
        """Проверка доступности MAX интеграции"""
        return bool(self.config['api_token'])

    async def sync_message(self, telegram_user_id: int, message: str) -> bool:
        """
        Синхронизация сообщения между Telegram и MAX.

        Args:
            telegram_user_id: ID пользователя в Telegram
            message: Сообщение для синхронизации

        Returns:
            True если синхронизация успешна
        """
        # В реальной реализации здесь будет API вызов к MAX
        self.logger.info(f"Синхронизация сообщения для пользователя {telegram_user_id}: {message}")
        return True


class AIIntegrationService:
    """
    Основной сервис для управления AI интеграциями.
    Координирует работу всех AI сервисов.
    """

    def __init__(self):
        self.services = {
            'gigachat': GigaChatService(),
            'yandexgpt': YandexGPTService(),
            'max': MAXService()
        }
        self.logger = logging.getLogger(__name__)

        # Настройки по умолчанию
        self.default_service = 'gigachat'
        self.rate_limit_per_minute = 10
        self.user_requests = {}  # user_id -> [(timestamp, service)]

    async def generate_response(self, service_name: str, query: str, user_id: int = None, **kwargs) -> str:
        """
        Генерация ответа через указанный AI сервис.

        Args:
            service_name: Название сервиса ('gigachat', 'yandexgpt', 'max')
            query: Запрос пользователя
            user_id: ID пользователя
            **kwargs: Дополнительные параметры

        Returns:
            Ответ AI
        """
        # Проверка rate limiting
        if not await self._check_rate_limit(user_id):
            return "Превышен лимит запросов. Попробуйте позже."

        service = self.services.get(service_name)
        if not service:
            return f"Сервис {service_name} не найден."

        if not await service.is_available():
            return f"Сервис {service_name} временно недоступен."

        try:
            response = await service.generate_response(query, user_id, **kwargs)

            # Записываем запрос в статистику
            await self._record_request(user_id, service_name)

            return response

        except Exception as e:
            self.logger.error(f"Ошибка при генерации ответа через {service_name}: {e}")
            return "Извините, произошла ошибка при обработке запроса."

    async def get_available_services(self) -> List[str]:
        """
        Получение списка доступных сервисов.

        Returns:
            Список названий доступных сервисов
        """
        available = []
        for name, service in self.services.items():
            if await service.is_available():
                available.append(name)
        return available

    async def switch_service(self, user_id: int, service_name: str) -> bool:
        """
        Переключение пользователя на другой AI сервис.

        Args:
            user_id: ID пользователя
            service_name: Название сервиса

        Returns:
            True если переключение успешно
        """
        if service_name not in self.services:
            return False

        # В будущем здесь можно сохранить предпочтение в БД
        self.logger.info(f"Пользователь {user_id} переключился на сервис {service_name}")
        return True

    async def _check_rate_limit(self, user_id: int) -> bool:
        """
        Проверка rate limiting для пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            True если запрос разрешен
        """
        if user_id is None:
            return True

        now = datetime.now()
        user_reqs = self.user_requests.get(user_id, [])

        # Удаляем старые запросы (старше 1 минуты)
        user_reqs = [req for req in user_reqs if now - req[0] < timedelta(minutes=1)]

        if len(user_reqs) >= self.rate_limit_per_minute:
            return False

        return True

    async def _record_request(self, user_id: int, service_name: str):
        """
        Запись запроса в статистику.

        Args:
            user_id: ID пользователя
            service_name: Название сервиса
        """
        if user_id is None:
            return

        now = datetime.now()
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []

        self.user_requests[user_id].append((now, service_name))

        # Ограничиваем размер истории
        if len(self.user_requests[user_id]) > 100:
            self.user_requests[user_id] = self.user_requests[user_id][-50:]


# Глобальный экземпляр сервиса
ai_integration = AIIntegrationService()
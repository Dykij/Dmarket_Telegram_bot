# Шаблоны типичных операций для DMarket Telegram Bot

## Создание нового обработчика команд для Telegram-бота

```python
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Инициализация роутера
router = Router()

# Определение состояний, если нужно
class ExampleStates(StatesGroup):
    waiting_for_input = State()

# Обработчик команды
@router.message(Command("example_command"))
async def cmd_example(message: types.Message, state: FSMContext):
    """
    Обработчик для команды /example_command
    
    Args:
        message: Входящее сообщение
        state: Контекст состояния пользователя
    """
    # Здесь логика обработки команды
    await message.answer("Пример ответа на команду")
    
    # При необходимости изменение состояния
    await state.set_state(ExampleStates.waiting_for_input)
    
# Регистрация роутера в диспетчере (в другом файле)
# dp.include_router(router)
```

## Создание нового парсера для источника данных

```python
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ParsedItem:
    """Результат парсинга предмета"""
    item_id: str
    title: str
    price: float
    currency: str
    url: str
    image_url: Optional[str] = None
    
class ExampleParser:
    """
    Парсер для примера источника данных
    """
    BASE_URL = "https://api.example.com"
    
    def __init__(self, api_key: str, use_proxy: bool = False, proxy_list: Optional[List[str]] = None):
        """
        Инициализация парсера
        
        Args:
            api_key: Ключ API
            use_proxy: Использовать прокси
            proxy_list: Список прокси-серверов
        """
        self.api_key = api_key
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.logger = logging.getLogger("example_parser")
        self.session = None
        
    async def connect(self) -> None:
        """Создание HTTP-сессии"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        
    async def close(self) -> None:
        """Закрытие HTTP-сессии"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def search_items(self, query: str, limit: int = 10) -> List[ParsedItem]:
        """
        Поиск предметов по запросу
        
        Args:
            query: Строка поиска
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных предметов
        """
        await self.connect()
        
        params = {
            "query": query,
            "limit": limit
        }
        
        try:
            async with self.session.get(f"{self.BASE_URL}/items/search", params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                return [
                    ParsedItem(
                        item_id=item["id"],
                        title=item["title"],
                        price=float(item["price"]),
                        currency=item["currency"],
                        url=f"{self.BASE_URL}/item/{item['id']}",
                        image_url=item.get("image")
                    )
                    for item in data["items"]
                ]
        except Exception as e:
            self.logger.error(f"Error searching items: {e}")
            return []
```

## Работа с Redis

```python
from common.redis_auto_reconnect import RedisAutoReconnect
from typing import Dict, Any, Optional, List, Union
import json

class RedisStorage:
    """
    Класс для работы с хранилищем Redis
    """
    def __init__(self, redis_client: RedisAutoReconnect):
        """
        Инициализация хранилища
        
        Args:
            redis_client: Клиент Redis с автоматическим переподключением
        """
        self.redis = redis_client
        
    async def save_user_settings(self, user_id: int, settings: Dict[str, Any]) -> None:
        """
        Сохранение настроек пользователя
        
        Args:
            user_id: ID пользователя
            settings: Словарь с настройками
        """
        key = f"user:{user_id}:settings"
        await self.redis.set(key, json.dumps(settings))
        
    async def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение настроек пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с настройками или None
        """
        key = f"user:{user_id}:settings"
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None
        
    async def add_tracked_item(self, user_id: int, item_id: str, target_price: float) -> None:
        """
        Добавление отслеживаемого предмета
        
        Args:
            user_id: ID пользователя
            item_id: ID предмета
            target_price: Целевая цена
        """
        key = f"user:{user_id}:tracked_items"
        
        # Сохранение в хэш-таблице
        await self.redis.hset(
            key,
            item_id,
            json.dumps({
                "target_price": target_price,
                "added_at": datetime.datetime.now().isoformat()
            })
        )
        
        # Добавление в обратный индекс для быстрого поиска
        await self.redis.sadd(f"tracked_item:{item_id}:users", str(user_id))
        
    async def get_users_tracking_item(self, item_id: str) -> List[int]:
        """
        Получение списка пользователей, отслеживающих предмет
        
        Args:
            item_id: ID предмета
            
        Returns:
            Список ID пользователей
        """
        users = await self.redis.smembers(f"tracked_item:{item_id}:users")
        return [int(user_id) for user_id in users]
```

## Работа с RabbitMQ для обработки событий

```python
from common.rabbitmq_auto_reconnect import RabbitMQAutoReconnect
import json
from typing import Dict, Any, Callable, Awaitable
import asyncio

class EventProcessor:
    """
    Класс для обработки событий через RabbitMQ
    """
    def __init__(self, rabbitmq_client: RabbitMQAutoReconnect):
        """
        Инициализация процессора событий
        
        Args:
            rabbitmq_client: Клиент RabbitMQ с автоматическим переподключением
        """
        self.rabbitmq = rabbitmq_client
        self.handlers = {}
        
    async def publish_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Публикация события
        
        Args:
            event_type: Тип события
            payload: Данные события
        """
        message = {
            "event_type": event_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "payload": payload
        }
        
        await self.rabbitmq.publish_message(
            exchange_name="events",
            routing_key=event_type,
            message=json.dumps(message).encode(),
            properties={"content_type": "application/json"}
        )
        
    async def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Регистрация обработчика события
        
        Args:
            event_type: Тип события
            handler: Функция-обработчик
        """
        self.handlers[event_type] = handler
        
        # Создание очереди для события, если она еще не существует
        queue_name = f"queue.{event_type}"
        await self.rabbitmq.declare_queue(queue_name, durable=True)
        await self.rabbitmq.bind_queue(queue_name, "events", event_type)
        
        # Начало потребления сообщений
        async def message_processor(message):
            async with message.process():
                data = json.loads(message.body.decode())
                event_handler = self.handlers.get(data["event_type"])
                if event_handler:
                    try:
                        await event_handler(data["payload"])
                    except Exception as e:
                        logging.error(f"Error processing event {data['event_type']}: {e}")
                
        await self.rabbitmq.consume_queue(queue_name, message_processor)
```

## Создание локализованных сообщений

```python
from typing import Dict, Any, Optional
import json
import os

class Localizer:
    """
    Класс для работы с локализацией сообщений
    """
    def __init__(self, locale_path: str = "locale"):
        """
        Инициализация локализатора
        
        Args:
            locale_path: Путь к директории с файлами локализации
        """
        self.locale_path = locale_path
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_locale = "en"
        
        # Загрузка всех доступных локализаций
        self._load_translations()
        
    def _load_translations(self) -> None:
        """Загрузка всех файлов локализации"""
        for filename in os.listdir(self.locale_path):
            if filename.endswith(".json"):
                locale = filename.split(".")[0]
                with open(os.path.join(self.locale_path, filename), "r", encoding="utf-8") as f:
                    self.translations[locale] = json.load(f)
        
    def get_text(self, key: str, locale: str, **kwargs) -> str:
        """
        Получение локализованного текста
        
        Args:
            key: Ключ сообщения
            locale: Код языка
            **kwargs: Параметры для форматирования
            
        Returns:
            Локализованный текст
        """
        # Если локаль недоступна, используем дефолтную
        if locale not in self.translations:
            locale = self.default_locale
            
        # Если ключ не найден в указанной локали, ищем в дефолтной
        text = self.translations.get(locale, {}).get(key)
        if text is None:
            text = self.translations.get(self.default_locale, {}).get(key, f"MISSING_KEY:{key}")
            
        # Форматируем текст с переданными параметрами
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
```

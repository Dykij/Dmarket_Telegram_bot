# Примеры использования ключевых функций и классов проекта

## Пример использования Redis с автоматическим переподключением

```python
from common.redis_auto_reconnect import RedisAutoReconnect
import asyncio
import logging

async def example_redis():
    # Инициализация клиента Redis с автоматическим переподключением
    redis_client = RedisAutoReconnect(
        host="redis", 
        port=6379,
        max_reconnect_attempts=5,
        reconnect_delay=1.0
    )
    
    try:
        # Подключение к Redis
        await redis_client.connect()
        
        # Использование Redis
        await redis_client.set("key", "value")
        result = await redis_client.get("key")
        logging.info(f"Получено значение из Redis: {result}")
        
        # Хэш-таблицы
        await redis_client.hset("hash_key", "field", "hash_value")
        hash_result = await redis_client.hget("hash_key", "field")
        
        # Списки
        await redis_client.rpush("list_key", "item1", "item2")
        list_items = await redis_client.lrange("list_key", 0, -1)
        
        # Установка TTL для ключа
        await redis_client.set("expiring_key", "will_expire", expire=60)  # 60 секунд
        
    finally:
        # Закрытие соединения
        await redis_client.close()
```

## Пример использования RabbitMQ с автоматическим переподключением

```python
from common.rabbitmq_auto_reconnect import RabbitMQAutoReconnect
import asyncio
import json
import logging

async def example_rabbitmq():
    # Инициализация клиента RabbitMQ с автоматическим переподключением
    rabbitmq_client = RabbitMQAutoReconnect(
        host="rabbitmq",
        port=5672,
        login="guest",
        password="guest",
        max_reconnect_attempts=5,
        reconnect_delay=1.0
    )
    
    try:
        # Подключение к RabbitMQ
        await rabbitmq_client.connect()
        
        # Объявление очереди
        await rabbitmq_client.declare_queue("example_queue", durable=True)
        
        # Публикация сообщения
        message = {"data": "example", "timestamp": "2023-01-01T12:00:00"}
        await rabbitmq_client.publish_message(
            exchange_name="",
            routing_key="example_queue",
            message=json.dumps(message).encode(),
            properties={"content_type": "application/json"}
        )
        
        # Настройка обработчика сообщений
        async def message_handler(message):
            async with message.process():
                data = json.loads(message.body.decode())
                logging.info(f"Получено сообщение: {data}")
                # Обработка сообщения
                
        # Начало потребления сообщений
        await rabbitmq_client.consume_queue("example_queue", message_handler)
        
    finally:
        # Закрытие соединения
        await rabbitmq_client.close()
```

## Пример использования Telegram-бота на aiogram 3.x

```python
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import logging

# Инициализация бота и диспетчера
bot = Bot(token="YOUR_BOT_TOKEN")
router = Router()

# Определение состояний
class UserStates(StatesGroup):
    waiting_for_item = State()
    waiting_for_price = State()
    
# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в мониторинг цен DMarket! "
        "Используйте /track чтобы начать отслеживание предмета."
    )

# Обработчик команды /track
@router.message(Command("track"))
async def cmd_track(message: types.Message, state: FSMContext):
    await message.answer("Введите название предмета, который хотите отслеживать:")
    await state.set_state(UserStates.waiting_for_item)

# Обработка ввода предмета
@router.message(UserStates.waiting_for_item)
async def process_item(message: types.Message, state: FSMContext):
    await state.update_data(item=message.text)
    await message.answer("Введите целевую цену для отслеживания:")
    await state.set_state(UserStates.waiting_for_price)

# Обработка ввода цены
@router.message(UserStates.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        user_data = await state.get_data()
        item_name = user_data["item"]
        
        # Здесь код для добавления отслеживания в базу данных
        
        await message.answer(
            f"Отслеживание настроено для предмета {item_name} с целевой ценой {price}."
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число для цены.")

# Регистрация хэндлеров и запуск
async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

## Пример использования парсера DMarket

```python
from price_monitoring.parsers.dmarket import DMarketParser
import asyncio
import logging

async def example_parser():
    # Инициализация парсера
    parser = DMarketParser(
        use_proxy=True,
        proxy_file_path="utils_mount/dmarket_proxies.txt",
        request_delay=2.0
    )
    
    try:
        # Поиск предметов
        items = await parser.search_items(
            game="cs2",
            title="AK-47 | Redline",
            limit=10
        )
        
        # Обработка результатов
        for item in items:
            logging.info(f"Название: {item.title}")
            logging.info(f"Цена: {item.price}")
            logging.info(f"Идентификатор: {item.item_id}")
            
        # Получение дополнительной информации о конкретном предмете
        item_details = await parser.get_item_details(items[0].item_id)
        logging.info(f"Детали предмета: {item_details}")
        
    finally:
        await parser.close()
```

## Пример структурированного логирования

```python
import json_logging
import logging
import sys

def setup_logging():
    # Настройка структурированного JSON-логирования
    json_logging.init_non_web(enable_json=True)
    logger = logging.getLogger("dmarket_monitoring")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    
    return logger

logger = setup_logging()

# Использование логирования
logger.info("Приложение запущено", extra={"component": "main", "user_id": 12345})
logger.error(
    "Ошибка подключения", 
    extra={
        "component": "parser", 
        "endpoint": "dmarket_api", 
        "status_code": 503
    }
)
```

## Пример трассировки с Zipkin

```python
import aiozipkin
from aiohttp import ClientSession
import asyncio

async def example_tracing():
    # Создание трассировщика
    zipkin_address = "http://zipkin:9411"
    endpoint = aiozipkin.create_endpoint(
        service_name="dmarket_monitoring"
    )
    tracer = await aiozipkin.create(zipkin_address, endpoint)
    
    # Использование трассировки
    with tracer.new_trace(sampled=True) as span:
        # Добавление тегов к спану
        span.name("parse_dmarket")
        span.tag("user_id", "12345")
        span.kind(aiozipkin.CLIENT)
        
        # Создание дочернего спана
        with tracer.new_child(span.context) as child_span:
            child_span.name("http_request")
            
            # Выполнение HTTP-запроса с трассировкой
            async with ClientSession() as session:
                # Добавление заголовков трассировки
                headers = {}
                child_span.inject(headers)
                
                # Выполнение запроса
                try:
                    async with session.get(
                        "https://api.dmarket.com/items",
                        headers=headers
                    ) as response:
                        data = await response.json()
                        # Добавление информации о результате
                        child_span.tag("status_code", str(response.status))
                except Exception as e:
                    # Логирование ошибки в спан
                    child_span.tag("error", "true")
                    child_span.tag("error.message", str(e))
                    raise
    
    await tracer.close()
```

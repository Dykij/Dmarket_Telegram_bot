"""
DMarket Worker - основной обработчик данных с DMarket.

Этот модуль отвечает за:
1. Получение данных об отдельных предметах из очереди RabbitMQ ('dmarket_raw_items_queue')
2. Сохранение данных о предметах в Redis

Для работы требуется:
- Настроенный экземпляр RabbitMQ
- Настроенный экземпляр Redis
"""

import asyncio
import logging
import aio_pika # Import for message processing

from dotenv import load_dotenv

# Import functions to get env vars, not the vars themselves
from common.env_var import (
    # Removed unused env vars for arbitrage/notifications
    # get_dmarket_commission_percent, get_profit_threshold_usd,
    # get_telegram_api_token, get_telegram_whitelist,
    get_log_level,
    get_rabbitmq_host,
    get_rabbitmq_password,
    get_rabbitmq_port,
    get_rabbitmq_user,
    get_rabbitmq_virtual_host,
    get_redis_db,
    get_redis_host,
    get_redis_port,
)
# Import connector
from common.rabbitmq_connector import RabbitMQConnector
from common.redis_connector import RedisConnector
from price_monitoring.logs import setup_logging
# Removed old queue/payload imports
# from price_monitoring.queues.rabbitmq.dmarket_item_queue import (
#     AbstractDMarketItemQueue, DMarketItemsPayload)
# Import the specific item model and the new queue name
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.queues.rabbitmq.raw_items_queue import DMARKET_RAW_ITEMS_QUEUE_NAME
from price_monitoring.storage.dmarket import DMarketStorage

# Load environment variables from .env file
load_dotenv("worker.dev.env")  # Ensure this points to the correct env file

# Use the getter functions for env vars
LOG_LEVEL = get_log_level()
setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

# Removed unused constants
# DMARKET_COMMISSION_PERCENT = get_dmarket_commission_percent()
# PROFIT_THRESHOLD_USD = get_profit_threshold_usd()
# TELEGRAM_API_TOKEN = get_telegram_api_token()
# TELEGRAM_WHITELIST_STR = get_telegram_whitelist()
# TELEGRAM_WHITELIST_LIST = TELEGRAM_WHITELIST_STR.split(",") if TELEGRAM_WHITELIST_STR else []

# New function to process a single raw item message
async def process_raw_item_message(message: aio_pika.IncomingMessage, storage: DMarketStorage):
    """
    Обрабатывает сообщение с необработанными данными предмета DMarket.

    Десериализует данные и сохраняет предмет в Redis.

    Args:
        message: Входящее сообщение RabbitMQ.
        storage: Хранилище DMarketStorage для сохранения данных.
    """
    async with message.process(): # Acknowledge message upon successful processing
        try:
            item = DMarketItem.load_bytes(message.body)
            logger.debug(f"Received item: {item.item_id} - {item.title}")
            await storage.save_item(item)
            logger.info(f"Successfully saved item {item.item_id} ({item.title}) to Redis.")
        except Exception as e:
            logger.error(f"Failed to process message: {e}. Message body (first 100 bytes): {message.body[:100]}...")
            # Consider moving to a dead-letter queue instead of just logging


async def main():
    """
    Главная функция запуска и управления работой DMarket воркера.

    Эта функция выполняет следующие действия:
    1. Инициализирует подключения к RabbitMQ и Redis
    2. Создает хранилище DMarketStorage
    3. Настраивает прослушивание очереди 'dmarket_raw_items_queue'
    4. Обрабатывает получаемые данные (десериализует и сохраняет в Redis)
    5. Обеспечивает корректное завершение работы при получении сигналов остановки
    """
    logger.info("Starting DMarket Worker...")

    # Use getter functions inside main for connection details
    rabbitmq_connector = RabbitMQConnector(
        host=get_rabbitmq_host(),
        port=str(get_rabbitmq_port()),  # Преобразуем port в строку
        user=get_rabbitmq_user(),
        password=get_rabbitmq_password(),
        virtual_host=get_rabbitmq_virtual_host(),
    )
    # Преобразуем параметры Redis в соответствующие типы
    redis_connector = RedisConnector(
        host=get_redis_host(), port=int(get_redis_port()), db=int(get_redis_db())
    )

    channel = None # Define channel variable
    redis_client = None

    try:
        connection = await rabbitmq_connector.connect()
        channel = await connection.channel()
        # Set prefetch count to limit the number of unacknowledged messages
        await channel.set_qos(prefetch_count=10)

        # Declare the queue to ensure it exists
        queue = await channel.declare_queue(DMARKET_RAW_ITEMS_QUEUE_NAME, durable=True)

        redis_client = await redis_connector.get_client()
        dmarket_storage = DMarketStorage(redis_client=redis_client)

        logger.info(f"Worker is listening for messages on queue '{DMARKET_RAW_ITEMS_QUEUE_NAME}'...")

        # Consume messages from the queue
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await process_raw_item_message(message, dmarket_storage)

    except asyncio.CancelledError:
        logger.info("Worker task cancelled.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred in the worker main loop: {e}")
    finally:
        logger.info("Shutting down DMarket Worker...")
        # Close channel first if it exists
        if channel and not channel.is_closed:
            await channel.close()
            logger.info("RabbitMQ channel closed.")
        if rabbitmq_connector:
            await rabbitmq_connector.close() # Connection close should handle channel closure too
        if redis_connector:
            await redis_connector.close()
        logger.info("DMarket Worker stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")

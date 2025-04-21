"""
DMarket Worker Module

This module serves as the main worker for processing DMarket data.
It is responsible for:
1. Retrieving individual item data from the RabbitMQ queue ('dmarket_raw_items_queue')
2. Storing item data in Redis

Requirements:
- Configured RabbitMQ instance
- Configured Redis instance

The worker continuously listens for messages on the queue, processes them,
and stores the results in Redis for later retrieval by the Telegram bot.
"""

import asyncio
import logging
from typing import Optional

import aio_pika  # Library for RabbitMQ interaction

from dotenv import load_dotenv

# Import functions to get environment variables
from common.env_var import (
    # Environment variables for logging
    get_log_level,

    # Environment variables for RabbitMQ connection
    get_rabbitmq_host,
    get_rabbitmq_password,
    get_rabbitmq_port,
    get_rabbitmq_user,
    get_rabbitmq_virtual_host,

    # Environment variables for Redis connection
    get_redis_db,
    get_redis_host,
    get_redis_port,
)
# Import connectors for external services
from common.rabbitmq_connector import RabbitMQConnector
from common.redis_connector import RedisConnector
from price_monitoring.logs import setup_logging

# Import the DMarket item model for deserialization
from price_monitoring.models.dmarket import DMarketItem
# Import the queue name constant
from price_monitoring.queues.rabbitmq.raw_items_queue import DMARKET_RAW_ITEMS_QUEUE_NAME
# Import storage class for Redis operations
from price_monitoring.storage.dmarket import DMarketStorage

# Load environment variables from .env file
load_dotenv("worker.dev.env")  # Ensure this points to the correct env file

# Set up logging with the configured log level
LOG_LEVEL = get_log_level()
setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

# Removed unused constants
# DMARKET_COMMISSION_PERCENT = get_dmarket_commission_percent()
# PROFIT_THRESHOLD_USD = get_profit_threshold_usd()
# TELEGRAM_API_TOKEN = get_telegram_api_token()
# TELEGRAM_WHITELIST_STR = get_telegram_whitelist()
# TELEGRAM_WHITELIST_LIST = TELEGRAM_WHITELIST_STR.split(",") if TELEGRAM_WHITELIST_STR else []

async def process_raw_item_message(message: aio_pika.IncomingMessage, storage: DMarketStorage) -> None:
    """
    Process a raw item message from the RabbitMQ queue.

    This function deserializes the message body into a DMarketItem object
    and saves it to Redis using the provided storage instance.

    The message is automatically acknowledged when the processing is complete
    or rejected if an exception occurs during processing.

    Args:
        message: The incoming RabbitMQ message containing serialized item data
        storage: DMarketStorage instance for saving the item to Redis

    Returns:
        None

    Raises:
        Exception: Logs but doesn't propagate exceptions to allow continuous operation
    """
    async with message.process():  # Acknowledge message upon successful processing
        try:
            # Deserialize the message body into a DMarketItem object
            item = DMarketItem.load_bytes(message.body)
            logger.debug(f"Received item: {item.item_id} - {item.title}")

            # Save the item to Redis
            await storage.save_item(item)
            logger.info(f"Successfully saved item {item.item_id} ({item.title}) to Redis.")
        except Exception as e:
            # Log the error and truncate the message body to avoid flooding the logs
            logger.error(f"Failed to process message: {e}. Message body (first 100 bytes): {message.body[:100]}...")
            # Consider moving to a dead-letter queue instead of just logging


async def main() -> None:
    """
    Main function for running and managing the DMarket worker.

    This function performs the following actions:
    1. Initializes connections to RabbitMQ and Redis
    2. Creates a DMarketStorage instance for Redis operations
    3. Sets up listening on the 'dmarket_raw_items_queue' queue
    4. Processes incoming messages (deserializes and saves to Redis)
    5. Ensures proper cleanup of resources on shutdown

    The worker runs indefinitely until interrupted or an unrecoverable error occurs.

    Returns:
        None
    """
    logger.info("Starting DMarket Worker...")

    # Initialize RabbitMQ connector with connection details from environment variables
    rabbitmq_connector = RabbitMQConnector(
        host=get_rabbitmq_host(),
        port=str(get_rabbitmq_port()),  # Convert port to string as required by the connector
        user=get_rabbitmq_user(),
        password=get_rabbitmq_password(),
        virtual_host=get_rabbitmq_virtual_host(),
    )

    # Initialize Redis connector with connection details from environment variables
    redis_connector = RedisConnector(
        host=get_redis_host(), 
        port=int(get_redis_port()), 
        db=int(get_redis_db())
    )

    # Initialize variables for resources that need to be cleaned up
    channel: Optional[aio_pika.Channel] = None
    redis_client = None

    try:
        # Connect to RabbitMQ and create a channel
        connection = await rabbitmq_connector.connect()
        channel = await connection.channel()

        # Set prefetch count to limit the number of unacknowledged messages
        # This prevents the worker from being overwhelmed with too many messages
        await channel.set_qos(prefetch_count=10)

        # Declare the queue to ensure it exists
        # The durable=True parameter ensures the queue survives broker restarts
        queue = await channel.declare_queue(DMARKET_RAW_ITEMS_QUEUE_NAME, durable=True)

        # Connect to Redis and create a storage instance
        redis_client = await redis_connector.get_client()
        dmarket_storage = DMarketStorage(redis_client=redis_client)

        logger.info(f"Worker is listening for messages on queue '{DMARKET_RAW_ITEMS_QUEUE_NAME}'...")

        # Consume messages from the queue in an infinite loop
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await process_raw_item_message(message, dmarket_storage)

    except asyncio.CancelledError:
        # Handle graceful cancellation (e.g., when the event loop is stopped)
        logger.info("Worker task cancelled.")
    except Exception as e:
        # Log any unexpected errors
        logger.exception(f"An unexpected error occurred in the worker main loop: {e}")
    finally:
        # Ensure proper cleanup of resources
        logger.info("Shutting down DMarket Worker...")

        # Close the RabbitMQ channel if it exists and is not already closed
        if channel and not channel.is_closed:
            await channel.close()
            logger.info("RabbitMQ channel closed.")

        # Close the RabbitMQ connection
        if rabbitmq_connector:
            await rabbitmq_connector.close()

        # Close the Redis connection
        if redis_connector:
            await redis_connector.close()

        logger.info("DMarket Worker stopped.")


if __name__ == "__main__":
    try:
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        logger.info("Worker stopped by user.")

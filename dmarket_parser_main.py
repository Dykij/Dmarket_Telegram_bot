"""DMarket Parser Main Module

This module serves as the main entry point for the DMarket parser application.
It continuously fetches items from the DMarket API and publishes them to a RabbitMQ queue
for further processing by worker nodes.

The parser supports multiple game IDs and implements retry logic with exponential backoff
to handle API errors gracefully.
"""

# Применяем патчи для совместимости с aioredis 2.0.0+

import asyncio
import logging
import time

from dotenv import load_dotenv

from common.dmarket_auth import DMarketAuth
from common.env_var import API_REQUEST_DELAY_SECONDS  # Delay between API requests in seconds
from common.env_var import CURRENCY  # Currency for item prices (e.g., USD)
from common.env_var import DMARKET_GAME_IDS  # Comma-separated list of game IDs to parse
from common.env_var import DMARKET_PUBLIC_KEY  # DMarket API public key
from common.env_var import DMARKET_SECRET_KEY  # DMarket API secret key
from common.env_var import ITEMS_PER_PAGE  # Number of items to fetch per API request
from common.env_var import LOG_LEVEL  # Logging level (INFO, DEBUG, etc.)
from common.env_var import PARSE_DELAY_SECONDS  # Delay between parsing cycles in seconds
from common.env_var import RABBITMQ_HOST  # RabbitMQ host address
from common.env_var import RABBITMQ_PASSWORD  # RabbitMQ password
from common.env_var import RABBITMQ_PORT  # RabbitMQ port
from common.env_var import RABBITMQ_USER  # RabbitMQ username
from common.env_var import RABBITMQ_VIRTUAL_HOST  # RabbitMQ virtual host
from common.rabbitmq_connector import RabbitMQConnector
from price_monitoring.logs import setup_logging
from price_monitoring.parsers.dmarket.items_parser import DMarketItemsParser
from price_monitoring.queues.rabbitmq.raw_items_queue import (DMARKET_RAW_ITEMS_QUEUE_NAME,
                                                              DMarketRawItemsQueuePublisher)
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory

# Load environment variables from .env file
load_dotenv("dmarket_parser.dev.env")
setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)


async def parse_game(
    session_factory: AiohttpSessionFactory,
    dmarket_auth: DMarketAuth,
    publisher: DMarketRawItemsQueuePublisher,
    game_id: str,
    currency: str,
    items_per_page: int,
    api_request_delay: float,
) -> int:
    """Parses all items for a specific game ID using DMarketItemsParser.

    This function initializes a DMarketItemsParser with the provided parameters,
    fetches items from the DMarket API, and publishes them to a RabbitMQ queue.

    Args:
        session_factory: Factory for creating HTTP sessions
        dmarket_auth: Authentication credentials for DMarket API
        publisher: Queue publisher for sending items to RabbitMQ
        game_id: ID of the game to parse items for
        currency: Currency for item prices (e.g., USD)
        items_per_page: Number of items to fetch per API request
        api_request_delay: Delay between API requests in seconds

    Returns:
        int: Total number of items successfully published to the queue

    Raises:
        Exception: Logs but doesn't propagate exceptions to allow continuous operation
    """
    logger.info(f"Starting parsing for game: {game_id}")
    total_items_published = 0
    parser = DMarketItemsParser(
        session_factory=session_factory,
        dmarket_auth=dmarket_auth,
        game_id=game_id,
        currency=currency,
        items_per_page=items_per_page,
        api_request_delay_seconds=api_request_delay,
    )

    try:
        # Parse items from DMarket API
        items, errors = await parser.parse()

        # Log any errors encountered during parsing
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during parsing game {game_id}:")
            for i, error in enumerate(errors[:5]):  # Log first 5 errors
                logger.warning(f"  Error {i + 1}: {error}")
            if len(errors) > 5:
                logger.warning(f"  ... and {len(errors) - 5} more errors.")

        # Publish parsed items to the queue
        if items:
            logger.info(f"Parsed {len(items)} items for game {game_id}. Publishing to queue...")
            published_count = 0
            for item in items:
                try:
                    await publisher.publish_item(item)
                    published_count += 1
                except Exception as pub_err:
                    logger.error(
                        f"Failed to publish item {item.item_id} for game {game_id}: {pub_err}"
                    )
                    # Optional: Implement retry or dead-letter queue logic here
            total_items_published = published_count
            logger.info(
                f"Successfully published {published_count}/{len(items)} items for game {game_id}."
            )
        else:
            logger.info(f"No items parsed or published for game {game_id}.")

    except Exception as e:
        logger.exception(f"Critical error during parsing game {game_id}: {e}")
        # Optional: implement retry logic or specific error handling

    logger.info(
        f"Finished parsing cycle for game: {game_id}. Total items published: {total_items_published}"
    )

    return total_items_published


async def main() -> None:
    """Main function to run the DMarket parser.

    This function:
    1. Initializes the HTTP session factory for making API requests
    2. Sets up DMarket authentication
    3. Establishes connection to RabbitMQ
    4. Creates a publisher for sending items to the queue
    5. Runs an infinite loop that:
       - Parses items for each configured game ID
       - Waits for the configured delay between cycles
       - Handles errors gracefully
    6. Ensures proper cleanup of resources on shutdown

    Returns:
        None
    """
    logger.info("Starting DMarket Parser...")

    # Parse game IDs from environment variable
    game_ids = [gid.strip() for gid in DMARKET_GAME_IDS.split(",") if gid.strip()]
    if not game_ids:
        logger.error(
            "No DMarket game IDs specified in DMARKET_GAME_IDS environment variable. Exiting."
        )
        return

    logger.info(f"Target games: {game_ids}")

    # Initialize Session Factory for HTTP requests
    session_factory = AiohttpSessionFactory()

    # Initialize DMarket Auth with API keys
    if not DMARKET_PUBLIC_KEY or not DMARKET_SECRET_KEY:
        logger.error(
            "DMarket API keys (DMARKET_PUBLIC_KEY, DMARKET_SECRET_KEY) are not set. Exiting."
        )
        return
    dmarket_auth = DMarketAuth(public_key=DMARKET_PUBLIC_KEY, secret_key=DMARKET_SECRET_KEY)

    # Initialize RabbitMQ Connector for message queue
    rabbitmq_connector = RabbitMQConnector(
        host=RABBITMQ_HOST,
        port=str(RABBITMQ_PORT),  # Ensure port is string if constructor expects it
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
        virtual_host=RABBITMQ_VIRTUAL_HOST,
    )

    # Initialize Queue Publisher
    publisher = None

    try:
        # Connect to RabbitMQ
        await rabbitmq_connector.connect()

        # Create the specific publisher for raw items
        publisher = DMarketRawItemsQueuePublisher(
            connector=rabbitmq_connector, queue_name=DMARKET_RAW_ITEMS_QUEUE_NAME
        )

        # Main parsing loop
        while True:
            logger.info("Starting new parsing cycle...")
            start_cycle_time = time.monotonic()

            # Create parsing tasks for each game ID
            tasks = [
                parse_game(
                    session_factory=session_factory,
                    dmarket_auth=dmarket_auth,
                    publisher=publisher,
                    game_id=game_id,
                    currency=CURRENCY,
                    items_per_page=ITEMS_PER_PAGE,
                    api_request_delay=API_REQUEST_DELAY_SECONDS,
                )
                for game_id in game_ids
            ]

            # Run all parsing tasks concurrently
            await asyncio.gather(*tasks)

            # Calculate cycle duration and wait time for next cycle
            end_cycle_time = time.monotonic()
            cycle_duration = end_cycle_time - start_cycle_time
            logger.info(f"Parsing cycle finished in {cycle_duration:.2f} seconds.")

            # Wait until next cycle, respecting minimum delay
            wait_time = max(0, PARSE_DELAY_SECONDS - cycle_duration)
            logger.info(f"Waiting {wait_time:.2f} seconds until the next cycle.")
            await asyncio.sleep(wait_time)

    except asyncio.CancelledError:
        logger.info("Parser task cancelled.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred in the main loop: {e}")
    finally:
        # Ensure proper cleanup of resources
        logger.info("Shutting down DMarket Parser...")
        if publisher:
            await publisher.close()  # Close publisher channel
        if rabbitmq_connector:
            await rabbitmq_connector.close()
        # Close aiohttp sessions
        await session_factory.close_all_sessions()
        logger.info("DMarket Parser stopped.")


if __name__ == "__main__":
    try:
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        logger.info("Parser stopped by user.")

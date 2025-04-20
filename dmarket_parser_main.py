import asyncio
import logging
import time

from dotenv import load_dotenv

from common.env_var import (
    API_REQUEST_DELAY_SECONDS,
    CURRENCY,
    DMARKET_GAME_IDS,
    ITEMS_PER_PAGE,
    LOG_LEVEL,
    PARSE_DELAY_SECONDS,
    RABBITMQ_HOST,
    RABBITMQ_PASSWORD,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_VIRTUAL_HOST,
    DMARKET_PUBLIC_KEY, # Added
    DMARKET_SECRET_KEY, # Added
)
from common.rabbitmq_connector import RabbitMQConnector
from price_monitoring.logs import setup_logging
from price_monitoring.parsers.dmarket.items_parser import DMarketItemsParser
from price_monitoring.queues.rabbitmq.raw_items_queue import (
    DMarketRawItemsQueuePublisher, DMARKET_RAW_ITEMS_QUEUE_NAME
)
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory
from common.dmarket_auth import DMarketAuth


# Load environment variables from .env file
load_dotenv("dmarket_parser.dev.env")
setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)


# Rewritten parse_game function
async def parse_game(
    session_factory: AiohttpSessionFactory,
    dmarket_auth: DMarketAuth,
    publisher: DMarketRawItemsQueuePublisher,
    game_id: str,
    currency: str,
    items_per_page: int,
    api_request_delay: float,
):
    """Parses all items for a specific game ID using DMarketItemsParser."""
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
        items, errors = await parser.parse()

        if errors:
            logger.warning(f"Encountered {len(errors)} errors during parsing game {game_id}:")
            for i, error in enumerate(errors[:5]): # Log first 5 errors
                logger.warning(f"  Error {i+1}: {error}")
            if len(errors) > 5:
                logger.warning(f"  ... and {len(errors) - 5} more errors.")

        if items:
            logger.info(f"Parsed {len(items)} items for game {game_id}. Publishing to queue...")
            published_count = 0
            for item in items:
                try:
                    await publisher.publish_item(item)
                    published_count += 1
                except Exception as pub_err:
                    logger.error(f"Failed to publish item {item.item_id} for game {game_id}: {pub_err}")
                    # Optional: Implement retry or dead-letter queue logic here
            total_items_published = published_count
            logger.info(f"Successfully published {published_count}/{len(items)} items for game {game_id}.")
        else:
            logger.info(f"No items parsed or published for game {game_id}.")

    except Exception as e:
        logger.exception(f"Critical error during parsing game {game_id}: {e}")
        # Optional: implement retry logic or specific error handling

    logger.info(
        f"Finished parsing cycle for game: {game_id}. Total items published: {total_items_published}"
    )


async def main():
    """Main function to run the DMarket parser."""
    logger.info("Starting DMarket Parser...")

    # Разбиваем длинную строку на несколько строк
    game_ids = [gid.strip() for gid in DMARKET_GAME_IDS.split(",") if gid.strip()]
    if not game_ids:
        logger.error(
            "No DMarket game IDs specified in DMARKET_GAME_IDS environment variable. Exiting."
        )
        return

    logger.info(f"Target games: {game_ids}")

    # Initialize Session Factory
    # Assuming default constructor is sufficient, or add proxy/TLS settings if needed
    session_factory = AiohttpSessionFactory()

    # Initialize DMarket Auth
    if not DMARKET_PUBLIC_KEY or not DMARKET_SECRET_KEY:
        logger.error("DMarket API keys (DMARKET_PUBLIC_KEY, DMARKET_SECRET_KEY) are not set. Exiting.")
        return
    dmarket_auth = DMarketAuth(public_key=DMARKET_PUBLIC_KEY, secret_key=DMARKET_SECRET_KEY)

    # Initialize RabbitMQ Connector
    rabbitmq_connector = RabbitMQConnector(
        host=RABBITMQ_HOST,
        port=str(RABBITMQ_PORT), # Ensure port is string if constructor expects it
        user=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
        virtual_host=RABBITMQ_VIRTUAL_HOST,
    )

    # Initialize Queue Publisher
    publisher = None

    try:
        await rabbitmq_connector.connect()
        # Create the specific publisher for raw items
        publisher = DMarketRawItemsQueuePublisher(connector=rabbitmq_connector, queue_name=DMARKET_RAW_ITEMS_QUEUE_NAME)
        # No need to call create_publisher with Abstract class anymore

        while True:
            logger.info("Starting new parsing cycle...")
            start_cycle_time = time.monotonic()

            # Prepare arguments for parse_game
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
            await asyncio.gather(*tasks)

            end_cycle_time = time.monotonic()
            cycle_duration = end_cycle_time - start_cycle_time
            logger.info(f"Parsing cycle finished in {cycle_duration:.2f} seconds.")

            wait_time = max(0, PARSE_DELAY_SECONDS - cycle_duration)
            logger.info(f"Waiting {wait_time:.2f} seconds until the next cycle.")
            await asyncio.sleep(wait_time)

    except asyncio.CancelledError:
        logger.info("Parser task cancelled.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred in the main loop: {e}")
    finally:
        logger.info("Shutting down DMarket Parser...")
        if publisher:
             await publisher.close() # Close publisher channel
        if rabbitmq_connector:
            await rabbitmq_connector.close()
        # Close aiohttp sessions if the factory provides a method
        # Assuming AiohttpSessionFactory might have a close method like this:
        await session_factory.close_all_sessions() # Or similar method if exists
        logger.info("DMarket Parser stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Parser stopped by user.")

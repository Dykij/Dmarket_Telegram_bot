"""Parser entry point for Dmarket Telegram Bot.

This script runs a distributed parser instance that coordinates
with other instances through Redis.
"""

import asyncio
import logging
import os
import sys
from uuid import uuid4

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.dmarket_auth import DMarketAuth
from common.rabbitmq_connector import RabbitMQConnector
from common.redis_connector import RedisConnector
from price_monitoring.queues.rabbitmq.raw_items_queue import DMarketRawItemsQueuePublisher
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory
from scalability.distributed_parser import DistributedParser
from scalability.proxy_manager import ProxyManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the distributed parser."""
    # Create a unique instance ID
    instance_id = str(uuid4())
    logger.info(f"Starting parser instance {instance_id}")

    redis_connector = None
    rabbitmq_connector = None
    proxy_manager = None

    try:
        # Initialize Redis connector
        redis_connector = RedisConnector(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=os.environ.get("REDIS_PORT", "6379"),
            db=os.environ.get("REDIS_DB", "0"),
        )
        redis_client = await redis_connector.get_client()

        # Initialize RabbitMQ connector
        rabbitmq_connector = RabbitMQConnector(
            host=os.environ.get("RABBITMQ_HOST", "localhost"),
            port=os.environ.get("RABBITMQ_PORT", "5672"),
            user=os.environ.get("RABBITMQ_USER", "guest"),
            password=os.environ.get("RABBITMQ_PASSWORD", "guest"),
            virtual_host=os.environ.get("RABBITMQ_VHOST", "/"),
        )
        await rabbitmq_connector.connect()

        # Initialize proxy manager
        proxy_manager = ProxyManager(
            redis_client=redis_client,
            instance_id=instance_id,
            max_proxies_per_instance=int(os.environ.get("MAX_PROXIES_PER_INSTANCE", "0")),
        )
        await proxy_manager.start()

        # Allocate proxies for this instance
        proxies = await proxy_manager.allocate_proxies(
            count=int(os.environ.get("PROXY_COUNT", "0"))
        )
        logger.info(f"Allocated {len(proxies)} proxies")

        # Create session factory with proxies
        session_factory = AiohttpSessionFactory()
        for proxy in proxies:
            session_factory.create_session_with_proxy(proxy)

        # Initialize DMarket auth
        dmarket_auth = DMarketAuth(
            public_key=os.environ.get("DMARKET_PUBLIC_KEY", ""),
            secret_key=os.environ.get("DMARKET_SECRET_KEY", ""),
        )

        # Create publisher
        publisher = DMarketRawItemsQueuePublisher(
            connector=rabbitmq_connector,
            queue_name=os.environ.get("RAW_ITEMS_QUEUE", "dmarket_raw_items_queue"),
        )

        # Initialize distributed parser
        parser = DistributedParser(
            redis_client=redis_client,
            instance_id=instance_id,
            lock_expiry=int(os.environ.get("LOCK_EXPIRY", "300")),
            heartbeat_interval=int(os.environ.get("HEARTBEAT_INTERVAL", "30")),
        )

        # Start the parser
        await parser.start(
            session_factory=session_factory, dmarket_auth=dmarket_auth, publisher=publisher
        )

    except asyncio.CancelledError:
        logger.info("Parser cancelled")
    except Exception as e:
        logger.exception(f"Error in parser: {e}")
    finally:
        # Clean up
        if proxy_manager:
            try:
                await proxy_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping proxy manager: {e}")

        if rabbitmq_connector:
            try:
                await rabbitmq_connector.close()
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}")

        if redis_connector:
            try:
                await redis_connector.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

        logger.info(f"Parser instance {instance_id} stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Parser stopped by user")

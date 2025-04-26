"""Worker entry point for Dmarket Telegram Bot.

This script runs a scalable worker instance that processes items
from the queue and can be scaled horizontally.
"""

import asyncio
import logging
import os
import sys
from uuid import uuid4

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.rabbitmq_connector import RabbitMQConnector
from common.redis_connector import RedisConnector
from scalability.scalable_worker import ScalableWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the scalable worker."""
    # Create a unique instance ID
    instance_id = str(uuid4())
    logger.info(f"Starting worker instance {instance_id}")

    redis_connector = None
    rabbitmq_connector = None

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

        # Initialize worker
        worker = ScalableWorker(
            redis_client=redis_client,
            rabbitmq_connector=rabbitmq_connector,
            instance_id=instance_id,
            heartbeat_interval=int(os.environ.get("HEARTBEAT_INTERVAL", "30")),
            batch_size=int(os.environ.get("BATCH_SIZE", "100")),
            processing_timeout=int(os.environ.get("PROCESSING_TIMEOUT", "300")),
        )

        # Start the worker
        await worker.start()

    except asyncio.CancelledError:
        logger.info("Worker cancelled")
    except Exception as e:
        logger.exception(f"Error in worker: {e}")
    finally:
        # Clean up
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

        logger.info(f"Worker instance {instance_id} stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")

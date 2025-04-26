"""Example integration module for improved Redis and RabbitMQ clients.

This module provides example code for integrating the improved Redis and RabbitMQ
auto-reconnect clients into your project. It can be used as a reference for
updating existing code or implementing new features.
"""

import asyncio
import json
import logging

from common.rabbitmq_auto_reconnect import RabbitMQAutoReconnect
from common.redis_auto_reconnect import RedisAutoReconnect
from price_monitoring.constants.dmarket_api import DEFAULT_CURRENCY
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.parsers.dmarket.improved_dmarket_parser import ImprovedDMarketParser

logger = logging.getLogger(__name__)


class DMarketIntegrationExample:
    """Example integration class showing how to use the improved components.

    This class demonstrates integration of:
    1. Improved DMarket parser with constants
    2. Redis auto-reconnect client
    3. RabbitMQ auto-reconnect client
    """

    def __init__(
        self,
        redis_url: str,
        rabbitmq_url: str,
        use_proxy: bool = False,
        redis_db: int = 0,
    ):
        """Initialize the integration example.

        Args:
            redis_url: URL for Redis connection
            rabbitmq_url: URL for RabbitMQ connection
            use_proxy: Whether to use proxies for API requests
            redis_db: Redis database number to use
        """
        # Initialize components with improved clients
        self.redis_client = RedisAutoReconnect(redis_url=redis_url, db=redis_db)
        self.rabbitmq_client = RabbitMQAutoReconnect(rabbitmq_url=rabbitmq_url)
        self.dmarket_parser = ImprovedDMarketParser(use_proxy=use_proxy)

    async def process_market_items(
        self,
        game: str,
        limit: int = 100,
        exchange_name: str = "dmarket_items",
        queue_name: str = "processed_items",
        routing_key: str = "items.processed",
        redis_key_prefix: str = "dmarket:item:",
    ) -> list[DMarketItem]:
        """Process market items workflow demonstration.

        This method showcases:
        1. Fetching items from DMarket API
        2. Parsing the response
        3. Storing items in Redis
        4. Publishing messages to RabbitMQ

        Args:
            game: Game identifier (e.g., 'csgo')
            limit: Maximum number of items to retrieve
            exchange_name: RabbitMQ exchange name
            queue_name: RabbitMQ queue name
            routing_key: RabbitMQ routing key
            redis_key_prefix: Prefix for Redis keys

        Returns:
            List of processed DMarket items
        """
        try:
            # 1. Fetch items from DMarket API using improved parser
            response = await self.dmarket_parser.get_market_items(
                game=game, limit=limit, currency=DEFAULT_CURRENCY
            )

            # 2. Parse the response into DMarket items
            items = self.dmarket_parser.parse_items(response)
            logger.info(f"Retrieved {len(items)} items from DMarket API")

            # 3. Store items in Redis using auto-reconnect client
            for item in items:
                redis_key = f"{redis_key_prefix}{item.item_id}"
                item_data = item.to_dict()

                # Using the execute_with_retry method for reliable Redis operations
                await self.redis_client.execute_with_retry(
                    self.redis_client._redis.set,
                    redis_key,
                    json.dumps(item_data),
                    ex=3600,  # 1 hour expiration
                )

            # 4. Send notification to RabbitMQ for further processing
            await self.rabbitmq_client.get_connection()

            # Ensure exchange and queue exist
            await self.rabbitmq_client.get_exchange(exchange_name)
            await self.rabbitmq_client.get_queue(queue_name)
            await self.rabbitmq_client.bind_queue(queue_name, exchange_name, routing_key)

            # Publish message with items summary
            message_data = {
                "game": game,
                "item_count": len(items),
                "timestamp": asyncio.get_event_loop().time(),
            }

            await self.rabbitmq_client.publish(
                exchange_name=exchange_name, routing_key=routing_key, message_body=message_data
            )

            logger.info(f"Published items summary to RabbitMQ queue {queue_name}")
            return items

        except Exception as e:
            logger.error(f"Error processing market items: {e!s}", exc_info=True)
            raise

    async def close(self):
        """Close all connections and clean up resources."""
        await self.redis_client.close()
        await self.rabbitmq_client.close()
        await self.dmarket_parser.close()

    async def __aenter__(self):
        """Support for async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context."""
        await self.close()


# Example usage
async def run_integration_example():
    """Run the integration example."""
    # Initialize with environment variables in a real application
    integration = DMarketIntegrationExample(
        redis_url="redis://localhost:6379",
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        use_proxy=False,
    )

    try:
        # Process CS:GO items
        items = await integration.process_market_items(
            game="csgo", limit=50, redis_key_prefix="dmarket:csgo:item:"
        )

        # Print summary
        print(f"Processed {len(items)} CS:GO items")

    finally:
        # Ensure connections are closed
        await integration.close()


# Run the example if executed directly
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        asyncio.run(run_integration_example())
    except KeyboardInterrupt:
        print("Operation cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

"""Scalable worker for Dmarket Telegram Bot.

This module implements a worker that can be scaled horizontally
across multiple instances, with coordination through Redis.
"""

import asyncio
import contextlib
import json
import logging
import os
import uuid
from typing import Optional

from redis.asyncio import Redis

from common.rabbitmq_connector import RabbitMQConnector
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.queues.rabbitmq.raw_items_queue import DMarketRawItemsQueuePublisher

logger = logging.getLogger(__name__)


class ScalableWorker:
    """Scalable worker for processing DMarket items.

    This class implements a worker that can be scaled horizontally
    across multiple instances, with coordination through Redis.
    """

    def __init__(
        self,
        redis_client: Redis,
        rabbitmq_connector: RabbitMQConnector,
        instance_id: Optional[str] = None,
        heartbeat_interval: int = 30,  # 30 seconds
        batch_size: int = 100,
        processing_timeout: int = 300,  # 5 minutes
    ):
        """Initialize the scalable worker.

        Args:
            redis_client: Redis client for coordination
            rabbitmq_connector: RabbitMQ connector for message queue
            instance_id: Unique ID for this worker instance (generated if not provided)
            heartbeat_interval: Time in seconds between heartbeats
            batch_size: Number of items to process in each batch
            processing_timeout: Time in seconds after which a processing task is considered failed
        """
        self.redis = redis_client
        self.rabbitmq_connector = rabbitmq_connector
        self.instance_id = instance_id or str(uuid.uuid4())
        self.heartbeat_interval = heartbeat_interval
        self.batch_size = batch_size
        self.processing_timeout = processing_timeout

        self.heartbeat_task = None
        self.running = False

        # Keys for Redis coordination
        self.instances_key = "dmarket:worker:instances"
        self.processing_key = "dmarket:worker:processing"
        self.stats_key = "dmarket:worker:stats"

    async def register_instance(self) -> None:
        """Register this worker instance in Redis."""
        instance_data = {
            "id": self.instance_id,
            "hostname": os.environ.get("HOSTNAME", "unknown"),
            "pid": os.getpid(),
            "started_at": asyncio.get_event_loop().time(),
            "last_heartbeat": asyncio.get_event_loop().time(),
            "status": "initializing",
        }

        await self.redis.hset(self.instances_key, self.instance_id, json.dumps(instance_data))

        logger.info(f"Registered worker instance {self.instance_id}")

    async def heartbeat(self) -> None:
        """Send periodic heartbeats to indicate this instance is alive."""
        while self.running:
            try:
                await self.redis.hset(
                    self.instances_key,
                    self.instance_id,
                    json.dumps(
                        {
                            "id": self.instance_id,
                            "hostname": os.environ.get("HOSTNAME", "unknown"),
                            "pid": os.getpid(),
                            "last_heartbeat": asyncio.get_event_loop().time(),
                            "status": "running",
                        }
                    ),
                )
                logger.debug(f"Sent heartbeat for worker instance {self.instance_id}")
            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")

            await asyncio.sleep(self.heartbeat_interval)

    async def process_items(self, publisher: DMarketRawItemsQueuePublisher) -> None:
        """Process items from the queue.

        Args:
            publisher: Publisher for sending processed items to RabbitMQ
        """
        # Get a batch of items from the queue
        queue_name = "dmarket_raw_items_queue"
        channel = await self.rabbitmq_connector.connection.channel()

        try:
            # Set QoS to limit the number of unacknowledged messages
            await channel.set_qos(prefetch_count=self.batch_size)

            # Declare the queue to ensure it exists
            queue = await channel.declare_queue(queue_name, durable=True)

            # Process messages in batches
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    if not self.running:
                        break

                    async with message.process():
                        try:
                            # Deserialize the message
                            item = DMarketItem.load_bytes(message.body)

                            # Process the item (in a real implementation, this would do more)
                            # For now, we just publish it back to another queue
                            await publisher.publish_item(item)

                            # Update statistics
                            await self.redis.hincrby(
                                f"{self.stats_key}:{self.instance_id}", "processed_items", 1
                            )

                            logger.debug(f"Processed item {item.item_id}")

                        except Exception as e:
                            logger.error(f"Failed to process message: {e}")

                            # Update error statistics
                            await self.redis.hincrby(
                                f"{self.stats_key}:{self.instance_id}", "error_count", 1
                            )

        finally:
            # Close the channel
            await channel.close()

    async def start(self) -> None:
        """Start the worker."""
        # Register this instance
        await self.register_instance()

        # Start heartbeat task
        self.running = True
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

        # Create publisher
        publisher = DMarketRawItemsQueuePublisher(
            connector=self.rabbitmq_connector, queue_name="dmarket_processed_items_queue"
        )

        try:
            logger.info(f"Started worker instance {self.instance_id}")

            # Process items
            await self.process_items(publisher)

        finally:
            # Clean up
            self.running = False

            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.heartbeat_task

            # Update status
            await self.redis.hset(
                self.instances_key,
                self.instance_id,
                json.dumps(
                    {
                        "id": self.instance_id,
                        "hostname": os.environ.get("HOSTNAME", "unknown"),
                        "pid": os.getpid(),
                        "last_heartbeat": asyncio.get_event_loop().time(),
                        "status": "stopped",
                    }
                ),
            )

            logger.info(f"Stopped worker instance {self.instance_id}")

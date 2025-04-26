"""Distributed parser for Dmarket Telegram Bot.

This module provides a distributed parser that can run multiple instances
simultaneously, coordinating work through Redis to prevent duplicate effort.
"""

import asyncio
import contextlib
import json
import logging
import uuid
from typing import Any, Optional

from redis.asyncio import Redis

from common.dmarket_auth import DMarketAuth
from price_monitoring.parsers.dmarket.items_parser import DMarketItemsParser
from price_monitoring.queues.rabbitmq.raw_items_queue import DMarketRawItemsQueuePublisher
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory

logger = logging.getLogger(__name__)


class DistributedParser:
    """Distributed parser that coordinates work across multiple instances.

    This class implements a distributed parser that can run multiple instances
    simultaneously, coordinating work through Redis to prevent duplicate effort.
    """

    def __init__(
        self,
        redis_client: Redis,
        instance_id: Optional[str] = None,
        lock_expiry: int = 300,  # 5 minutes
        heartbeat_interval: int = 30,  # 30 seconds
    ):
        """Initialize the distributed parser.

        Args:
            redis_client: Redis client for coordination
            instance_id: Unique ID for this parser instance (generated if not provided)
            lock_expiry: Time in seconds after which locks expire
            heartbeat_interval: Time in seconds between heartbeats
        """
        self.redis = redis_client
        self.instance_id = instance_id or str(uuid.uuid4())
        self.lock_expiry = lock_expiry
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_task = None
        self.running = False

        # Keys for Redis coordination
        self.instances_key = "dmarket:parser:instances"
        self.game_locks_key = "dmarket:parser:game_locks"
        self.work_queue_key = "dmarket:parser:work_queue"

    async def register_instance(self) -> None:
        """Register this parser instance in Redis."""
        instance_data = {
            "id": self.instance_id,
            "started_at": asyncio.get_event_loop().time(),
            "last_heartbeat": asyncio.get_event_loop().time(),
            "status": "initializing",
        }
        await self.redis.hset(self.instances_key, self.instance_id, json.dumps(instance_data))
        logger.info(f"Registered parser instance {self.instance_id}")

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
                            "last_heartbeat": asyncio.get_event_loop().time(),
                            "status": "running",
                        }
                    ),
                )
                logger.debug(f"Sent heartbeat for instance {self.instance_id}")
            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")

            await asyncio.sleep(self.heartbeat_interval)

    async def acquire_game_lock(self, game_id: str) -> bool:
        """Attempt to acquire a lock for parsing a specific game.

        Args:
            game_id: ID of the game to lock

        Returns:
            True if lock was acquired, False otherwise
        """
        lock_key = f"{self.game_locks_key}:{game_id}"
        # Use Redis SET NX (Not eXists) with expiry
        acquired = await self.redis.set(lock_key, self.instance_id, nx=True, ex=self.lock_expiry)

        if acquired:
            logger.info(f"Acquired lock for game {game_id}")
        else:
            logger.debug(f"Failed to acquire lock for game {game_id}")

        return bool(acquired)

    async def release_game_lock(self, game_id: str) -> None:
        """Release a lock for a specific game.

        Args:
            game_id: ID of the game to unlock
        """
        lock_key = f"{self.game_locks_key}:{game_id}"
        # Only delete if we own the lock
        current_owner = await self.redis.get(lock_key)
        if current_owner == self.instance_id:
            await self.redis.delete(lock_key)
            logger.info(f"Released lock for game {game_id}")

    async def get_work_item(self) -> Optional[dict[str, Any]]:
        """Get a work item from the queue.

        Returns:
            Work item as a dictionary, or None if no work is available
        """
        # Pop an item from the list (BRPOP with timeout)
        result = await self.redis.brpop(self.work_queue_key, timeout=1)
        if not result:
            return None

        _, item_json = result
        try:
            return json.loads(item_json)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse work item: {item_json}")
            return None

    async def add_work_item(self, game_id: str, params: dict[str, Any]) -> None:
        """Add a work item to the queue.

        Args:
            game_id: ID of the game to parse
            params: Parameters for parsing
        """
        work_item = {
            "game_id": game_id,
            "params": params,
            "added_at": asyncio.get_event_loop().time(),
        }
        await self.redis.lpush(self.work_queue_key, json.dumps(work_item))
        logger.info(f"Added work item for game {game_id}")

    async def process_game(
        self,
        session_factory: AiohttpSessionFactory,
        dmarket_auth: DMarketAuth,
        publisher: DMarketRawItemsQueuePublisher,
        game_id: str,
        params: dict[str, Any],
    ) -> int:
        """Process a single game.

        Args:
            session_factory: Factory for creating HTTP sessions
            dmarket_auth: Authentication for DMarket API
            publisher: Publisher for sending items to RabbitMQ
            game_id: ID of the game to parse
            params: Parameters for parsing

        Returns:
            Number of items published
        """
        # Try to acquire lock for this game
        if not await self.acquire_game_lock(game_id):
            logger.info(f"Game {game_id} is being processed by another instance")
            return 0

        try:
            # Create parser for this game
            parser = DMarketItemsParser(
                session_factory=session_factory,
                dmarket_auth=dmarket_auth,
                game_id=game_id,
                currency=params.get("currency", "USD"),
                items_per_page=params.get("items_per_page", 100),
                api_request_delay_seconds=params.get("api_request_delay", 1.0),
            )

            # Parse items
            items, errors = await parser.parse()

            # Log errors
            if errors:
                logger.warning(f"Encountered {len(errors)} errors during parsing game {game_id}")

            # Publish items
            published_count = 0
            for item in items:
                try:
                    await publisher.publish_item(item)
                    published_count += 1
                except Exception as e:
                    logger.error(f"Failed to publish item {item.item_id}: {e}")

            logger.info(f"Published {published_count}/{len(items)} items for game {game_id}")
            return published_count

        finally:
            # Always release the lock
            await self.release_game_lock(game_id)

    async def start(
        self,
        session_factory: AiohttpSessionFactory,
        dmarket_auth: DMarketAuth,
        publisher: DMarketRawItemsQueuePublisher,
    ) -> None:
        """Start the distributed parser.

        Args:
            session_factory: Factory for creating HTTP sessions
            dmarket_auth: Authentication for DMarket API
            publisher: Publisher for sending items to RabbitMQ
        """
        # Register this instance
        await self.register_instance()

        # Start heartbeat task
        self.running = True
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

        try:
            logger.info(f"Started distributed parser instance {self.instance_id}")

            # Main processing loop
            while self.running:
                # Get work item
                work_item = await self.get_work_item()
                if not work_item:
                    # No work available, wait a bit
                    await asyncio.sleep(1)
                    continue

                # Process work item
                game_id = work_item["game_id"]
                params = work_item["params"]

                logger.info(f"Processing game {game_id}")
                await self.process_game(
                    session_factory=session_factory,
                    dmarket_auth=dmarket_auth,
                    publisher=publisher,
                    game_id=game_id,
                    params=params,
                )

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
                        "last_heartbeat": asyncio.get_event_loop().time(),
                        "status": "stopped",
                    }
                ),
            )

            logger.info(f"Stopped distributed parser instance {self.instance_id}")

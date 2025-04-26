# Scalability Improvements for Dmarket Telegram Bot

This document outlines the implementation of a comprehensive scalability system for the Dmarket Telegram Bot project, addressing one of the key improvement areas identified in the repository analysis.

## Overview

The scalability improvements will enable:
- Running multiple parser instances simultaneously
- Distributing work efficiently across parser instances
- Optimizing proxy utilization for maximum throughput
- Scaling workers horizontally to handle increased load
- Implementing coordination mechanisms to prevent duplicate work

## Current Issues

The current architecture has several limitations that affect scalability:
1. **Single Parser Instance**: The system is designed to run only one parser instance at a time, limiting throughput
2. **Proxy Dependency**: Parsing throughput is directly limited by the number of available proxies
3. **Potential Bottlenecks**: Processing large volumes of data can create bottlenecks
4. **No Work Distribution**: No mechanism exists for distributing work across multiple instances

## Implementation Details

### 1. Distributed Parser Architecture

We'll implement a distributed parser architecture that allows multiple parser instances to run simultaneously:

```python
import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional

from redis.asyncio import Redis
from aiohttp import ClientSession

from common.redis_connector import RedisConnector
from price_monitoring.parsers.dmarket.items_parser import DMarketItemsParser
from price_monitoring.queues.rabbitmq.raw_items_queue import DMarketRawItemsQueuePublisher
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory
from common.dmarket_auth import DMarketAuth

logger = logging.getLogger(__name__)

class DistributedParser:
    """
    Distributed parser that coordinates work across multiple instances.

    This class implements a distributed parser that can run multiple instances
    simultaneously, coordinating work through Redis to prevent duplicate effort.
    """

    def __init__(
        self,
        redis_client: Redis,
        instance_id: str = None,
        lock_expiry: int = 300,  # 5 minutes
        heartbeat_interval: int = 30,  # 30 seconds
    ):
        """
        Initialize the distributed parser.

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
            "status": "initializing"
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
                    json.dumps({
                        "id": self.instance_id,
                        "last_heartbeat": asyncio.get_event_loop().time(),
                        "status": "running"
                    })
                )
                logger.debug(f"Sent heartbeat for instance {self.instance_id}")
            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")

            await asyncio.sleep(self.heartbeat_interval)

    async def acquire_game_lock(self, game_id: str) -> bool:
        """
        Attempt to acquire a lock for parsing a specific game.

        Args:
            game_id: ID of the game to lock

        Returns:
            True if lock was acquired, False otherwise
        """
        lock_key = f"{self.game_locks_key}:{game_id}"
        # Use Redis SET NX (Not eXists) with expiry
        acquired = await self.redis.set(
            lock_key, 
            self.instance_id,
            nx=True,
            ex=self.lock_expiry
        )

        if acquired:
            logger.info(f"Acquired lock for game {game_id}")
        else:
            logger.debug(f"Failed to acquire lock for game {game_id}")

        return bool(acquired)

    async def release_game_lock(self, game_id: str) -> None:
        """
        Release a lock for a specific game.

        Args:
            game_id: ID of the game to unlock
        """
        lock_key = f"{self.game_locks_key}:{game_id}"
        # Only delete if we own the lock
        current_owner = await self.redis.get(lock_key)
        if current_owner == self.instance_id:
            await self.redis.delete(lock_key)
            logger.info(f"Released lock for game {game_id}")

    async def get_work_item(self) -> Optional[Dict[str, Any]]:
        """
        Get a work item from the queue.

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

    async def add_work_item(self, game_id: str, params: Dict[str, Any]) -> None:
        """
        Add a work item to the queue.

        Args:
            game_id: ID of the game to parse
            params: Parameters for parsing
        """
        work_item = {
            "game_id": game_id,
            "params": params,
            "added_at": asyncio.get_event_loop().time()
        }
        await self.redis.lpush(self.work_queue_key, json.dumps(work_item))
        logger.info(f"Added work item for game {game_id}")

    async def process_game(
        self,
        session_factory: AiohttpSessionFactory,
        dmarket_auth: DMarketAuth,
        publisher: DMarketRawItemsQueuePublisher,
        game_id: str,
        params: Dict[str, Any]
    ) -> int:
        """
        Process a single game.

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
        publisher: DMarketRawItemsQueuePublisher
    ) -> None:
        """
        Start the distributed parser.

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
                    params=params
                )

        finally:
            # Clean up
            self.running = False
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            # Update status
            await self.redis.hset(
                self.instances_key,
                self.instance_id,
                json.dumps({
                    "id": self.instance_id,
                    "last_heartbeat": asyncio.get_event_loop().time(),
                    "status": "stopped"
                })
            )

            logger.info(f"Stopped distributed parser instance {self.instance_id}")
```

### 2. Proxy Management System

We'll implement an enhanced proxy management system that efficiently distributes proxies across parser instances:

```python
import asyncio
import logging
import random
import time
from typing import List, Dict, Any, Optional, Set

from redis.asyncio import Redis

from proxy_http.proxy import Proxy
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Enhanced proxy management system.

    This class provides efficient distribution and management of proxies
    across multiple parser instances, with health monitoring and rotation.
    """

    def __init__(
        self,
        redis_client: Redis,
        instance_id: str,
        proxies_key: str = "dmarket_proxies",
        proxy_stats_key: str = "dmarket:proxy:stats",
        proxy_locks_key: str = "dmarket:proxy:locks",
        max_proxies_per_instance: int = 0,  # 0 means no limit
        lock_expiry: int = 60,  # 1 minute
        health_check_interval: int = 300,  # 5 minutes
    ):
        """
        Initialize the proxy manager.

        Args:
            redis_client: Redis client for coordination
            instance_id: Unique ID for this parser instance
            proxies_key: Redis key for storing proxies
            proxy_stats_key: Redis key for storing proxy statistics
            proxy_locks_key: Redis key for storing proxy locks
            max_proxies_per_instance: Maximum number of proxies per instance (0 = no limit)
            lock_expiry: Time in seconds after which locks expire
            health_check_interval: Time in seconds between health checks
        """
        self.redis = redis_client
        self.instance_id = instance_id
        self.proxies_key = proxies_key
        self.proxy_stats_key = proxy_stats_key
        self.proxy_locks_key = proxy_locks_key
        self.max_proxies_per_instance = max_proxies_per_instance
        self.lock_expiry = lock_expiry
        self.health_check_interval = health_check_interval

        self.allocated_proxies: Set[str] = set()
        self.session_factory = AiohttpSessionFactory()
        self.health_check_task = None
        self.running = False

    async def start(self) -> None:
        """Start the proxy manager."""
        self.running = True
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Started proxy manager for instance {self.instance_id}")

    async def stop(self) -> None:
        """Stop the proxy manager and release all proxies."""
        self.running = False

        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        # Release all allocated proxies
        for proxy_id in list(self.allocated_proxies):
            await self.release_proxy(proxy_id)

        # Close all sessions
        await self.session_factory.close_all_sessions()

        logger.info(f"Stopped proxy manager for instance {self.instance_id}")

    async def get_all_proxies(self) -> List[Proxy]:
        """
        Get all available proxies.

        Returns:
            List of all proxies
        """
        from price_monitoring.storage.proxy import RedisProxyStorage

        storage = RedisProxyStorage(self.redis, self.proxies_key)
        return await storage.get_all()

    async def allocate_proxies(self, count: int = None) -> List[Proxy]:
        """
        Allocate proxies for this instance.

        Args:
            count: Number of proxies to allocate (None = all available)

        Returns:
            List of allocated proxies
        """
        # Get all available proxies
        all_proxies = await self.get_all_proxies()
        if not all_proxies:
            logger.warning("No proxies available")
            return []

        # Determine how many proxies to allocate
        if count is None:
            if self.max_proxies_per_instance > 0:
                count = min(len(all_proxies), self.max_proxies_per_instance)
            else:
                count = len(all_proxies)

        # Shuffle proxies to randomize allocation
        random.shuffle(all_proxies)

        # Try to allocate proxies
        allocated_proxies = []
        for proxy in all_proxies:
            if len(allocated_proxies) >= count:
                break

            proxy_id = proxy.get_identifier()
            if await self._acquire_proxy_lock(proxy_id):
                self.allocated_proxies.add(proxy_id)
                allocated_proxies.append(proxy)

        logger.info(f"Allocated {len(allocated_proxies)} proxies for instance {self.instance_id}")
        return allocated_proxies

    async def release_proxy(self, proxy_id: str) -> None:
        """
        Release a proxy.

        Args:
            proxy_id: ID of the proxy to release
        """
        if proxy_id in self.allocated_proxies:
            await self._release_proxy_lock(proxy_id)
            self.allocated_proxies.remove(proxy_id)
            logger.debug(f"Released proxy {proxy_id}")

    async def _acquire_proxy_lock(self, proxy_id: str) -> bool:
        """
        Acquire a lock for a proxy.

        Args:
            proxy_id: ID of the proxy to lock

        Returns:
            True if lock was acquired, False otherwise
        """
        lock_key = f"{self.proxy_locks_key}:{proxy_id}"
        acquired = await self.redis.set(
            lock_key,
            self.instance_id,
            nx=True,
            ex=self.lock_expiry
        )

        return bool(acquired)

    async def _release_proxy_lock(self, proxy_id: str) -> None:
        """
        Release a lock for a proxy.

        Args:
            proxy_id: ID of the proxy to unlock
        """
        lock_key = f"{self.proxy_locks_key}:{proxy_id}"
        current_owner = await self.redis.get(lock_key)
        if current_owner == self.instance_id:
            await self.redis.delete(lock_key)

    async def _health_check_loop(self) -> None:
        """Periodically check the health of allocated proxies."""
        while self.running:
            try:
                await self._check_proxy_health()
            except Exception as e:
                logger.error(f"Error during proxy health check: {e}")

            await asyncio.sleep(self.health_check_interval)

    async def _check_proxy_health(self) -> None:
        """Check the health of all allocated proxies."""
        if not self.allocated_proxies:
            return

        logger.debug(f"Checking health of {len(self.allocated_proxies)} proxies")

        # Get all proxies
        all_proxies = await self.get_all_proxies()
        proxy_map = {proxy.get_identifier(): proxy for proxy in all_proxies}

        # Check each allocated proxy
        for proxy_id in list(self.allocated_proxies):
            if proxy_id not in proxy_map:
                # Proxy no longer exists
                self.allocated_proxies.remove(proxy_id)
                continue

            proxy = proxy_map[proxy_id]

            try:
                # Create a session with this proxy
                session = self.session_factory.create_session_with_proxy(proxy)

                # Test the proxy with a simple request
                start_time = time.time()
                async with session.get("https://api.dmarket.com/exchange/v1/ping", timeout=10) as response:
                    response_time = time.time() - start_time

                    # Update proxy statistics
                    stats = {
                        "last_check": time.time(),
                        "response_time": response_time,
                        "status_code": response.status,
                        "is_healthy": response.status == 200
                    }

                    await self.redis.hset(
                        f"{self.proxy_stats_key}:{proxy_id}",
                        mapping=stats
                    )

                    if response.status != 200:
                        logger.warning(f"Proxy {proxy_id} returned status {response.status}")

            except Exception as e:
                logger.warning(f"Proxy {proxy_id} health check failed: {e}")

                # Update proxy statistics
                stats = {
                    "last_check": time.time(),
                    "error": str(e),
                    "is_healthy": False
                }

                await self.redis.hset(
                    f"{self.proxy_stats_key}:{proxy_id}",
                    mapping=stats
                )
```

### 3. Work Distribution System

We'll implement a work distribution system that efficiently distributes parsing tasks across multiple instances:

```python
import asyncio
import json
import logging
import time
from typing import List, Dict, Any, Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

class WorkDistributor:
    """
    Work distributor for parsing tasks.

    This class manages the distribution of parsing tasks across multiple
    parser instances, ensuring fair distribution and preventing duplicate work.
    """

    def __init__(
        self,
        redis_client: Redis,
        work_queue_key: str = "dmarket:parser:work_queue",
        game_schedule_key: str = "dmarket:parser:game_schedule",
        default_interval: int = 3600,  # 1 hour
    ):
        """
        Initialize the work distributor.

        Args:
            redis_client: Redis client for coordination
            work_queue_key: Redis key for the work queue
            game_schedule_key: Redis key for game schedules
            default_interval: Default interval in seconds between parsing the same game
        """
        self.redis = redis_client
        self.work_queue_key = work_queue_key
        self.game_schedule_key = game_schedule_key
        self.default_interval = default_interval

    async def schedule_game(
        self,
        game_id: str,
        params: Dict[str, Any],
        interval: int = None,
        priority: int = 0
    ) -> None:
        """
        Schedule a game for parsing.

        Args:
            game_id: ID of the game to parse
            params: Parameters for parsing
            interval: Interval in seconds between parsing (None = use default)
            priority: Priority (0-9, higher = more important)
        """
        interval = interval or self.default_interval

        # Store schedule information
        schedule_data = {
            "game_id": game_id,
            "params": params,
            "interval": interval,
            "priority": priority,
            "last_scheduled": time.time(),
            "next_scheduled": time.time() + interval
        }

        await self.redis.hset(
            self.game_schedule_key,
            game_id,
            json.dumps(schedule_data)
        )

        # Add to work queue
        await self.add_to_queue(game_id, params, priority)

        logger.info(f"Scheduled game {game_id} with interval {interval}s and priority {priority}")

    async def add_to_queue(
        self,
        game_id: str,
        params: Dict[str, Any],
        priority: int = 0
    ) -> None:
        """
        Add a game to the work queue.

        Args:
            game_id: ID of the game to parse
            params: Parameters for parsing
            priority: Priority (0-9, higher = more important)
        """
        work_item = {
            "game_id": game_id,
            "params": params,
            "priority": priority,
            "added_at": time.time()
        }

        # Use priority queue (sorted set) with score = -priority
        # This ensures higher priority items come first
        await self.redis.zadd(
            self.work_queue_key,
            {json.dumps(work_item): -priority}
        )

        logger.debug(f"Added game {game_id} to work queue with priority {priority}")

    async def get_next_work_item(self) -> Optional[Dict[str, Any]]:
        """
        Get the next work item from the queue.

        Returns:
            Work item as a dictionary, or None if no work is available
        """
        # Get highest priority item (lowest score)
        result = await self.redis.zpopmin(self.work_queue_key)
        if not result:
            return None

        item_json, _ = result[0]
        try:
            return json.loads(item_json)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse work item: {item_json}")
            return None

    async def update_schedules(self) -> int:
        """
        Update schedules and add due games to the work queue.

        Returns:
            Number of games added to the queue
        """
        # Get all schedules
        schedules = await self.redis.hgetall(self.game_schedule_key)
        if not schedules:
            return 0

        current_time = time.time()
        added_count = 0

        for game_id, schedule_json in schedules.items():
            try:
                schedule = json.loads(schedule_json)

                # Check if it's time to schedule this game
                if schedule["next_scheduled"] <= current_time:
                    # Add to work queue
                    await self.add_to_queue(
                        game_id=schedule["game_id"],
                        params=schedule["params"],
                        priority=schedule["priority"]
                    )

                    # Update schedule
                    schedule["last_scheduled"] = current_time
                    schedule["next_scheduled"] = current_time + schedule["interval"]

                    await self.redis.hset(
                        self.game_schedule_key,
                        game_id,
                        json.dumps(schedule)
                    )

                    added_count += 1
                    logger.debug(f"Scheduled game {game_id} for parsing")

            except Exception as e:
                logger.error(f"Error updating schedule for game {game_id}: {e}")

        logger.info(f"Added {added_count} games to the work queue")
        return added_count

    async def run_scheduler(self, check_interval: int = 60) -> None:
        """
        Run the scheduler loop.

        Args:
            check_interval: Interval in seconds between schedule checks
        """
        logger.info("Starting scheduler loop")

        try:
            while True:
                await self.update_schedules()
                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
```

### 4. Horizontal Scaling for Workers

We'll implement a horizontal scaling solution for workers:

```python
import asyncio
import json
import logging
import os
import signal
import uuid
from typing import Dict, Any, List, Optional

from redis.asyncio import Redis

from common.redis_connector import RedisConnector
from common.rabbitmq_connector import RabbitMQConnector
from price_monitoring.queues.rabbitmq.raw_items_queue import DMarketRawItemsQueuePublisher
from price_monitoring.models.dmarket import DMarketItem

logger = logging.getLogger(__name__)

class ScalableWorker:
    """
    Scalable worker for processing DMarket items.

    This class implements a worker that can be scaled horizontally
    across multiple instances, with coordination through Redis.
    """

    def __init__(
        self,
        redis_client: Redis,
        rabbitmq_connector: RabbitMQConnector,
        instance_id: str = None,
        heartbeat_interval: int = 30,  # 30 seconds
        batch_size: int = 100,
        processing_timeout: int = 300,  # 5 minutes
    ):
        """
        Initialize the scalable worker.

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
            "status": "initializing"
        }

        await self.redis.hset(
            self.instances_key,
            self.instance_id,
            json.dumps(instance_data)
        )

        logger.info(f"Registered worker instance {self.instance_id}")

    async def heartbeat(self) -> None:
        """Send periodic heartbeats to indicate this instance is alive."""
        while self.running:
            try:
                await self.redis.hset(
                    self.instances_key,
                    self.instance_id,
                    json.dumps({
                        "id": self.instance_id,
                        "hostname": os.environ.get("HOSTNAME", "unknown"),
                        "pid": os.getpid(),
                        "last_heartbeat": asyncio.get_event_loop().time(),
                        "status": "running"
                    })
                )
                logger.debug(f"Sent heartbeat for worker instance {self.instance_id}")
            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")

            await asyncio.sleep(self.heartbeat_interval)

    async def process_items(self, publisher: DMarketRawItemsQueuePublisher) -> None:
        """
        Process items from the queue.

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
                batch = []
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
                                f"{self.stats_key}:{self.instance_id}",
                                "processed_items",
                                1
                            )

                            logger.debug(f"Processed item {item.item_id}")

                        except Exception as e:
                            logger.error(f"Failed to process message: {e}")

                            # Update error statistics
                            await self.redis.hincrby(
                                f"{self.stats_key}:{self.instance_id}",
                                "error_count",
                                1
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
            connector=self.rabbitmq_connector,
            queue_name="dmarket_processed_items_queue"
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
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            # Update status
            await self.redis.hset(
                self.instances_key,
                self.instance_id,
                json.dumps({
                    "id": self.instance_id,
                    "hostname": os.environ.get("HOSTNAME", "unknown"),
                    "pid": os.getpid(),
                    "last_heartbeat": asyncio.get_event_loop().time(),
                    "status": "stopped"
                })
            )

            logger.info(f"Stopped worker instance {self.instance_id}")
```

## Usage Examples

### Distributed Parser

```python
import asyncio
import logging
from uuid import uuid4

from common.redis_connector import RedisConnector
from common.rabbitmq_connector import RabbitMQConnector
from common.dmarket_auth import DMarketAuth
from price_monitoring.queues.rabbitmq.raw_items_queue import DMarketRawItemsQueuePublisher
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory
from scalability.distributed_parser import DistributedParser
from scalability.proxy_manager import ProxyManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Initialize Redis connector
    redis_connector = RedisConnector(
        host="localhost",
        port="6379",
        db="0"
    )
    redis_client = await redis_connector.get_client()

    # Initialize RabbitMQ connector
    rabbitmq_connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    await rabbitmq_connector.connect()

    # Create a unique instance ID
    instance_id = str(uuid4())

    # Initialize proxy manager
    proxy_manager = ProxyManager(
        redis_client=redis_client,
        instance_id=instance_id
    )
    await proxy_manager.start()

    # Allocate proxies for this instance
    proxies = await proxy_manager.allocate_proxies()

    # Create session factory with proxies
    session_factory = AiohttpSessionFactory()

    # Initialize DMarket auth
    dmarket_auth = DMarketAuth(
        public_key="your_public_key",
        secret_key="your_secret_key"
    )

    # Create publisher
    publisher = DMarketRawItemsQueuePublisher(
        connector=rabbitmq_connector,
        queue_name="dmarket_raw_items_queue"
    )

    # Initialize distributed parser
    parser = DistributedParser(
        redis_client=redis_client,
        instance_id=instance_id
    )

    # Start the parser
    try:
        await parser.start(
            session_factory=session_factory,
            dmarket_auth=dmarket_auth,
            publisher=publisher
        )
    finally:
        # Clean up
        await proxy_manager.stop()
        await rabbitmq_connector.close()
        await redis_connector.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Work Distributor

```python
import asyncio
import logging

from common.redis_connector import RedisConnector
from scalability.work_distributor import WorkDistributor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Initialize Redis connector
    redis_connector = RedisConnector(
        host="localhost",
        port="6379",
        db="0"
    )
    redis_client = await redis_connector.get_client()

    # Initialize work distributor
    distributor = WorkDistributor(
        redis_client=redis_client,
        default_interval=3600  # 1 hour
    )

    # Schedule some games
    game_ids = ["a8db", "9a92", "730"]  # Example game IDs

    for i, game_id in enumerate(game_ids):
        await distributor.schedule_game(
            game_id=game_id,
            params={
                "currency": "USD",
                "items_per_page": 100,
                "api_request_delay": 1.0
            },
            interval=3600 + i * 300,  # Stagger schedules
            priority=i  # Different priorities
        )

    # Run the scheduler
    try:
        await distributor.run_scheduler(check_interval=60)
    finally:
        await redis_connector.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Scalable Worker

```python
import asyncio
import logging
from uuid import uuid4

from common.redis_connector import RedisConnector
from common.rabbitmq_connector import RabbitMQConnector
from scalability.scalable_worker import ScalableWorker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Initialize Redis connector
    redis_connector = RedisConnector(
        host="localhost",
        port="6379",
        db="0"
    )
    redis_client = await redis_connector.get_client()

    # Initialize RabbitMQ connector
    rabbitmq_connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    await rabbitmq_connector.connect()

    # Create a unique instance ID
    instance_id = str(uuid4())

    # Initialize worker
    worker = ScalableWorker(
        redis_client=redis_client,
        rabbitmq_connector=rabbitmq_connector,
        instance_id=instance_id,
        batch_size=100
    )

    # Start the worker
    try:
        await worker.start()
    finally:
        await rabbitmq_connector.close()
        await redis_connector.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Docker Compose Configuration

To deploy the scalable system, we can use Docker Compose to run multiple instances of each component:

```yaml
version: '3.8'

services:
  redis:
    image: redis:6
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      - RABBITMQ_DEFAULT_USER=guest
      - RABBITMQ_DEFAULT_PASS=guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  scheduler:
    build:
      context: ..
      dockerfile: ../Dockerfile
    depends_on:
      - redis
      - rabbitmq
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - RABBITMQ_HOST=rabbitmq
      - RABBITMQ_PORT=5672
      - RABBITMQ_USER=guest
      - RABBITMQ_PASSWORD=guest
    command: python -m scalability.scheduler

  parser:
    build:
      context: ..
      dockerfile: ../Dockerfile
    depends_on:
      - redis
      - rabbitmq
      - scheduler
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - RABBITMQ_HOST=rabbitmq
      - RABBITMQ_PORT=5672
      - RABBITMQ_USER=guest
      - RABBITMQ_PASSWORD=guest
      - DMARKET_PUBLIC_KEY=${DMARKET_PUBLIC_KEY}
      - DMARKET_SECRET_KEY=${DMARKET_SECRET_KEY}
    command: python -m scalability.parser
    deploy:
      replicas: 3

  worker:
    build:
      context: ..
      dockerfile: ../Dockerfile
    depends_on:
      - redis
      - rabbitmq
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - RABBITMQ_HOST=rabbitmq
      - RABBITMQ_PORT=5672
      - RABBITMQ_USER=guest
      - RABBITMQ_PASSWORD=guest
    command: python -m scalability.worker
    deploy:
      replicas: 5

volumes:
  redis_data:
  rabbitmq_data:
```

## Migration Guide

### Step 1: Create the Scalability Package

Create a new package structure for the scalability components:

```
Dmarket_Telegram_bot/
├── scalability/
│   ├── __init__.py
│   ├── distributed_parser.py
│   ├── proxy_manager.py
│   ├── work_distributor.py
│   ├── scalable_worker.py
│   ├── scheduler.py
│   ├── parser.py
│   └── worker.py
```

### Step 2: Implement the Core Components

Implement the core components as described in this document:

1. `distributed_parser.py`: Distributed parser architecture
2. `proxy_manager.py`: Enhanced proxy management system
3. `work_distributor.py`: Work distribution system
4. `scalable_worker.py`: Horizontally scalable worker

### Step 3: Create Entry Points

Create entry point scripts for each component:

1. `scheduler.py`: Runs the work distributor scheduler
2. `parser.py`: Runs a distributed parser instance
3. `worker.py`: Runs a scalable worker instance

### Step 4: Update Docker Configuration

Update the Docker configuration to support multiple instances:

1. Create a new Docker Compose file for the scalable system
2. Configure environment variables for coordination
3. Set up replica counts for horizontal scaling

### Step 5: Gradual Migration

Migrate from the current system to the scalable system gradually:

1. Start by running a single instance of each component alongside the existing system
2. Validate that the new system works correctly
3. Gradually increase the number of instances
4. Monitor performance and adjust as needed
5. Once stable, switch over completely to the new system

## Benefits

Implementing this scalability system will:

1. **Increased Throughput**: Multiple parser instances can run simultaneously, significantly increasing throughput
2. **Efficient Resource Utilization**: Proxies are distributed efficiently across instances
3. **Improved Reliability**: Coordination mechanisms prevent duplicate work and ensure all tasks are completed
4. **Horizontal Scaling**: The system can scale horizontally by adding more instances
5. **Better Monitoring**: Comprehensive monitoring of all components provides visibility into system health

## Conclusion

The proposed scalability improvements provide a comprehensive solution for addressing the scalability limitations identified in the repository analysis. By implementing a distributed parser architecture, enhanced proxy management, work distribution system, and horizontally scalable workers, we can significantly improve the throughput and reliability of the Dmarket Telegram Bot.

"""Enhanced proxy management system for Dmarket Telegram Bot.

This module provides efficient distribution and management of proxies
across multiple parser instances, with health monitoring and rotation.
"""

import asyncio
import contextlib
import logging
import random
import time
from typing import Optional

from redis.asyncio import Redis

from proxy_http.aiohttp_session_factory import AiohttpSessionFactory
from proxy_http.proxy import Proxy

logger = logging.getLogger(__name__)


class ProxyManager:
    """Enhanced proxy management system.

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
        """Initialize the proxy manager.

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

        self.allocated_proxies: set[str] = set()
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
            with contextlib.suppress(asyncio.CancelledError):
                await self.health_check_task

        # Release all allocated proxies
        for proxy_id in list(self.allocated_proxies):
            await self.release_proxy(proxy_id)

        # Close all sessions
        await self.session_factory.close_all_sessions()

        logger.info(f"Stopped proxy manager for instance {self.instance_id}")

    async def get_all_proxies(self) -> list[Proxy]:
        """Get all available proxies.

        Returns:
            List of all proxies
        """
        from price_monitoring.storage.proxy import RedisProxyStorage

        storage = RedisProxyStorage(self.redis, self.proxies_key)
        return await storage.get_all()

    async def allocate_proxies(self, count: Optional[int] = None) -> list[Proxy]:
        """Allocate proxies for this instance.

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
        """Release a proxy.

        Args:
            proxy_id: ID of the proxy to release
        """
        if proxy_id in self.allocated_proxies:
            await self._release_proxy_lock(proxy_id)
            self.allocated_proxies.remove(proxy_id)
            logger.debug(f"Released proxy {proxy_id}")

    async def _acquire_proxy_lock(self, proxy_id: str) -> bool:
        """Acquire a lock for a proxy.

        Args:
            proxy_id: ID of the proxy to lock

        Returns:
            True if lock was acquired, False otherwise
        """
        lock_key = f"{self.proxy_locks_key}:{proxy_id}"
        acquired = await self.redis.set(lock_key, self.instance_id, nx=True, ex=self.lock_expiry)

        return bool(acquired)

    async def _release_proxy_lock(self, proxy_id: str) -> None:
        """Release a lock for a proxy.

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
                async with session.get(
                    "https://api.dmarket.com/exchange/v1/ping", timeout=10
                ) as response:
                    response_time = time.time() - start_time

                    # Update proxy statistics
                    stats = {
                        "last_check": time.time(),
                        "response_time": response_time,
                        "status_code": response.status,
                        "is_healthy": response.status == 200,
                    }

                    await self.redis.hset(f"{self.proxy_stats_key}:{proxy_id}", mapping=stats)

                    if response.status != 200:
                        logger.warning(f"Proxy {proxy_id} returned status {response.status}")

            except Exception as e:
                logger.warning(f"Proxy {proxy_id} health check failed: {e}")

                # Update proxy statistics
                stats = {"last_check": time.time(), "error": str(e), "is_healthy": False}

                await self.redis.hset(f"{self.proxy_stats_key}:{proxy_id}", mapping=stats)

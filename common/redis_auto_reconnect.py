"""Redis Auto-Reconnect Module

This module provides a wrapper for Redis connections with automatic reconnection functionality.
It helps improve the robustness of Redis operations by handling connection failures gracefully.
"""

import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar, cast

import aioredis
from aioredis import Redis
from aioredis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar("T")

# Maximum number of reconnection attempts
MAX_RECONNECT_ATTEMPTS = 5

# Delay between reconnection attempts (in seconds)
RECONNECT_DELAY = 1.0


class RedisAutoReconnect:
    """Wrapper for Redis connections with automatic reconnection functionality.

    This class wraps a Redis connection and provides automatic reconnection
    if the connection is lost or an operation fails due to connection issues.
    """

    def __init__(
        self,
        redis_url: str,
        db: int = 0,
        max_reconnect_attempts: int = MAX_RECONNECT_ATTEMPTS,
        reconnect_delay: float = RECONNECT_DELAY,
    ):
        """Initialize the Redis auto-reconnect wrapper.

        Args:
            redis_url: Redis connection URL
            db: Redis database number
            max_reconnect_attempts: Maximum number of reconnection attempts
            reconnect_delay: Delay between reconnection attempts (in seconds)
        """
        self.redis_url = redis_url
        self.db = db
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self._redis: Optional[Redis] = None
        self._connection_lock = asyncio.Lock()

    async def get_connection(self) -> Redis:
        """Get the Redis connection, creating it if it doesn't exist.

        Returns:
            Redis connection object
        """
        if self._redis is None:
            async with self._connection_lock:
                if self._redis is None:
                    self._redis = await self._create_connection()

        return cast(Redis, self._redis)

    async def _create_connection(self) -> Redis:
        """Create a new Redis connection.

        Returns:
            Redis connection object
        """
        try:
            logger.debug(f"Creating Redis connection to {self.redis_url}, db={self.db}")
            redis = await aioredis.create_redis_pool(self.redis_url, db=self.db, encoding="utf-8")
            logger.info(f"Redis connection established: {self.redis_url}, db={self.db}")
            return redis
        except Exception as e:
            logger.error(f"Failed to create Redis connection: {e!s}")
            raise

    async def reconnect(self) -> Redis:
        """Attempt to reconnect to Redis.

        Returns:
            New Redis connection object
        """
        if self._redis is not None:
            self._redis.close()
            await self._redis.wait_closed()
            self._redis = None

        return await self.get_connection()

    async def execute_with_retry(self, operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a Redis operation with automatic retry on connection failure.

        Args:
            operation: Redis operation to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the Redis operation

        Raises:
            RedisError: If all reconnection attempts fail
        """
        attempts = 0
        last_error = None

        while attempts < self.max_reconnect_attempts:
            try:
                redis = await self.get_connection()
                method = getattr(redis, operation.__name__)
                return await method(*args, **kwargs)
            except (ConnectionError, RedisError) as e:
                attempts += 1
                last_error = e

                if attempts >= self.max_reconnect_attempts:
                    logger.error(
                        f"Failed to execute Redis operation {operation.__name__} "
                        f"after {attempts} attempts: {e!s}"
                    )
                    break

                logger.warning(
                    f"Redis operation {operation.__name__} failed: {e!s}. "
                    f"Reconnecting (attempt {attempts}/{self.max_reconnect_attempts})..."
                )

                # Exponential backoff
                wait_time = self.reconnect_delay * (2 ** (attempts - 1))
                await asyncio.sleep(wait_time)

                try:
                    await self.reconnect()
                except Exception as reconnect_error:
                    logger.error(f"Reconnection failed: {reconnect_error!s}")

        if last_error:
            raise last_error

        # This should never happen, but it's here for type checking
        raise RedisError("Failed to execute Redis operation for unknown reason")

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis is not None:
            self._redis.close()
            await self._redis.wait_closed()
            self._redis = None
            logger.info("Redis connection closed")

    async def __aenter__(self) -> "RedisAutoReconnect":
        """Enter the async context manager."""
        await self.get_connection()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager."""
        await self.close()

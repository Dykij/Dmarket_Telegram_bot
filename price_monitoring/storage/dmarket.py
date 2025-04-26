import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import redis.asyncio as redis  # Using redis.asyncio
# Import exceptions from the main redis package
from redis.exceptions import RedisError

from price_monitoring.models.dmarket import DMarketItem

logger = logging.getLogger(__name__)


# Abstract classes for working with DMarket item storage
class AbstractDmarketItemStorage(ABC):
    """Abstract class for DMarket item storage."""

    @property
    def is_trade_ban(self) -> bool:
        """Check if there is a trade ban."""
        return False

    @abstractmethod
    async def get_all(self) -> dict[str, float]:
        """Get all items from storage."""


class AbstractDmarketOrdersStorage(ABC):
    """Abstract class for DMarket orders storage."""

    @abstractmethod
    async def get_all(self) -> dict[str, tuple[float, int]]:
        """Get all orders from storage."""


class AbstractDmarketSellHistoryStorage(ABC):
    """Abstract class for DMarket sell history storage."""

    @abstractmethod
    async def get_all(self) -> dict[str, Any]:
        """Get all sell history from storage."""


class DMarketStorage:
    """Storage for DMarket items using Redis."""

    def __init__(
        self, redis_client: redis.Redis, prefix: str = "dmarket:items", ttl_seconds: int = 3600
    ):
        """Initialize the storage.

        Args:
            redis_client: Asynchronous Redis client.
            prefix: Prefix for Redis keys.
            ttl_seconds: Time-to-live for keys in seconds.
        """
        self._redis = redis_client
        self._prefix = prefix
        self._ttl = ttl_seconds

    def _get_key(self, item_id: str) -> str:
        """Generate Redis key for a given item ID."""
        return f"{self._prefix}:{item_id}"

    async def save_item(self, item: DMarketItem) -> None:
        """Save an item to Redis with TTL.

        Args:
            item: DMarketItem to save.

        Raises:
            RedisError: If an error occurs when working with Redis.
            ValueError: If a JSON serialization error occurs.
        """
        key = self._get_key(item.item_id)
        try:
            item_json = json.dumps(item.to_dict())
            await self._redis.set(key, item_json, ex=self._ttl)
            logger.debug(f"Saved item {item.item_id} to Redis with TTL {self._ttl}s.")
        # Use imported exceptions
        except (RedisError, TypeError, json.JSONDecodeError) as error:
            logger.error(
                f"Failed to save item {item.item_id} to Redis. Error: {error}", exc_info=True
            )
            # Re-raise Redis error so the calling code can handle it
            if isinstance(error, RedisError):
                raise error
            # Otherwise raise ValueError for serialization errors
            raise ValueError(f"Failed to serialize item {item.item_id}") from error

    async def get_item(self, item_id: str) -> Optional[DMarketItem]:
        """Get an item from Redis by ID.

        Args:
            item_id: Item ID.

        Returns:
            DMarketItem object if found and successfully deserialized, otherwise None.
        """
        key = self._get_key(item_id)
        try:
            item_json_bytes = await self._redis.get(key)
            if item_json_bytes is None:
                logger.debug(f"Item {item_id} not found in Redis.")
                return None

            item_data = json.loads(item_json_bytes.decode("utf-8"))
            item = DMarketItem.from_dict(item_data)
            logger.debug(f"Retrieved item {item_id} from Redis.")
            return item
        # Use imported exceptions and catch KeyError/TypeError for from_dict
        except (RedisError, json.JSONDecodeError, TypeError, KeyError) as e:
            logger.error(
                f"Failed to get or parse item {item_id} from Redis. Error: {e}", exc_info=True
            )
            return None  # Return None for any error in retrieval or parsing

    async def delete_item(self, item_id: str) -> bool:
        """Delete an item from Redis by ID.

        Args:
            item_id: ID of the item to delete.

        Returns:
            True if the item was deleted, False otherwise.

        Raises:
            RedisError: If an error occurs when working with Redis.
        """
        key = self._get_key(item_id)
        try:
            deleted_count = await self._redis.delete(key)
            was_deleted = deleted_count > 0
            if was_deleted:
                logger.debug(f"Deleted item {item_id} from Redis.")
            else:
                logger.debug(f"Item {item_id} not found in Redis for deletion.")
            return was_deleted
        except RedisError as e:
            logger.error(f"Failed to delete item {item_id} from Redis. Error: {e}", exc_info=True)
            raise e  # Re-raise Redis error

    async def get_and_update_price_if_lower(
        self, game_id: str, title: str, price: float
    ) -> tuple[Optional[float], bool]:
        """Get the previous price of an item and update it if the new price is lower.

        Args:
            game_id: Game ID of the item
            title: Item title
            price: New item price

        Returns:
            Tuple (previous_price, updated), where:
            - previous_price: previous item price or None if item not found
            - updated: True if the price was updated, False otherwise
        """
        item_id = f"{game_id}:{title}"
        key = self._get_key(item_id)
        try:
            # Try to get the current price
            current_price_data = await self._redis.get(key)
            current_price = None

            if current_price_data is not None:
                try:
                    current_price = float(current_price_data.decode("utf-8"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid price format for item {item_id}: {e}")

            # Update price only if it doesn't exist or the new price is lower than current
            update_needed = current_price is None or price < current_price

            if update_needed:
                await self._redis.set(key, str(price), ex=self._ttl)
                logger.debug(f"Updated price for item {item_id} from {current_price} to {price}")

            return current_price, update_needed

        except RedisError as e:
            logger.error(f"Failed to get or update price for item {item_id}: {e}", exc_info=True)
            return None, False

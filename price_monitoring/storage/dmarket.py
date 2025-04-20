import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

import redis.asyncio as redis  # Используем redis.asyncio
# Импортируем исключения из основного пакета redis
from redis.exceptions import RedisError

from ..models.dmarket import DMarketItem

logger = logging.getLogger(__name__)


# Абстрактные классы для работы с хранилищем предметов DMarket
class AbstractDmarketItemStorage(ABC):
    """Абстрактный класс для хранилища предметов DMarket."""

    @property
    def is_trade_ban(self) -> bool:
        """Проверяет, есть ли торговый бан."""
        return False

    @abstractmethod
    async def get_all(self) -> Dict[str, float]:
        """Получает все предметы из хранилища."""


class AbstractDmarketOrdersStorage(ABC):
    """Абстрактный класс для хранилища ордеров DMarket."""

    @abstractmethod
    async def get_all(self) -> Dict[str, Tuple[float, int]]:
        """Получает все ордера из хранилища."""


class AbstractDmarketSellHistoryStorage(ABC):
    """Абстрактный класс для хранилища истории продаж DMarket."""

    @abstractmethod
    async def get_all(self) -> Dict[str, Any]:
        """Получает всю историю продаж из хранилища."""


class DMarketStorage:
    """Хранилище для предметов DMarket с использованием Redis."""

    def __init__(
        self, redis_client: redis.Redis, prefix: str = "dmarket:items", ttl_seconds: int = 3600
    ):
        """
        Инициализация хранилища.

        Args:
            redis_client: Асинхронный клиент Redis.
            prefix: Префикс для ключей в Redis.
            ttl_seconds: Время жизни ключей в секундах.
        """
        self._redis = redis_client
        self._prefix = prefix
        self._ttl = ttl_seconds

    def _get_key(self, item_id: str) -> str:
        """Формирует ключ Redis для заданного ID предмета."""
        return f"{self._prefix}:{item_id}"

    async def save_item(self, item: DMarketItem) -> None:
        """
        Сохраняет предмет в Redis с установкой TTL.

        Args:
            item: Предмет DMarketItem для сохранения.

        Raises:
            RedisError: Если произошла ошибка при работе с Redis.
            ValueError: Если произошла ошибка сериализации JSON.
        """
        key = self._get_key(item.item_id)
        try:
            item_json = json.dumps(item.to_dict())
            await self._redis.set(key, item_json, ex=self._ttl)
            logger.debug(f"Saved item {item.item_id} to Redis with TTL {self._ttl}s.")
        # Используем импортированные исключения
        except (RedisError, TypeError, json.JSONDecodeError) as error:
            logger.error(
                f"Failed to save item {item.item_id} to Redis. Error: {error}", exc_info=True
            )
            # Перевыбрасываем ошибку Redis, чтобы вызывающий код мог ее обработать
            if isinstance(error, RedisError):
                raise error
            # Иначе выбрасываем ValueError для ошибок сериализации
            raise ValueError(f"Failed to serialize item {item.item_id}") from error

    async def get_item(self, item_id: str) -> Optional[DMarketItem]:
        """
        Получает предмет из Redis по ID.

        Args:
            item_id: ID предмета.

        Returns:
            Объект DMarketItem, если найден и успешно десериализован, иначе None.
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
        # Используем импортированные исключения и ловим KeyError/TypeError для from_dict
        except (RedisError, json.JSONDecodeError, TypeError, KeyError) as e:
            logger.error(
                f"Failed to get or parse item {item_id} from Redis. Error: {e}", exc_info=True
            )
            return None  # Возвращаем None при любой ошибке получения или парсинга

    async def delete_item(self, item_id: str) -> bool:
        """
        Удаляет предмет из Redis по ID.

        Args:
            item_id: ID предмета для удаления.

        Returns:
            True, если предмет был удален, False в противном случае.

        Raises:
            RedisError: Если произошла ошибка при работе с Redis.
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
            raise e  # Перевыбрасываем ошибку Redis

    async def get_and_update_price_if_lower(
        self, game_id: str, title: str, price: float
    ) -> Tuple[Optional[float], bool]:
        """
        Получает предыдущую цену предмета и обновляет ее, если новая цена ниже.

        Args:
            game_id: ID игры предмета
            title: Название предмета
            price: Новая цена предмета

        Returns:
            Кортеж (предыдущая_цена, обновлено), где:
            - предыдущая_цена: предыдущая цена предмета или None, если предмет не найден
            - обновлено: True, если цена была обновлена, False в противном случае
        """
        item_id = f"{game_id}:{title}"
        key = self._get_key(item_id)
        try:
            # Пытаемся получить текущую цену
            current_price_data = await self._redis.get(key)
            current_price = None

            if current_price_data is not None:
                try:
                    current_price = float(current_price_data.decode("utf-8"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid price format for item {item_id}: {e}")

            # Обновляем цену только если она не существует или новая цена ниже текущей
            update_needed = current_price is None or price < current_price

            if update_needed:
                await self._redis.set(key, str(price), ex=self._ttl)
                logger.debug(f"Updated price for item {item_id} from {current_price} to {price}")

            return current_price, update_needed

        except RedisError as e:
            logger.error(f"Failed to get or update price for item {item_id}: {e}", exc_info=True)
            return None, False

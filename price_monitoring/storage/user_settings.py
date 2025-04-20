import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class UserSettingsStorage:
    """
    Класс для хранения и управления настройками пользователей в Redis.

    Позволяет сохранять и получать настройки пользователей между сессиями,
    такие как:
    - выбранный режим
    - настройки фильтров (минимальная и максимальная прибыль)
    - выбранные игры

    Attributes:
        _redis: Клиент Redis для работы c базой данных
        _key_prefix: Префикс ключей для настроек пользователей
        _ttl: Время жизни (в секундах) для настроек пользователей
            (по умолчанию 7 дней)
    """

    def __init__(
        self, redis_client: redis.Redis, key_prefix: str = "user_settings:", ttl: int = 604800
    ):
        """
        Инициализация хранилища настроек пользователей.

        Args:
            redis_client: Клиент Redis для работы c базой данных
            key_prefix: Префикс ключей для настроек пользователей
            ttl: Время жизни (в секундах) для настроек пользователей
                (по умолчанию 7 дней)
        """
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._ttl = ttl

    def _get_key(self, user_id: int) -> str:
        """
        Формирует ключ Redis для хранения настроек пользователя.

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            Строка ключа для Redis
        """
        return f"{self._key_prefix}{user_id}"

    async def save_settings(self, user_id: int, settings: dict[str, Any]) -> bool:
        """
        Сохраняет настройки пользователя в Redis.

        Args:
            user_id: ID пользователя в Telegram
            settings: Словарь c настройками пользователя

        Returns:
            True если сохранение успешно, иначе False

        Raises:
            RedisError: Если произошла ошибка при работе c Redis
        """
        key = self._get_key(user_id)
        try:
            settings_json = json.dumps(settings)
            await self._redis.set(key, settings_json, ex=self._ttl)
            logger.debug(f"Saved settings for user {user_id} to Redis.")
            return True
        except (RedisError, TypeError, json.JSONDecodeError) as error:
            logger.error(
                f"Failed to save settings for user {user_id}. Error: {error}", exc_info=True
            )
            if isinstance(error, RedisError):
                raise error
            return False

    async def get_settings(self, user_id: int) -> Optional[dict[str, Any]]:
        """
        Получает настройки пользователя из Redis.

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            Словарь c настройками пользователя или None, если настройки не найдены

        Raises:
            RedisError: Если произошла ошибка при работе c Redis
        """
        key = self._get_key(user_id)
        try:
            settings_json = await self._redis.get(key)
            if settings_json is None:
                logger.debug(f"No settings found for user {user_id} in Redis.")
                return None

            settings: dict[str, Any] = json.loads(settings_json.decode("utf-8"))
            logger.debug(f"Retrieved settings for user {user_id} from Redis.")
            return settings
        except (RedisError, json.JSONDecodeError, TypeError) as error:
            logger.error(
                f"Failed to get settings for user {user_id}. Error: {error}", exc_info=True
            )
            if isinstance(error, RedisError):
                raise error
            return None

    async def update_setting(self, user_id: int, key: str, value: Any) -> bool:
        """
        Обновляет отдельную настройку пользователя.

        Args:
            user_id: ID пользователя в Telegram
            key: Ключ настройки для обновления
            value: Новое значение настройки

        Returns:
            True если обновление успешно, иначе False
        """
        try:
            # Получаем текущие настройки
            settings = await self.get_settings(user_id) or {}

            # Обновляем настройку
            settings[key] = value

            # Сохраняем обновленные настройки
            return await self.save_settings(user_id, settings)
        except RedisError as error:
            err_msg = f"Failed to update setting '{key}' for user {user_id}. Error: {error}"
            logger.error(err_msg, exc_info=True)
            return False

    async def get_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        """
        Получает значение отдельной настройки пользователя.

        Args:
            user_id: ID пользователя в Telegram
            key: Ключ настройки
            default: Значение по умолчанию, если настройка не найдена

        Returns:
            Значение настройки или default, если настройка не найдена
        """
        try:
            settings = await self.get_settings(user_id) or {}
            return settings.get(key, default)
        except RedisError as error:
            err_msg = f"Failed to get setting '{key}' for user {user_id}. Error: {error}"
            logger.error(err_msg, exc_info=True)
            return default

    async def delete_settings(self, user_id: int) -> bool:
        """
        Удаляет все настройки пользователя.

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            True если удаление успешно, иначе False
        """
        key = self._get_key(user_id)
        try:
            result = await self._redis.delete(key)
            success = result > 0
            if success:
                logger.debug(f"Deleted settings for user {user_id} from Redis.")
            else:
                logger.debug(f"No settings found for user {user_id} to delete.")
            return success
        except RedisError as error:
            err_msg = f"Failed to delete settings for user {user_id}. Error: {error}"
            logger.error(err_msg, exc_info=True)
            return False

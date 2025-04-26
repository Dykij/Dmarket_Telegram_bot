import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class UserSettingsStorage:
    """Class for storing and managing user settings in Redis.

    Allows saving and retrieving user settings between sessions,
    such as:
    - selected mode
    - filter settings (minimum and maximum profit)
    - selected games
    - language preferences

    Attributes:
        _redis: Redis client for working with the database
        _key_prefix: Prefix for user settings keys
        _ttl: Time to live (in seconds) for user settings
             (default is 7 days)
        _default_settings: Default settings for new users
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "user_settings:",
        ttl: int = 604800,
        default_settings: Optional[dict[str, Any]] = None,
    ):
        """Initialize the user settings storage.

        Args:
            redis_client: Redis client for working with the database
            key_prefix: Prefix for user settings keys
            ttl: Time to live (in seconds) for user settings
                (default is 7 days)
            default_settings: Default settings for new users
        """
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._ttl = ttl
        self._default_settings = default_settings or {
            "language": "en",
            "min_profit": 5.0,
            "max_profit": 1000.0,
            "selected_games": [],
            "notifications_enabled": True,
            "theme": "light",
        }
        # Set of keys that should be persisted even on reset
        self._persistent_keys: set[str] = {"language", "theme"}

    def _get_key(self, user_id: int) -> str:
        """Forms a Redis key for storing user settings.

        Args:
            user_id: User's Telegram ID

        Returns:
            Redis key string
        """
        return f"{self._key_prefix}{user_id}"

    async def save_settings(self, user_id: int, settings: dict[str, Any]) -> bool:
        """Saves user settings to Redis.

        Args:
            user_id: User's Telegram ID
            settings: Dictionary with user settings

        Returns:
            True if saving was successful, otherwise False

        Raises:
            RedisError: If there was an error working with Redis
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
        """Gets user settings from Redis.

        Args:
            user_id: User's Telegram ID

        Returns:
            Dictionary with user settings or None if settings not found

        Raises:
            RedisError: If there was an error working with Redis
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

    async def get_or_create_settings(self, user_id: int) -> dict[str, Any]:
        """Gets user settings or creates default settings if they don't exist.

        Args:
            user_id: User's Telegram ID

        Returns:
            Dictionary with user settings (existing or default)

        Raises:
            RedisError: If there was an error working with Redis
        """
        settings = await self.get_settings(user_id)
        if settings is None:
            settings = self._default_settings.copy()
            await self.save_settings(user_id, settings)
            logger.info(f"Created default settings for user {user_id}")
        return settings

    async def update_setting(self, user_id: int, key: str, value: Any) -> bool:
        """Updates a single user setting.

        Args:
            user_id: User's Telegram ID
            key: Setting key to update
            value: New setting value

        Returns:
            True if update was successful, otherwise False
        """
        try:
            # Get current settings or create default ones
            settings = await self.get_or_create_settings(user_id)

            # Update the setting
            settings[key] = value

            # Save updated settings
            return await self.save_settings(user_id, settings)
        except RedisError as error:
            err_msg = f"Failed to update setting '{key}' for user {user_id}. Error: {error}"
            logger.error(err_msg, exc_info=True)
            return False

    async def update_settings(self, user_id: int, new_settings: dict[str, Any]) -> bool:
        """Updates multiple user settings at once.

        Args:
            user_id: User's Telegram ID
            new_settings: Dictionary with settings to update

        Returns:
            True if update was successful, otherwise False
        """
        try:
            # Get current settings or create default ones
            settings = await self.get_or_create_settings(user_id)

            # Update settings
            settings.update(new_settings)

            # Save updated settings
            return await self.save_settings(user_id, settings)
        except RedisError as error:
            err_msg = f"Failed to update settings for user {user_id}. Error: {error}"
            logger.error(err_msg, exc_info=True)
            return False

    async def get_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        """Gets the value of a single user setting.

        Args:
            user_id: User's Telegram ID
            key: Setting key
            default: Default value if setting is not found

        Returns:
            Setting value or default if setting is not found
        """
        try:
            settings = await self.get_settings(user_id)
            if settings is None:
                # If user has no settings yet, return from default settings or provided default
                return self._default_settings.get(key, default)
            return settings.get(key, default)
        except RedisError as error:
            err_msg = f"Failed to get setting '{key}' for user {user_id}. Error: {error}"
            logger.error(err_msg, exc_info=True)
            return default

    async def delete_settings(self, user_id: int) -> bool:
        """Deletes all user settings.

        Args:
            user_id: User's Telegram ID

        Returns:
            True if deletion was successful, otherwise False
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

    async def reset_settings(self, user_id: int, preserve_persistent: bool = True) -> bool:
        """Resets user settings to default values.

        Args:
            user_id: User's Telegram ID
            preserve_persistent: Whether to preserve persistent settings like language

        Returns:
            True if reset was successful, otherwise False
        """
        try:
            current_settings = await self.get_settings(user_id)
            new_settings = self._default_settings.copy()

            # Preserve persistent settings if needed
            if preserve_persistent and current_settings:
                for key in self._persistent_keys:
                    if key in current_settings:
                        new_settings[key] = current_settings[key]

            # Save new settings
            success = await self.save_settings(user_id, new_settings)
            if success:
                logger.info(f"Reset settings for user {user_id} to defaults")
            return success
        except RedisError as error:
            err_msg = f"Failed to reset settings for user {user_id}. Error: {error}"
            logger.error(err_msg, exc_info=True)
            return False

    async def get_users_with_setting(self, key: str, value: Any = None) -> list[int]:
        """Gets a list of user IDs that have a specific setting value.

        Args:
            key: Setting key to check
            value: Setting value to match (if None, matches any value for the key)

        Returns:
            List of user IDs
        """
        try:
            # Get all keys matching the prefix
            pattern = f"{self._key_prefix}*"
            keys = await self._redis.keys(pattern)

            matching_user_ids = []

            for key_bytes in keys:
                key_str = key_bytes.decode("utf-8")
                user_id = int(key_str.replace(self._key_prefix, ""))

                settings = await self.get_settings(user_id)
                if settings and key in settings:
                    if value is None or settings[key] == value:
                        matching_user_ids.append(user_id)

            return matching_user_ids
        except (RedisError, ValueError) as error:
            logger.error(f"Failed to get users with setting '{key}': {error}", exc_info=True)
            return []

    # Integration with i18n system

    async def get_user_language(self, user_id: int, default_language: str = "en") -> str:
        """Gets user's preferred language.

        Args:
            user_id: User's Telegram ID
            default_language: Default language if not set

        Returns:
            Language code (e.g., 'en', 'ru')
        """
        return await self.get_setting(user_id, "language", default_language)

    async def set_user_language(self, user_id: int, language: str) -> bool:
        """Sets user's preferred language.

        Args:
            user_id: User's Telegram ID
            language: Language code (e.g., 'en', 'ru')

        Returns:
            True if successful, otherwise False
        """
        return await self.update_setting(user_id, "language", language)

    async def get_users_by_language(self, language: str) -> list[int]:
        """Gets a list of users who have selected a specific language.

        Args:
            language: Language code (e.g., 'en', 'ru')

        Returns:
            List of user IDs
        """
        return await self.get_users_with_setting("language", language)

    async def reset_settings(self, user_id: int, preserve_persistent: bool = True) -> bool:
        """Resets user settings to default values.

        Args:
            user_id: User's Telegram ID
            preserve_persistent: Whether to preserve persistent settings like language

        Returns:
            True if reset was successful, otherwise False
        """
        try:
            current_settings = await self.get_settings(user_id)
            new_settings = self._default_settings.copy()

            # Preserve persistent settings if needed
            if preserve_persistent and current_settings:
                for key in self._persistent_keys:
                    if key in current_settings:
                        new_settings[key] = current_settings[key]

            # Save new settings
            success = await self.save_settings(user_id, new_settings)
            if success:
                logger.info(f"Reset settings for user {user_id} to defaults")
            return success
        except RedisError as error:
            err_msg = f"Failed to reset settings for user {user_id}. Error: {error}"
            logger.error(err_msg, exc_info=True)
            return False

    async def get_users_with_setting(self, key: str, value: Any = None) -> list[int]:
        """Gets a list of user IDs that have a specific setting value.

        Args:
            key: Setting key to check
            value: Setting value to match (if None, matches any value for the key)

        Returns:
            List of user IDs
        """
        try:
            # Get all keys matching the prefix
            pattern = f"{self._key_prefix}*"
            keys = await self._redis.keys(pattern)

            matching_user_ids = []

            for key_bytes in keys:
                key_str = key_bytes.decode("utf-8")
                user_id = int(key_str.replace(self._key_prefix, ""))

                settings = await self.get_settings(user_id)
                if settings and key in settings:
                    if value is None or settings[key] == value:
                        matching_user_ids.append(user_id)

            return matching_user_ids
        except (RedisError, ValueError) as error:
            logger.error(f"Failed to get users with setting '{key}': {error}", exc_info=True)
            return []

    # Integration with i18n system

    async def get_user_language(self, user_id: int, default_language: str = "en") -> str:
        """Gets user's preferred language.

        Args:
            user_id: User's Telegram ID
            default_language: Default language if not set

        Returns:
            Language code (e.g., 'en', 'ru')
        """
        return await self.get_setting(user_id, "language", default_language)

    async def set_user_language(self, user_id: int, language: str) -> bool:
        """Sets user's preferred language.

        Args:
            user_id: User's Telegram ID
            language: Language code (e.g., 'en', 'ru')

        Returns:
            True if successful, otherwise False
        """
        return await self.update_setting(user_id, "language", language)

    async def get_users_by_language(self, language: str) -> list[int]:
        """Gets a list of users who have selected a specific language.

        Args:
            language: Language code (e.g., 'en', 'ru')

        Returns:
            List of user IDs
        """
        return await self.get_users_with_setting("language", language)

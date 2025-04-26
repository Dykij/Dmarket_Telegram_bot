"""Environment Variables Module

This module provides functions for accessing environment variables used throughout the application.
It includes helper functions for retrieving variables with proper type conversion and default values,
as well as logging when variables are missing.

The module is organized into sections for different components:
- RabbitMQ connection settings
- Redis connection settings
- Telegram bot settings
- DMarket API settings
- Parser settings
- Worker settings
- Logging settings
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# --- Helper function to get env var with logging ---
def _get_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get the value of an environment variable with logging.

    This helper function retrieves the value of an environment variable and logs a warning
    if the variable is not set and no default value is provided.

    Args:
        var_name: Name of the environment variable
        default: Default value to return if the variable is not set

    Returns:
        The value of the environment variable, or the default value,
        or None if the variable is not set and no default is provided
    """
    value = os.getenv(var_name, default)
    if value is None and default is None:
        logger.warning(f"Environment variable {var_name} is not set and has no default value.")
    return value


# --- RabbitMQ ---
def get_rabbitmq_host() -> str:
    """Get the RabbitMQ host address.

    Returns:
        The RabbitMQ host address from the RABBITMQ_HOST environment variable,
        or 'rabbitmq' as the default value
    """
    return _get_env("RABBITMQ_HOST", "rabbitmq")


def get_rabbitmq_port() -> int:
    """Get the RabbitMQ port number.

    Returns:
        The RabbitMQ port from the RABBITMQ_PORT environment variable as an integer,
        or 5672 as the default value
    """
    return int(_get_env("RABBITMQ_PORT", "5672"))


def get_rabbitmq_user() -> str:
    """Get the RabbitMQ username.

    Returns:
        The RabbitMQ username from the RABBITMQ_USER environment variable,
        or 'guest' as the default value
    """
    return _get_env("RABBITMQ_USER", "guest")


def get_rabbitmq_password() -> str:
    """Get the RabbitMQ password.

    Returns:
        The RabbitMQ password from the RABBITMQ_PASSWORD environment variable,
        or 'guest' as the default value
    """
    return os.getenv("RABBITMQ_PASSWORD", "guest")


def get_rabbitmq_virtual_host() -> str:
    """Get the RabbitMQ virtual host.

    Returns:
        The RabbitMQ virtual host from the RABBITMQ_VIRTUAL_HOST environment variable,
        or '/' as the default value
    """
    return os.getenv("RABBITMQ_VIRTUAL_HOST", "/")


# --- Redis ---
def get_redis_host() -> str:
    """Get the Redis host address.

    Returns:
        The Redis host address from the REDIS_HOST environment variable,
        or 'redis' as the default value
    """
    return _get_env("REDIS_HOST", "redis")


def get_redis_port() -> int:
    """Get the Redis port number.

    Returns:
        The Redis port from the REDIS_PORT environment variable as an integer,
        or 6379 as the default value
    """
    return int(_get_env("REDIS_PORT", "6379"))


def get_redis_db() -> int:
    """Get the Redis database number.

    Returns:
        The Redis database number from the REDIS_DB environment variable as an integer,
        or 0 as the default value
    """
    return int(_get_env("REDIS_DB", "0"))


# --- Telegram ---
def get_telegram_api_token() -> str:
    """Get the Telegram API token.

    Returns:
        The Telegram API token from the TELEGRAM_API_TOKEN environment variable,
        or None if not set
    """
    return _get_env("TELEGRAM_API_TOKEN")


def get_telegram_whitelist() -> str:
    """Get the list of allowed Telegram users.

    Returns:
        A comma-separated string of allowed Telegram user IDs from the TELEGRAM_WHITELIST
        environment variable, or None if not set
    """
    return _get_env("TELEGRAM_WHITELIST")


# --- DMarket ---
def get_dmarket_public_key() -> str:
    """Get the DMarket API public key.

    Returns:
        The DMarket public key from the DMARKET_PUBLIC_KEY environment variable,
        or None if not set
    """
    return _get_env("DMARKET_PUBLIC_KEY")


def get_dmarket_secret_key() -> str:
    """Get the DMarket API secret key.

    Returns:
        The DMarket secret key from the DMARKET_SECRET_KEY environment variable,
        or None if not set
    """
    return _get_env("DMARKET_SECRET_KEY")


def get_dmarket_game_ids() -> str:
    """Get the comma-separated list of DMarket game IDs to parse.

    Returns:
        A comma-separated string of game IDs from the DMARKET_GAME_IDS environment variable,
        or 'a8db' (CS:GO) as the default value
    """
    return os.getenv("DMARKET_GAME_IDS", "a8db")


# --- Parser Settings ---
def get_parse_delay_seconds() -> int:
    """Get the delay between parsing cycles in seconds.

    Returns:
        The delay in seconds from the PARSE_DELAY_SECONDS environment variable as an integer,
        or 60 seconds as the default value
    """
    return int(os.getenv("PARSE_DELAY_SECONDS", "60"))


def get_items_per_page() -> int:
    """Get the number of items to fetch per API request.

    Returns:
        The number of items per page from the ITEMS_PER_PAGE environment variable as an integer,
        or 100 as the default value
    """
    return int(os.getenv("ITEMS_PER_PAGE", "100"))


def get_api_request_delay_seconds() -> float:
    """Get the delay between API requests in seconds.

    Returns:
        The delay in seconds from the API_REQUEST_DELAY_SECONDS environment variable as a float,
        or 0.5 seconds as the default value
    """
    return float(os.getenv("API_REQUEST_DELAY_SECONDS", "0.5"))


def get_currency() -> str:
    """Get the currency for item prices.

    Returns:
        The currency code from the CURRENCY environment variable,
        or 'USD' as the default value
    """
    return os.getenv("CURRENCY", "USD")


# --- Worker Settings ---
def get_dmarket_commission_percent() -> float:
    """Get the DMarket commission percentage.

    Returns:
        The commission percentage from the DMARKET_COMMISSION_PERCENT environment variable as a float,
        or 5.0% as the default value
    """
    return float(_get_env("DMARKET_COMMISSION_PERCENT", "5.0"))


def get_profit_threshold_usd() -> float:
    """Get the profit threshold in USD.

    Returns:
        The profit threshold from the PROFIT_THRESHOLD_USD environment variable as a float,
        or 0.50 USD as the default value
    """
    return float(_get_env("PROFIT_THRESHOLD_USD", "0.50"))


# --- Logging ---
def get_log_level() -> str:
    """Get the logging level.

    Returns:
        The logging level from the LOG_LEVEL environment variable,
        or 'INFO' as the default value
    """
    return os.getenv("LOG_LEVEL", "INFO")


# --- Proxy Settings ---
# Direct access to proxy environment variables for backward compatibility
PROXY_LOGIN = os.getenv("PROXY_LOGIN")  # Username for proxy authentication
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")  # Password for proxy authentication
PROXY_LIST_PATH = os.getenv("PROXY_LIST_PATH", "proxies.txt")  # Path to the file with proxy list

# --- Export functions as constants for backward compatibility ---
# These constants are provided for backward compatibility with code that directly
# imports these values instead of calling the getter functions
DMARKET_PUBLIC_KEY = get_dmarket_public_key()
DMARKET_SECRET_KEY = get_dmarket_secret_key()
RABBITMQ_HOST = get_rabbitmq_host()
RABBITMQ_PORT = get_rabbitmq_port()
RABBITMQ_USER = get_rabbitmq_user()
RABBITMQ_PASSWORD = get_rabbitmq_password()
RABBITMQ_VIRTUAL_HOST = get_rabbitmq_virtual_host()
DMARKET_GAME_IDS = get_dmarket_game_ids()
PARSE_DELAY_SECONDS = get_parse_delay_seconds()
ITEMS_PER_PAGE = get_items_per_page()
API_REQUEST_DELAY_SECONDS = get_api_request_delay_seconds()
CURRENCY = get_currency()
LOG_LEVEL = get_log_level()

# --- Deprecated/Old Variables ---
# These variables are no longer used but kept as comments for reference
# CSMONEY_OFFER_LIMIT = int(os.getenv("CSMONEY_OFFER_LIMIT", "100"))
# ... other old variables ...

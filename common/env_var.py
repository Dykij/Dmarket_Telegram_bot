import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)


# --- Helper function to get env var with logging ---
def _get_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Получает значение переменной окружения.

    Args:
        var_name: Имя переменной окружения
        default: Значение по умолчанию

    Returns:
        Значение переменной окружения или default, или None, если значение не найдено и default не задан
    """
    value = os.getenv(var_name, default)
    if value is None and default is None:
         logger.warning(
             f"Переменная окружения {var_name} не установлена и не имеет значения по умолчанию."
         )
    return value


# --- RabbitMQ ---
def get_rabbitmq_host() -> str:
    """Возвращает хост RabbitMQ."""
    return _get_env("RABBITMQ_HOST", "rabbitmq")


def get_rabbitmq_port() -> int:
    """Возвращает порт RabbitMQ."""
    return int(_get_env("RABBITMQ_PORT", "5672"))


def get_rabbitmq_user() -> str:
    """Возвращает пользователя RabbitMQ."""
    return _get_env("RABBITMQ_USER", "guest")


def get_rabbitmq_password() -> str:
    """Возвращает пароль пользователя RabbitMQ."""
    return os.getenv("RABBITMQ_PASSWORD", "guest")


def get_rabbitmq_virtual_host() -> str:
    """Возвращает виртуальный хост RabbitMQ."""
    return os.getenv("RABBITMQ_VIRTUAL_HOST", "/")


# --- Redis ---
def get_redis_host() -> str:
    """Возвращает хост Redis."""
    return _get_env("REDIS_HOST", "redis")


def get_redis_port() -> int:
    """Возвращает порт Redis."""
    return int(_get_env("REDIS_PORT", "6379"))


def get_redis_db() -> int:
    """Возвращает номер базы данных Redis."""
    return int(_get_env("REDIS_DB", "0"))


# --- Telegram ---
def get_telegram_api_token() -> str:
    """Возвращает API токен Telegram."""
    return _get_env("TELEGRAM_API_TOKEN")


def get_telegram_whitelist() -> str:
    """Возвращает список разрешенных пользователей Telegram в виде строки, разделенной запятыми, или None."""
    return _get_env("TELEGRAM_WHITELIST")


# --- DMarket ---
def get_dmarket_public_key() -> str:
    """Возвращает публичный ключ DMarket."""
    return _get_env("DMARKET_PUBLIC_KEY")


def get_dmarket_secret_key() -> str:
    """Возвращает секретный ключ DMarket."""
    return _get_env("DMARKET_SECRET_KEY")


def get_dmarket_game_ids() -> List[str]:
    """Возвращает список ID игр DMarket."""
    ids_str = os.getenv("DMARKET_GAME_IDS", "a8db")
    return [item.strip() for item in ids_str.split(",")]


# --- Parser Settings ---
def get_parse_delay_seconds() -> int:
    """Возвращает задержку между парсингами в секундах."""
    return int(os.getenv("PARSE_DELAY_SECONDS", "60"))


def get_items_per_page() -> int:
    """Возвращает количество предметов на странице."""
    return int(os.getenv("ITEMS_PER_PAGE", "100"))


def get_api_request_delay_seconds() -> float:
    """Возвращает задержку между запросами к API в секундах."""
    return float(os.getenv("API_REQUEST_DELAY_SECONDS", "0.5"))


def get_currency() -> str:
    """Возвращает валюту."""
    return os.getenv("CURRENCY", "USD")


# --- Worker Settings ---
def get_dmarket_commission_percent() -> float:
    """Возвращает процент комиссии DMarket."""
    return float(_get_env("DMARKET_COMMISSION_PERCENT", "5.0"))


def get_profit_threshold_usd() -> float:
    """Возвращает порог прибыли в долларах США."""
    return float(_get_env("PROFIT_THRESHOLD_USD", "0.50"))


# --- Logging ---
def get_log_level() -> str:
    """Возвращает уровень логирования."""
    return os.getenv("LOG_LEVEL", "INFO")


# --- Proxy (Keep existing proxy settings if needed) ---
PROXY_LOGIN = os.getenv("PROXY_LOGIN")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
PROXY_LIST_PATH = os.getenv("PROXY_LIST_PATH", "proxies.txt")

# --- Экспорт функций как констант для обратной совместимости ---
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

# --- Deprecated/Old Vars (Commented out or removed if sure) ---
# CSMONEY_OFFER_LIMIT = int(os.getenv("CSMONEY_OFFER_LIMIT", "100"))
# ... other old variables ...

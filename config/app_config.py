"""Модуль конфигурации приложения.

Этот модуль предоставляет интерфейс для загрузки, проверки и доступа
к конфигурационным параметрам приложения из различных источников.
"""

from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Конфигурация приложения для тестов.

    Представляет упрощенную версию конфигурации для использования в тестах.
    """

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_url: str = "redis://localhost:6379/0"

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # Telegram
    telegram_bot_token: str = "test_token"
    telegram_admin_id: int = 123456789

    # DMarket
    dmarket_api_url: str = "https://api.dmarket.com"
    dmarket_game_ids: List[str] = field(default_factory=lambda: ["a8db"])
    dmarket_api_key: str = ""
    dmarket_api_secret: str = ""

    # Прокси
    proxies_file: str = ""

    # Задержки и тайминги
    parse_delay_seconds: float = 0.1
    api_request_delay_seconds: float = 0.1

    # Логирование
    log_level: str = "INFO"

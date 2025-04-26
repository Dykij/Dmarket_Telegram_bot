"""Модуль конфигурации приложения.

Этот модуль предоставляет интерфейс для загрузки, проверки и доступа
к конфигурационным параметрам приложения из различных источников.
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from marshmallow import Schema, ValidationError, fields, validates_schema

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """Перечисление источников конфигурации."""

    ENV = "env"  # Переменные окружения
    FILE = "file"  # Файл конфигурации
    DEFAULT = "default"  # Значения по умолчанию


class ConfigStrategy(ABC):
    """Абстрактный класс для стратегии загрузки конфигурации.

    Определяет интерфейс для различных стратегий загрузки конфигурации,
    таких как загрузка из переменных окружения, файла конфигурации и т.д.
    """

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Загружает конфигурационные параметры.

        Returns:
            Словарь с конфигурационными параметрами
        """
        pass


class EnvConfigStrategy(ConfigStrategy):
    """Стратегия загрузки конфигурации из переменных окружения.

    Загружает конфигурационные параметры из переменных окружения,
    опционально из файла .env.
    """

    def __init__(self, env_file: Optional[str] = None):
        """Инициализирует стратегию с опциональным путем к файлу .env.

        Args:
            env_file: Путь к файлу .env
        """
        self.env_file = env_file

    def load(self) -> dict[str, Any]:
        """Загружает конфигурационные параметры из переменных окружения.

        Returns:
            Словарь с конфигурационными параметрами
        """
        if self.env_file and Path(self.env_file).exists():
            load_dotenv(self.env_file)
            logger.info(f"Loaded environment variables from {self.env_file}")

        # Загружаем только те параметры, которые нам нужны
        # Это не все переменные окружения, а только релевантные для конфигурации
        config = {
            # Redis
            "redis_host": os.getenv("REDIS_HOST", "localhost"),
            "redis_port": int(os.getenv("REDIS_PORT", "6379")),
            "redis_db": int(os.getenv("REDIS_DB", "0")),
            "redis_password": os.getenv("REDIS_PASSWORD", ""),
            # RabbitMQ
            "rabbitmq_host": os.getenv("RABBITMQ_HOST", "localhost"),
            "rabbitmq_port": int(os.getenv("RABBITMQ_PORT", "5672")),
            "rabbitmq_user": os.getenv("RABBITMQ_USER", "guest"),
            "rabbitmq_password": os.getenv("RABBITMQ_PASSWORD", "guest"),
            "rabbitmq_vhost": os.getenv("RABBITMQ_VHOST", "/"),
            # Telegram
            "telegram_token": os.getenv("TELEGRAM_TOKEN", ""),
            "telegram_admin_id": int(os.getenv("TELEGRAM_ADMIN_ID", "0")),
            # DMarket
            "dmarket_api_url": os.getenv("DMARKET_API_URL", "https://api.dmarket.com"),
            "dmarket_game_ids": os.getenv("DMARKET_GAME_IDS", "").split(","),
            "items_per_page": int(os.getenv("ITEMS_PER_PAGE", "100")),
            "currency": os.getenv("CURRENCY", "USD"),
            # Прокси
            "proxies_file": os.getenv("PROXIES_FILE", ""),
            # Задержки и тайминги
            "parse_delay_seconds": float(os.getenv("PARSE_DELAY_SECONDS", "1.0")),
            "api_request_delay_seconds": float(os.getenv("API_REQUEST_DELAY_SECONDS", "0.5")),
            # Логирование
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        }

        logger.info("Loaded configuration from environment variables")
        return config


class FileConfigStrategy(ConfigStrategy):
    """Стратегия загрузки конфигурации из файла.

    Загружает конфигурационные параметры из YAML или JSON файла.
    """

    def __init__(self, config_file: str):
        """Инициализирует стратегию с путем к файлу конфигурации.

        Args:
            config_file: Путь к файлу конфигурации (YAML или JSON)
        """
        self.config_file = config_file

    def load(self) -> dict[str, Any]:
        """Загружает конфигурационные параметры из файла.

        Returns:
            Словарь с конфигурационными параметрами

        Raises:
            FileNotFoundError: Если файл конфигурации не найден
            ValueError: Если формат файла не поддерживается
        """
        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        file_ext = config_path.suffix.lower()

        if file_ext in [".yaml", ".yml"]:
            with config_path.open() as f:
                config = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config file format: {file_ext}")

        logger.info(f"Loaded configuration from file {self.config_file}")
        return config


class DefaultConfigStrategy(ConfigStrategy):
    """Стратегия загрузки конфигурации по умолчанию.

    Предоставляет значения по умолчанию для всех конфигурационных параметров.
    """

    def load(self) -> dict[str, Any]:
        """Загружает конфигурационные параметры по умолчанию.

        Returns:
            Словарь с конфигурационными параметрами по умолчанию
        """
        return {
            # Redis
            "redis_host": "localhost",
            "redis_port": 6379,
            "redis_db": 0,
            "redis_password": "",
            # RabbitMQ
            "rabbitmq_host": "localhost",
            "rabbitmq_port": 5672,
            "rabbitmq_user": "guest",
            "rabbitmq_password": "guest",
            "rabbitmq_vhost": "/",
            # Telegram
            "telegram_token": "",
            "telegram_admin_id": 0,
            # DMarket
            "dmarket_api_url": "https://api.dmarket.com",
            "dmarket_game_ids": ["a8db"],  # CS2
            "items_per_page": 100,
            "currency": "USD",
            # Задержки и тайминги
            "parse_delay_seconds": 1.0,
            "api_request_delay_seconds": 0.5,
            # Логирование
            "log_level": "INFO",
        }


class ConfigSchema(Schema):
    """Схема для валидации конфигурационных параметров.

    Определяет типы и ограничения для всех конфигурационных параметров.
    """

    # Константы для валидации
    MAX_PORT = 65535
    MAX_REDIS_DB = 15
    MAX_ITEMS_PER_PAGE = 1000

    # Redis
    redis_host = fields.String(required=True)
    redis_port = fields.Integer(required=True, validate=lambda n: 1 <= n <= ConfigSchema.MAX_PORT)
    redis_db = fields.Integer(required=True, validate=lambda n: 0 <= n <= ConfigSchema.MAX_REDIS_DB)
    redis_password = fields.String(required=False, allow_none=True, missing="")

    # RabbitMQ
    rabbitmq_host = fields.String(required=True)
    rabbitmq_port = fields.Integer(required=True, validate=lambda n: 1 <= n <= ConfigSchema.MAX_PORT)
    rabbitmq_user = fields.String(required=True)
    rabbitmq_password = fields.String(required=True)
    rabbitmq_vhost = fields.String(required=True)

    # Telegram
    telegram_token = fields.String(required=False, allow_none=True, missing="")
    telegram_admin_id = fields.Integer(required=False, allow_none=True, missing=0)

    # DMarket
    dmarket_api_url = fields.String(required=True)
    dmarket_game_ids = fields.List(fields.String(), required=True)
    items_per_page = fields.Integer(
        required=True, validate=lambda n: 1 <= n <= ConfigSchema.MAX_ITEMS_PER_PAGE
    )
    currency = fields.String(required=True)

    # Прокси
    proxies_file = fields.String(required=False, allow_none=True, missing="")

    # Задержки и тайминги
    parse_delay_seconds = fields.Float(required=True, validate=lambda n: n >= 0)
    api_request_delay_seconds = fields.Float(required=True, validate=lambda n: n >= 0)

    # Логирование
    log_level = fields.String(
        required=True, validate=lambda s: s in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )

    @validates_schema
    def validate_schema(self, data, **_):
        """Дополнительная валидация данных схемы.

        Args:
            data: Данные для валидации

        Raises:
            ValidationError: Если валидация не прошла
        """
        # Проверка наличия либо API токена, либо файла с токенами
        if not data.get("telegram_token") and not data.get("telegram_admin_id"):
            logger.warning("Neither Telegram token nor admin ID is specified")

        # Проверка валидности game_ids
        if not data.get("dmarket_game_ids"):
            raise ValidationError("At least one game ID must be specified")


@dataclass
class Config:
    """Конфигурация приложения.

    Содержит все параметры конфигурации, загруженные из различных источников,
    с приоритетом: переменные окружения > файл конфигурации > значения по умолчанию.
    """

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"

    # Telegram
    telegram_token: str = ""
    telegram_admin_id: int = 0

    # DMarket
    dmarket_api_url: str = "https://api.dmarket.com"
    dmarket_game_ids: list = field(default_factory=lambda: ["a8db"])  # CS2
    items_per_page: int = 100
    currency: str = "USD"

    # Прокси
    proxies_file: str = ""

    # Задержки и тайминги
    parse_delay_seconds: float = 1.0
    api_request_delay_seconds: float = 0.5

    # Логирование
    log_level: str = "INFO"

    @classmethod
    def load(cls, env_file: Optional[str] = None, config_file: Optional[str] = None) -> "Config":
        """Загружает и возвращает конфигурацию из всех источников с приоритетом.

        Args:
            env_file: Путь к файлу .env
            config_file: Путь к файлу конфигурации

        Returns:
            Объект конфигурации
        """
        # Загружаем дефолтную конфигурацию
        config_data = DefaultConfigStrategy().load()

        # Если указан файл конфигурации, загружаем из него
        if config_file:
            try:
                file_config = FileConfigStrategy(config_file).load()
                config_data.update(file_config)
            except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
                logger.error(f"Failed to load config from file: {e}")

        # Загружаем из переменных окружения (приоритетнее всего)
        env_config = EnvConfigStrategy(env_file).load()
        config_data.update(env_config)

        # Валидируем конфигурацию
        try:
            validated_data = ConfigSchema().load(config_data)
            logger.info("Configuration validated successfully")
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e.messages}")
            # В случае ошибки валидации используем исходные данные, но логируем предупреждение
            validated_data = config_data
            logger.warning("Using unvalidated configuration")

        return cls(**validated_data)


# Глобальный экземпляр конфигурации
app_config: Optional[Config] = None


def init_config(env_file: Optional[str] = None, config_file: Optional[str] = None) -> Config:
    """Инициализирует и возвращает глобальный экземпляр конфигурации.

    Args:
        env_file: Путь к файлу .env
        config_file: Путь к файлу конфигурации

    Returns:
        Глобальный экземпляр конфигурации
    """
    # Вместо использования global обновляем app_config через возвращаемое значение
    config = Config.load(env_file, config_file)
    return config


def get_config() -> Config:
    """Возвращает глобальный экземпляр конфигурации.

    Если конфигурация еще не инициализирована, инициализирует ее
    с параметрами по умолчанию.

    Returns:
        Глобальный экземпляр конфигурации
    """
    global app_config
    if app_config is None:
        app_config = init_config()
    return app_config

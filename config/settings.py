"""
Модуль для управления настройками проекта с поддержкой 
различных окружений и динамического обновления.
"""

import json
import logging
import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Типы для функций обратного вызова
SettingsChangedCallback = Callable[["Settings", Dict[str, Any]], None]


class Environment(str, Enum):
    """Поддерживаемые окружения для конфигурации."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseModel):
    """
    Основной класс настроек приложения.
    
    Включает все конфигурационные параметры и обеспечивает
    их валидацию через Pydantic.
    """
    # Общие настройки
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Текущее окружение (development, testing, production)"
    )
    debug: bool = Field(
        default=False,
        description="Режим отладки"
    )
    
    # Настройки Redis
    redis_host: str = Field(
        default="localhost",
        description="Хост Redis сервера"
    )
    redis_port: int = Field(
        default=6379,
        description="Порт Redis сервера"
    )
    redis_db: int = Field(
        default=0,
        description="Номер базы данных Redis"
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Пароль для Redis (опционально)"
    )
    
    # Настройки RabbitMQ
    rabbitmq_host: str = Field(
        default="localhost",
        description="Хост RabbitMQ сервера"
    )
    rabbitmq_port: int = Field(
        default=5672,
        description="Порт RabbitMQ сервера"
    )
    rabbitmq_user: str = Field(
        default="guest",
        description="Имя пользователя RabbitMQ"
    )
    rabbitmq_password: str = Field(
        default="guest",
        description="Пароль пользователя RabbitMQ"
    )
    rabbitmq_vhost: str = Field(
        default="/",
        description="Виртуальный хост RabbitMQ"
    )
    
    # Настройки Telegram
    telegram_bot_token: str = Field(
        default="",
        description="Токен Telegram бота"
    )
    telegram_allowed_users: List[int] = Field(
        default=[],
        description="Список разрешенных пользователей (Telegram ID)"
    )
    
    # Настройки DMarket
    dmarket_api_url: str = Field(
        default="https://api.dmarket.com",
        description="URL API DMarket"
    )
    dmarket_api_public_key: str = Field(
        default="",
        description="Публичный ключ API DMarket"
    )
    dmarket_api_secret_key: str = Field(
        default="",
        description="Секретный ключ API DMarket"
    )
    
    # Настройки интернационализации
    i18n_default_language: str = Field(
        default="en",
        description="Язык по умолчанию"
    )
    i18n_available_languages: List[str] = Field(
        default=["en", "ru", "uk"],
        description="Список доступных языков"
    )
    i18n_locale_dir: str = Field(
        default="locale",
        description="Директория с файлами локализации"
    )
    
    # Настройки масштабирования
    max_parser_instances: int = Field(
        default=1,
        description="Максимальное количество экземпляров парсера"
    )
    max_handler_instances: int = Field(
        default=1,
        description="Максимальное количество экземпляров обработчика"
    )
    use_proxy: bool = Field(
        default=False,
        description="Использовать прокси для запросов к API"
    )
    
    # Настройки хранилища данных
    data_dir: str = Field(
        default="data",
        description="Директория для хранения данных"
    )
    data_compression: bool = Field(
        default=True,
        description="Использовать сжатие данных"
    )
    data_compression_algorithm: str = Field(
        default="gzip",
        description="Алгоритм сжатия (gzip, zlib, brotli)"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        validate_assignment = True
        extra = "ignore"


# Глобальная переменная для хранения текущих настроек
_settings: Optional[Settings] = None

# Список функций обратного вызова при изменении настроек
_settings_changed_callbacks: List[SettingsChangedCallback] = []


def register_settings_changed_callback(callback: SettingsChangedCallback) -> None:
    """
    Регистрирует функцию обратного вызова, которая будет вызвана
    при изменении настроек.
    
    Args:
        callback: Функция, которая будет вызвана при изменении настроек.
                 Принимает экземпляр Settings и словарь измененных параметров.
    """
    if callback not in _settings_changed_callbacks:
        _settings_changed_callbacks.append(callback)
        logger.debug(f"Зарегистрирована функция обратного вызова {callback.__name__}")


def _call_settings_changed_callbacks(
    settings: Settings, changed_params: Dict[str, Any]
) -> None:
    """
    Вызывает все зарегистрированные функции обратного вызова.
    
    Args:
        settings: Текущий экземпляр настроек
        changed_params: Словарь измененных параметров
    """
    for callback in _settings_changed_callbacks:
        try:
            callback(settings, changed_params)
        except Exception as e:
            logger.error(
                f"Ошибка при вызове функции обратного вызова {callback.__name__}: {e}"
            )


@lru_cache()
def get_settings() -> Settings:
    """
    Возвращает текущие настройки приложения.
    
    Returns:
        Экземпляр класса Settings с текущими настройками
    """
    global _settings
    
    if _settings is None:
        # Загружаем настройки из различных источников
        config_sources = _load_config_sources()
        
        # Создаем объект настроек
        _settings = Settings(**config_sources)
        logger.info(f"Настройки загружены для окружения: {_settings.environment}")
    
    return _settings


def reload_settings() -> Settings:
    """
    Перезагружает настройки из всех источников.
    
    Returns:
        Обновленный экземпляр настроек
    """
    global _settings
    
    # Сохраняем старые настройки для сравнения
    old_settings_dict = {}
    if _settings is not None:
        old_settings_dict = _settings.dict()
    
    # Загружаем настройки из различных источников
    config_sources = _load_config_sources()
    
    # Создаем новый объект настроек
    _settings = Settings(**config_sources)
    
    # Определяем, какие параметры изменились
    new_settings_dict = _settings.dict()
    changed_params = {
        k: new_settings_dict[k]
        for k in new_settings_dict
        if k not in old_settings_dict or old_settings_dict[k] != new_settings_dict[k]
    }
    
    if changed_params:
        logger.info(f"Настройки перезагружены, изменения: {list(changed_params.keys())}")
        _call_settings_changed_callbacks(_settings, changed_params)
    else:
        logger.info("Настройки перезагружены, изменений нет")
    
    # Очищаем кэш функции get_settings
    get_settings.cache_clear()
    
    return _settings


def update_settings(
    **kwargs
) -> Settings:
    """
    Обновляет настройки динамически во время выполнения.
    
    Args:
        **kwargs: Параметры для обновления в формате имя_параметра=значение
        
    Returns:
        Обновленный экземпляр настроек
    """
    global _settings
    
    if _settings is None:
        _settings = get_settings()
    
    # Обновляем параметры
    for key, value in kwargs.items():
        if hasattr(_settings, key):
            setattr(_settings, key, value)
    
    # Очищаем кэш функции get_settings
    get_settings.cache_clear()
    
    # Вызываем функции обратного вызова
    _call_settings_changed_callbacks(_settings, kwargs)
    
    logger.info(f"Настройки обновлены: {list(kwargs.keys())}")
    
    return _settings


def _load_config_sources() -> Dict[str, Any]:
    """
    Загружает конфигурацию из различных источников в порядке приоритета:
    1. Переменные окружения
    2. Файлы .env
    3. YAML/JSON файлы конфигурации
    4. Значения по умолчанию в модели Settings
    
    Returns:
        Словарь с параметрами конфигурации
    """
    config: Dict[str, Any] = {}
    
    # Загружаем из файлов конфигурации
    config_files = _get_config_files()
    for config_file in config_files:
        try:
            file_config = _load_config_file(config_file)
            if file_config:
                config.update(file_config)
        except Exception as e:
            logger.warning(f"Не удалось загрузить конфигурацию из {config_file}: {e}")
    
    # Загружаем из переменных окружения (имеют приоритет над файлами)
    env_config = {
        key.lower(): value
        for key, value in os.environ.items()
        if key.startswith(("APP_", "DMARKET_", "TELEGRAM_", "REDIS_", "RABBITMQ_"))
    }
    if env_config:
        config.update(env_config)
    
    return config


def _get_config_files() -> List[Path]:
    """
    Находит все файлы конфигурации в порядке приоритета.
    
    Returns:
        Список путей к файлам конфигурации
    """
    # Определяем возможные имена файлов
    config_file_names = [
        "config.json",
        "config.yaml",
        "config.yml",
        f"config.{os.environ.get('ENVIRONMENT', 'development')}.json",
        f"config.{os.environ.get('ENVIRONMENT', 'development')}.yaml",
        f"config.{os.environ.get('ENVIRONMENT', 'development')}.yml",
    ]
    
    # Определяем возможные пути к файлам
    base_paths = [
        Path("."),
        Path("config"),
        Path(os.environ.get("CONFIG_DIR", ".")),
    ]
    
    # Собираем все возможные пути к файлам
    config_files = []
    for base_path in base_paths:
        for file_name in config_file_names:
            file_path = base_path / file_name
            if file_path.exists():
                config_files.append(file_path)
    
    return config_files


def _load_config_file(file_path: Path) -> Dict[str, Any]:
    """
    Загружает конфигурацию из файла JSON или YAML.
    
    Args:
        file_path: Путь к файлу конфигурации
        
    Returns:
        Словарь с параметрами конфигурации
    """
    if not file_path.exists():
        return {}
    
    with open(file_path, "r", encoding="utf-8") as file:
        if file_path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(file)
        elif file_path.suffix == ".json":
            return json.load(file)
        else:
            logger.warning(f"Неподдерживаемый формат файла конфигурации: {file_path}")
            return {}

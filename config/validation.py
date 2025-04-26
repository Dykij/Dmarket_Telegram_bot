"""
Модуль для валидации конфигурационных параметров.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import ValidationError

from .settings import Settings

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Исключение, возникающее при ошибке валидации конфигурации."""
    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors
        error_messages = [
            f"{'.'.join(e['loc'])}: {e['msg']}" for e in errors
        ]
        message = f"Ошибки валидации конфигурации: {', '.join(error_messages)}"
        super().__init__(message)


def validate_config(config: Dict[str, Any] = None) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
    """
    Проверяет правильность конфигурационных параметров.
    
    Args:
        config: Словарь с параметрами для валидации. Если None,
                используются текущие настройки.
    
    Returns:
        Кортеж (bool, list):
            - True если конфигурация валидна, иначе False
            - Список ошибок валидации или None, если ошибок нет
    """
    try:
        if config is not None:
            # Валидируем предоставленную конфигурацию
            Settings(**config)
        else:
            # Импортируем здесь, чтобы избежать циклических импортов
            from .settings import get_settings
            
            # Перепроверяем текущие настройки
            settings = get_settings()
            
            # Дополнительные проверки, не охваченные Pydantic
            _validate_telegram_token(settings.telegram_bot_token)
            _validate_api_keys(settings.dmarket_api_public_key, settings.dmarket_api_secret_key)
            _validate_directory_permissions(settings.data_dir, settings.i18n_locale_dir)
        
        return True, None
    
    except ValidationError as e:
        errors = e.errors()
        logger.error(f"Ошибка валидации конфигурации: {errors}")
        return False, errors
    
    except Exception as e:
        logger.error(f"Ошибка при валидации конфигурации: {e}")
        return False, [{"loc": ["unknown"], "msg": str(e), "type": "validation_error"}]


def _validate_telegram_token(token: str) -> None:
    """Проверяет правильность формата токена Telegram."""
    if token and not re.match(r"^\d+:[A-Za-z0-9_-]+$", token):
        raise ValueError("Неверный формат токена Telegram бота")


def _validate_api_keys(public_key: str, secret_key: str) -> None:
    """Проверяет API ключи DMarket."""
    if (public_key and not secret_key) or (not public_key and secret_key):
        raise ValueError("Должны быть указаны оба ключа API DMarket или ни одного")


def _validate_directory_permissions(data_dir: str, locale_dir: str) -> None:
    """Проверяет права доступа к директориям."""
    import os
    from pathlib import Path
    
    # Проверяем директорию данных
    data_path = Path(data_dir)
    if not data_path.exists():
        try:
            os.makedirs(data_path, exist_ok=True)
        except PermissionError:
            raise ValueError(f"Нет прав на создание директории данных: {data_dir}")
    elif not os.access(data_path, os.W_OK):
        raise ValueError(f"Нет прав на запись в директорию данных: {data_dir}")
    
    # Проверяем директорию локализации
    locale_path = Path(locale_dir)
    if not locale_path.exists():
        try:
            os.makedirs(locale_path, exist_ok=True)
        except PermissionError:
            raise ValueError(f"Нет прав на создание директории локализации: {locale_dir}")
    elif not os.access(locale_path, os.R_OK):
        raise ValueError(f"Нет прав на чтение директории локализации: {locale_dir}")

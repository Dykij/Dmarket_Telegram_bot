"""Модуль для валидации конфигурационных параметров."""

import logging
import os
from pathlib import Path
import re
from typing import Any, Optional

from pydantic import ValidationError

from .settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Исключение, возникающее при ошибке валидации конфигурации."""

    def __init__(self, errors: list[dict[str, Any]]):
        self.errors = errors
        error_messages = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors]
        message = f"Ошибки валидации конфигурации: {', '.join(error_messages)}"
        super().__init__(message)


def validate_config(
    config: Optional[dict[str, Any]] = None,
) -> tuple[bool, Optional[list[dict[str, Any]]]]:
    """Проверяет правильность конфигурационных параметров.

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
            _validated_settings = Settings(**config)
            # Дополнительные проверки для предоставленной конфигурации
            _validate_telegram_token(_validated_settings.telegram_bot_token)
            _validate_api_keys(
                _validated_settings.dmarket_api_public_key,
                _validated_settings.dmarket_api_secret_key,
            )
            _validate_directory_permissions(
                _validated_settings.data_dir, _validated_settings.i18n_locale_dir
            )
        else:
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

    except ValueError as e:  # Ловим конкретные ошибки валидации
        logger.error(f"Ошибка при валидации конфигурации: {e}")
        # Формируем ошибку в формате Pydantic для единообразия
        return False, [{"loc": ["custom_validation"], "msg": str(e), "type": "value_error"}]

    except Exception as e:  # Ловим остальные непредвиденные ошибки
        logger.exception(
            "Непредвиденная ошибка при валидации конфигурации."
        )  # Используем exception для stack trace
        return False, [{"loc": ["unknown"], "msg": str(e), "type": "unexpected_error"}]


def _validate_telegram_token(token: Optional[str]) -> None:
    """Проверяет правильность формата токена Telegram."""
    if token and not re.match(r"^\d+:[A-Za-z0-9_-]+$", token):
        raise ValueError("Неверный формат токена Telegram бота")


def _validate_api_keys(public_key: Optional[str], secret_key: Optional[str]) -> None:
    """Проверяет API ключи DMarket."""
    if (public_key and not secret_key) or (not public_key and secret_key):
        raise ValueError("Должны быть указаны оба ключа API DMarket или ни одного")


def _validate_directory_permissions(data_dir: str, locale_dir: str) -> None:
    """Проверяет права доступа к директориям."""
    # Проверяем директорию данных
    data_path = Path(data_dir)
    try:
        data_path.mkdir(parents=True, exist_ok=True)  # Создаем, если нет
        # Проверяем права на запись после создания/проверки существования
        if not os.access(data_path, os.W_OK):
            # Попытка создать временный файл для более надежной проверки записи
            test_file = data_path / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except OSError as e:
                raise ValueError(f"Нет прав на запись в директорию данных: {data_dir}") from e
    except PermissionError as e:
        raise ValueError(f"Нет прав на создание директории данных: {data_dir}") from e
    except Exception as e:  # Ловим другие возможные ошибки при работе с ФС
        raise ValueError(f"Ошибка при проверке директории данных {data_dir}: {e}") from e

    # Проверяем директорию локализации
    locale_path = Path(locale_dir)
    try:
        # Директорию локализации не создаем автоматически, она должна быть
        if not locale_path.is_dir():
            raise ValueError(f"Директория локализации не найдена: {locale_dir}")
        if not os.access(locale_path, os.R_OK):
            raise ValueError(f"Нет прав на чтение директории локализации: {locale_dir}")
    except PermissionError as e:
        raise ValueError(f"Нет прав на доступ к директории локализации: {locale_dir}") from e
    except Exception as e:  # Ловим другие возможные ошибки при работе с ФС
        raise ValueError(f"Ошибка при проверке директории локализации {locale_dir}: {e}") from e

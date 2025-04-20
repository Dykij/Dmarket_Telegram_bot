"""
Модуль настройки логирования для системы мониторинга цен.

Предоставляет функциональность для настройки системного логирования
с использованием YAML конфигурации, что позволяет гибко настраивать
форматы, обработчики и уровни логирования для разных компонентов.
"""

import logging
import logging.config
import os

import yaml


def setup_logging(
    default_path="logging.yaml", default_level=logging.INFO, env_key="LOG_CFG"
):  # pragma: no cover
    """
    Настраивает систему логирования на основе YAML конфигурации.

    Загружает конфигурацию логирования из указанного YAML файла.
    Если файл не найден или произошла ошибка при чтении,
    используется базовая конфигурация с указанным уровнем логирования.

    Args:
        default_path: Путь к файлу конфигурации логирования (по умолчанию "logging.yaml")
        default_level: Уровень логирования по умолчанию (по умолчанию INFO)
        env_key: Имя переменной окружения, которая может содержать
                альтернативный путь к конфигурации (по умолчанию "LOG_CFG")
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, encoding="utf8") as f:
            try:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)
            except Exception as exc:
                print(exc)
                print("Error in Logging Configuration. Using default configs")
                logging.basicConfig(level=default_level)
    else:
        logging.basicConfig(level=default_level)
        print("Failed to load configuration file. Using default configs")

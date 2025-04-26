"""
Центральный модуль конфигурации для проекта Dmarket Telegram Bot.

Этот модуль предоставляет единый интерфейс для доступа к конфигурации
всех компонентов системы, поддерживая разные окружения и валидацию параметров.
"""

from .settings import (
    Settings,
    get_settings,
    reload_settings,
    update_settings,
    register_settings_changed_callback
)
from .validation import validate_config

__all__ = [
    'Settings',
    'get_settings',
    'reload_settings',
    'update_settings',
    'register_settings_changed_callback',
    'validate_config',
]

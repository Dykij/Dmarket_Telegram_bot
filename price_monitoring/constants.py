"""
Константы для системы мониторинга цен.

Модуль содержит именованные константы для именования очередей сообщений,
ключей Redis и других параметров системы, обеспечивая единообразие
и предотвращая опечатки при использовании этих значений в коде.
"""


class QueueNames:
    """
    Имена очередей сообщений в системе.

    Определяет стандартные имена для очередей сообщений,
    используемых для обмена данными между компонентами системы.
    """

    DMARKET_RESULT = "dmarket_result"
    DMARKET_MARKET_NAME = "dmarket_market_name"


class RedisKeys:
    """
    Ключи для хранения данных в Redis.

    Определяет стандартные ключи для хранения различных типов
    данных в Redis, обеспечивая единообразную структуру хранилища.
    """

    DMARKET_ITEM_SCHEDULE = "dmarket_item_schedule"
    DMARKET_PROXIES = "dmarket_proxies"
    DMARKET_ITEMS = "prices:dmarket:"


class TelegramRedisKeys:
    """
    Ключи для хранения данных Telegram в Redis.

    Определяет стандартные ключи для хранения настроек и данных,
    связанных с работой Telegram-бота в Redis.
    """

    WHITELIST_KEY = "telegram:whitelist"
    SETTINGS_KEY = "telegram:settings"

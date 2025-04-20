# filepath: d:\steam_dmarket-master\price_monitoring\system_constants.py
"""
Модуль содержит константы для работы системы мониторинга цен.

Здесь определены имена очередей сообщений, ключи для хранения данных в Redis
и константы для работы с Telegram-ботом.

Примечание: Эти константы предназначены для использования в будущих
версиях системы и могут быть полезны при расширении функциональности.
"""


class QueueNames:
    """
    Имена очередей сообщений в RabbitMQ.

    Определяет стандартные имена для очередей сообщений в RabbitMQ,
    используемых в системе мониторинга цен на различных маркетплейсах.
    """

    DMARKET_RESULT = "dmarket_result"
    DMARKET_MARKET_NAME = "dmarket_market_name"


class RedisKeys:
    """
    Ключи для хранения данных в Redis.

    Предоставляет стандартизированные префиксы ключей для хранения
    разных типов данных в Redis, облегчая поиск и организацию информации.
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

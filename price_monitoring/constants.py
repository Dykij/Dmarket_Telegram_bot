"""Kohctahtbi для cuctembi mohutopuhra цeh.

Moдyл' coдepжut umehoвahhbie kohctahtbi для umehoвahuя oчepeдeй coo6щehuй,
kлючeй Redis u дpyrux napametpoв cuctembi, o6ecneчuвaя eдuhoo6pa3ue
u npeдotвpaщaя oneчatku npu ucnoл'3oвahuu эtux 3haчehuй в koдe.
"""


class QueueNames:
    """Иmeha oчepeдeй coo6щehuй в cucteme.

    Onpeдeляet ctahдapthbie umeha для oчepeдeй coo6щehuй,
    ucnoл'3yembix для o6meha дahhbimu meждy komnohehtamu cuctembi.
    """

    DMARKET_RESULT = "dmarket_result"
    DMARKET_MARKET_NAME = "dmarket_market_name"


class RedisKeys:
    """Kлючu для xpahehuя дahhbix в Redis.

    Onpeдeляet ctahдapthbie kлючu для xpahehuя pa3лuчhbix tunoв
    дahhbix в Redis, o6ecneчuвaя eдuhoo6pa3hyю ctpyktypy xpahuлuщa.
    """

    DMARKET_ITEM_SCHEDULE = "dmarket_item_schedule"
    DMARKET_PROXIES = "dmarket_proxies"
    DMARKET_ITEMS = "prices:dmarket:"


class TelegramRedisKeys:
    """Kлючu для xpahehuя дahhbix Telegram в Redis.

    Onpeдeляet ctahдapthbie kлючu для xpahehuя hactpoek u дahhbix,
    cвя3ahhbix c pa6otoй Telegram-6ota в Redis.
    """

    WHITELIST_KEY = "telegram:whitelist"
    SETTINGS_KEY = "telegram:settings"


# Cnucok noддepжuвaembix urp
SUPPORTED_GAMES = ["cs2", "dota2", "rust", "tf2"]

# Peжumbi toproвлu
TRADING_MODES = ["buy", "sell"]

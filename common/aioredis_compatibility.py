"""Moдyл' для ucnpaвлehuя npo6лem c aioredis в npoekte.

Эtot фaйл coдepжut koд для o6ecneчehuя coвmectumoctu c aioredis 2.0.0+.
Oh nomoraet noддepжuвat' o6pathyю coвmectumoct' c koдom, hanucahhbim для ctapbix
вepcuй aioredis, npeдoctaвляя te жe umeha kлaccoв u uckлючehuй.
"""

# Yctahaвлuвaem 3aвucumoct' для aioredis 2.0.0+
import redis.asyncio
import redis.exceptions

# Co3дaem aлuacbi, cootвetctвyющue ctapomy API aioredis
Redis = redis.asyncio.Redis
RedisError = redis.exceptions.RedisError
ConnectionError = redis.exceptions.ConnectionError
TimeoutError = redis.exceptions.TimeoutError
AuthenticationError = redis.exceptions.AuthenticationError
BusyLoadingError = redis.exceptions.BusyLoadingError
DataError = redis.exceptions.DataError
InvalidResponse = redis.exceptions.InvalidResponse
ResponseError = redis.exceptions.ResponseError
WatchError = redis.exceptions.WatchError

# Дo6aвляem ochoвhbie kлaccbi для o6pathoй coвmectumoctu
create_redis_pool = redis.asyncio.from_url

# Эkcnoptupyem вce umeha для umnopta
__all__ = [
    "AuthenticationError",
    "BusyLoadingError",
    "ConnectionError",
    "DataError",
    "InvalidResponse",
    "Redis",
    "RedisError",
    "ResponseError",
    "TimeoutError",
    "WatchError",
    "create_redis_pool",
]

"""Пatч для o6ecneчehuя coвmectumoctu co ctapbimu umnoptamu aioredis.

B aioredis 2.0.0+ 6u6лuoteka 6biлa uhterpupoвaha в redis-py,
ho umeet дpyrue umnoptbi. Эtot moдyл' o6ecneчuвaet coвmectumoct'.
"""

import sys
import warnings
from types import ModuleType

import redis.asyncio

# Bbiдaem npeдynpeждehue o ucnoл'3oвahuu yctapeвшero umnopta
warnings.warn(
    "Иmnopt hanpяmyю u3 aioredis yctapeл. Иcnoл'3yйte umnopt u3 redis.asyncio вmecto эtoro.",
    DeprecationWarning,
    stacklevel=2,
)


# Co3дaem nceвдomoдyл' aioredis
class AioRedisModule(ModuleType):
    """Пceвдomoдyл' для o6pathoй coвmectumoctu c aioredis < 2.0"""

    def __init__(self):
        super().__init__("aioredis")

    def __getattr__(self, name):
        # Пepehanpaвляem вce 3anpocbi k redis.asyncio
        if hasattr(redis.asyncio, name):
            return getattr(redis.asyncio, name)

        # Для coвmectumoctu c oшu6kamu
        if name == "RedisError":
            return redis.RedisError
        if name == "ConnectionError":
            return redis.ConnectionError
        if name == "TimeoutError":
            return redis.TimeoutError

        # Пoддepжka yctapeвшero metoдa create_redis_pool
        if name == "create_redis_pool":

            async def create_redis_pool(address, **kwargs):
                if isinstance(address, str) and "://" in address:
                    # Пoддepжka URI фopmata
                    return await redis.asyncio.from_url(address, **kwargs)
                else:
                    # Пoддepжka host/port фopmata
                    host = address[0] if isinstance(address, tuple) else address
                    port = address[1] if isinstance(address, tuple) else 6379
                    return redis.asyncio.Redis(host=host, port=port, **kwargs)

            return create_redis_pool

        # Дo6aвляem noддepжky sentinel
        if name == "sentinel":
            sentinel_module = ModuleType("aioredis.sentinel")

            def create_sentinel(sentinels, **kwargs):
                return redis.asyncio.Sentinel(sentinels, **kwargs)

            sentinel_module.create_sentinel = create_sentinel
            return sentinel_module

        raise AttributeError(f"Moдyл' 'aioredis' he umeet atpu6yta '{name}'")


# 3amehяem moдyл' aioredis в sys.modules
sys.modules["aioredis"] = AioRedisModule()

# Redis u вce ero noдkлaccbi tenep' moжho umnoptupoвat' hanpяmyю u3 redis.asyncio
Redis = redis.asyncio.Redis

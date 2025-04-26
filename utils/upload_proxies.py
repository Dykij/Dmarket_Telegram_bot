import asyncio
import os

from common.aioredis_compatibility import Redis
from common.env_var import get_redis_db, get_redis_host, get_redis_port
from common.redis_connector import RedisConnector
from price_monitoring.storage.proxy import RedisProxyStorage
from proxy_http.proxy import Proxy

_DMARKET_PROXIES = "utils_mount/dmarket_proxies.txt"
_DMARKET_PROXIES_KEY = "dmarket_proxies"


async def fill_proxies(redis: Redis, file: str, key: str):
    storage = RedisProxyStorage(redis, key)
    proxies = await storage.get_all()
    for proxy in proxies:
        await storage.remove(proxy)

    added_count = 0
    with open(file, encoding="utf8") as f:
        while f.readable():
            line = f.readline().strip()
            if not line:
                break
            proxy = Proxy(proxy=line)
            await storage.add(proxy)
            added_count += 1
    print(f"Successfully filled {added_count} proxies")


async def main():
    redis_password = os.environ.get("REDIS_PASSWORD", "")
    redis = RedisConnector.create(
        host=get_redis_host(),
        port=str(get_redis_port()),
        db=str(get_redis_db()),
        password=redis_password,
    )

    # Load only proxies for DMarket
    await fill_proxies(redis, _DMARKET_PROXIES, _DMARKET_PROXIES_KEY)


if __name__ == "__main__":
    asyncio.run(main())

from price_monitoring.models.dmarket import DMarketItemPack
from price_monitoring.queues.abstract_market_name_queue import AbstractMarketNameWriter


class MarketNameExtractor:
    def __init__(self, market_name_queue: AbstractMarketNameWriter):
        self._market_name_queue = market_name_queue

    async def process(self, pack: DMarketItemPack) -> None:
        market_names = {item.market_hash_name for item in pack.items}
        market_name_pack = MarketNamePack(items=list(market_names))
        await self._market_name_queue.put(market_name_pack)
        logger.info(f"Updated market names for items {market_names}")

import logging

from common.rpc.queue_publisher import QueuePublisher
from common.rpc.queue_reader import QueueReader

from price_monitoring.models.dmarket import DMarketItemPack
from price_monitoring.queues.abstract_dmarket_item_queue import (
    AbstractDmarketItemReader,
    AbstractDmarketItemWriter,
)


class DmarketItemReader(AbstractDmarketItemReader):
    def __init__(self, reader: QueueReader):
        self._reader = reader

    async def get(self, timeout: int = 5) -> DMarketItemPack | None:
        data = await self._reader.read(timeout=timeout)
        if data:
            return DMarketItemPack.load_bytes(data)
        return None


class DmarketItemWriter(AbstractDmarketItemWriter):
    def __init__(self, publisher: QueuePublisher):
        self._publisher = publisher

    async def put(self, item: DMarketItemPack) -> None:
        data = item.dump_bytes()
        await self._publisher.publish(data)

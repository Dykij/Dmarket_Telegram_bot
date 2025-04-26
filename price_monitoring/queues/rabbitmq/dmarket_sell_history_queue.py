from common.rpc.queue_publisher import QueuePublisher
from common.rpc.queue_reader import QueueReader
from price_monitoring.models.dmarket import DmarketSellHistory
from price_monitoring.queues.abstract_dmarket_sell_history_queue import (
    AbstractDmarketSellHistoryReader, AbstractDmarketSellHistoryWriter)


class DmarketSellHistoryReader(AbstractDmarketSellHistoryReader):
    def __init__(self, reader: QueueReader):
        self._reader = reader

    async def get(self, timeout: int = 5) -> DmarketSellHistory | None:
        data = await self._reader.read(timeout=timeout)
        if data:
            return DmarketSellHistory.load_bytes(data)
        return None


class DmarketSellHistoryWriter(AbstractDmarketSellHistoryWriter):
    def __init__(self, publisher: QueuePublisher):
        self._publisher = publisher

    async def put(self, history: DmarketSellHistory) -> None:
        data = history.dump_bytes()
        await self._publisher.publish(data)

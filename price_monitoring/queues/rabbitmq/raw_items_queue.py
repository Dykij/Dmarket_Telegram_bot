# price_monitoring/queues/rabbitmq/raw_items_queue.py
import logging
from common.rabbitmq_connector import RabbitMQConnector
from price_monitoring.models.dmarket import DMarketItem

# Define a constant for the queue name
DMARKET_RAW_ITEMS_QUEUE_NAME = "dmarket_raw_items_queue"

class DMarketRawItemsQueuePublisher:
    """
    Публикует необработанные данные о предметах DMarket в очередь RabbitMQ.
    """
    def __init__(self, connector: RabbitMQConnector, queue_name: str = DMARKET_RAW_ITEMS_QUEUE_NAME):
        self._connector = connector
        self._queue_name = queue_name
        self._logger = logging.getLogger(__name__)
        self._channel = None # Channel will be acquired when needed

    async def _ensure_channel(self):
        """Получает канал RabbitMQ, если он еще не получен."""
        if self._channel is None or self._channel.is_closed:
            self._channel = await self._connector.get_channel()
            # Объявляем очередь при получении канала, чтобы убедиться, что она существует
            await self._channel.declare_queue(self._queue_name, durable=True)
            self._logger.info(f"RabbitMQ channel acquired and queue '{self._queue_name}' declared.")

    async def publish_item(self, item: DMarketItem):
        """
        Публикует один предмет DMarketItem в очередь.

        Args:
            item: Экземпляр DMarketItem для публикации.
        """
        try:
            await self._ensure_channel()
            message_body = item.dump_bytes() # Сериализуем в bytes
            await self._connector.publish(
                channel=self._channel,
                routing_key=self._queue_name,
                body=message_body
            )
            # self._logger.debug(f"Published item {item.item_id} to queue '{self._queue_name}'")
        except Exception as e:
            self._logger.error(f"Failed to publish item {item.item_id} to queue '{self._queue_name}': {e}")
            # Сбрасываем канал при ошибке, чтобы переподключиться при следующей попытке
            self._channel = None
            raise # Повторно вызываем исключение, чтобы вызывающий код знал об ошибке

    async def close(self):
        """Закрывает канал, если он открыт."""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
            self._logger.info("RabbitMQ channel closed.")

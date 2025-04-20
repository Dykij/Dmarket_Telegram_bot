from typing import Any, Optional, TypeVar

from .rpc.queue_factory import QueueFactory
from .rpc.queue_listener import QueueListener
from .rpc.queue_publisher import QueuePublisher
from .rpc.rabbitmq_client import RabbitMQClient

T = TypeVar("T")


class RabbitMQConnector:
    def __init__(
        self,
        host: str,
        port: str,
        user: str,
        password: str,
        virtual_host: str,
        connection_name: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.virtual_host = virtual_host
        self.connection_name = connection_name
        self.client = None

    async def connect(self):
        """Подключение к серверу RabbitMQ."""
        self.client = RabbitMQClient(
            host=self.host,
            port=int(self.port),
            login=self.user,
            password=self.password,
            connection_name=self.connection_name,
        )
        await self.client.connect()
        return self.client

    async def create_publisher(self, queue_class: type[T]) -> "QueuePublisher[T]":
        """Создает издателя для заданной очереди."""
        if not self.client:
            await self.connect()
        factory = QueueFactory(self.client)
        return await factory.create_publisher(queue_class)

    async def create_listener(
        self, queue_class: type[T], on_message_callback: Any
    ) -> QueueListener:
        """Создает слушателя для заданной очереди c обратным вызовом при получении сообщения."""
        if not self.client:
            await self.connect()
        factory = QueueFactory(self.client)
        return await factory.create_listener(queue_class, on_message_callback)

    async def close(self):
        """Закрывает соединение c RabbitMQ."""
        if self.client:
            await self.client.close()
            self.client = None

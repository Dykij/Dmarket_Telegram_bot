"""RabbitMQ Auto-Reconnect Module

This module provides a wrapper for RabbitMQ connections with automatic reconnection functionality.
It helps improve the robustness of RabbitMQ operations by handling connection failures gracefully.
"""

import asyncio
import logging
import ssl
from typing import Any, Callable, Optional, TypeVar, Union, cast

from aio_pika import Channel, Connection, Exchange, Message, Queue, connect_robust
from aio_pika.abc import AbstractConnection
from aio_pika.exceptions import AMQPConnectionError, AMQPError

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar("T")

# Maximum number of reconnection attempts
MAX_RECONNECT_ATTEMPTS = 5

# Delay between reconnection attempts (in seconds)
RECONNECT_DELAY = 1.0


class RabbitMQAutoReconnect:
    """Wrapper for RabbitMQ connections with automatic reconnection functionality.

    This class wraps a RabbitMQ connection and provides automatic reconnection
    if the connection is lost or an operation fails due to connection issues.
    """

    def __init__(
        self,
        rabbitmq_url: str,
        max_reconnect_attempts: int = MAX_RECONNECT_ATTEMPTS,
        reconnect_delay: float = RECONNECT_DELAY,
        ssl_context: Optional[ssl.SSLContext] = None,
    ):
        """Initialize the RabbitMQ auto-reconnect wrapper.

        Args:
            rabbitmq_url: RabbitMQ connection URL
            max_reconnect_attempts: Maximum number of reconnection attempts
            reconnect_delay: Delay between reconnection attempts (in seconds)
            ssl_context: SSL context for secure connections
        """
        self.rabbitmq_url = rabbitmq_url
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.ssl_context = ssl_context
        self._connection: Optional[Connection] = None
        self._channel: Optional[Channel] = None
        self._exchanges: dict[str, Exchange] = {}
        self._queues: dict[str, Queue] = {}
        self._connection_lock = asyncio.Lock()
        self._channel_lock = asyncio.Lock()

    async def get_connection(self) -> Connection:
        """Get the RabbitMQ connection, creating it if it doesn't exist.

        Returns:
            RabbitMQ connection object
        """
        if self._connection is None or self._connection.is_closed:
            async with self._connection_lock:
                if self._connection is None or self._connection.is_closed:
                    self._connection = await self._create_connection()

        return cast(Connection, self._connection)

    async def get_channel(self) -> Channel:
        """Get a RabbitMQ channel, creating it if it doesn't exist.

        Returns:
            RabbitMQ channel object
        """
        if self._channel is None or self._channel.is_closed:
            async with self._channel_lock:
                if self._channel is None or self._channel.is_closed:
                    connection = await self.get_connection()
                    self._channel = await connection.channel()

        return cast(Channel, self._channel)

    async def _create_connection(self) -> Connection:
        """Create a new RabbitMQ connection.

        Returns:
            RabbitMQ connection object
        """
        try:
            logger.debug(f"Creating RabbitMQ connection to {self.rabbitmq_url}")
            connection = await connect_robust(self.rabbitmq_url, ssl_context=self.ssl_context)
            logger.info(f"RabbitMQ connection established: {self.rabbitmq_url}")

            # Set up reconnection callback
            connection.reconnect_callbacks.add(self._on_reconnect)

            return connection
        except Exception as e:
            logger.error(f"Failed to create RabbitMQ connection: {e!s}")
            raise

    async def _on_reconnect(self, connection: AbstractConnection) -> None:
        """Callback triggered when the connection is reconnected.

        Args:
            connection: The reconnected connection object
        """
        logger.info(f"RabbitMQ connection re-established: {self.rabbitmq_url}")

        # Clear cached channel and re-create it
        self._channel = None

        # Reset exchanges and queues cache so they'll be re-created
        self._exchanges = {}
        self._queues = {}

    async def reconnect(self) -> Connection:
        """Attempt to reconnect to RabbitMQ.

        Returns:
            New RabbitMQ connection object
        """
        if self._connection is not None:
            try:
                await self._connection.close()
            except Exception as e:
                logger.warning(f"Error while closing connection: {e!s}")

            self._connection = None

        self._channel = None
        self._exchanges = {}
        self._queues = {}

        return await self.get_connection()

    async def get_exchange(
        self, name: str, exchange_type: str = "direct", durable: bool = True
    ) -> Exchange:
        """Get or create an exchange.

        Args:
            name: Name of the exchange
            exchange_type: Type of the exchange (direct, fanout, topic, headers)
            durable: Whether the exchange should survive server restarts

        Returns:
            Exchange object
        """
        if name not in self._exchanges:
            channel = await self.get_channel()
            exchange = await channel.declare_exchange(name, exchange_type, durable=durable)
            self._exchanges[name] = exchange

        return self._exchanges[name]

    async def get_queue(self, name: str, durable: bool = True, auto_delete: bool = False) -> Queue:
        """Get or create a queue.

        Args:
            name: Name of the queue
            durable: Whether the queue should survive server restarts
            auto_delete: Whether the queue should be deleted when no longer used

        Returns:
            Queue object
        """
        if name not in self._queues:
            channel = await self.get_channel()
            queue = await channel.declare_queue(name, durable=durable, auto_delete=auto_delete)
            self._queues[name] = queue

        return self._queues[name]

    async def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str) -> None:
        """Bind a queue to an exchange with a routing key.

        Args:
            queue_name: Name of the queue
            exchange_name: Name of the exchange
            routing_key: Routing key for binding
        """
        exchange = await self.get_exchange(exchange_name)
        queue = await self.get_queue(queue_name)
        await queue.bind(exchange, routing_key)

    async def publish(
        self,
        exchange_name: str,
        routing_key: str,
        message_body: Union[str, bytes, dict],
        content_type: str = "application/json",
        delivery_mode: int = 2,  # Persistent
    ) -> None:
        """Publish a message to an exchange.

        Args:
            exchange_name: Name of the exchange to publish to
            routing_key: Routing key for the message
            message_body: The message body to send
            content_type: Content type of the message
            delivery_mode: Delivery mode (1=non-persistent, 2=persistent)
        """
        await self.execute_with_retry(
            self._publish, exchange_name, routing_key, message_body, content_type, delivery_mode
        )

    async def _publish(
        self,
        exchange_name: str,
        routing_key: str,
        message_body: Union[str, bytes, dict],
        content_type: str,
        delivery_mode: int,
    ) -> None:
        """Internal method to publish a message with proper error handling."""
        import json

        exchange = await self.get_exchange(exchange_name)

        # Convert dict to JSON string if needed
        if isinstance(message_body, dict):
            message_body = json.dumps(message_body).encode("utf-8")
        elif isinstance(message_body, str):
            message_body = message_body.encode("utf-8")

        message = Message(
            body=message_body,
            content_type=content_type,
            delivery_mode=delivery_mode,
        )

        await exchange.publish(message, routing_key)

    async def consume(
        self,
        queue_name: str,
        callback: Callable,
        prefetch_count: int = 10,
    ) -> None:
        """Start consuming messages from a queue.

        Args:
            queue_name: Name of the queue to consume from
            callback: Async callback function to process messages
            prefetch_count: Number of messages to prefetch
        """
        await self.execute_with_retry(self._consume, queue_name, callback, prefetch_count)

    async def _consume(
        self,
        queue_name: str,
        callback: Callable,
        prefetch_count: int,
    ) -> None:
        """Internal method to consume messages with proper error handling."""
        channel = await self.get_channel()
        await channel.set_qos(prefetch_count=prefetch_count)

        queue = await self.get_queue(queue_name)
        await queue.consume(callback)

    async def execute_with_retry(self, operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a RabbitMQ operation with automatic retry on connection failure.

        Args:
            operation: RabbitMQ operation to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the RabbitMQ operation

        Raises:
            AMQPError: If all reconnection attempts fail
        """
        attempts = 0
        last_error = None

        while attempts < self.max_reconnect_attempts:
            try:
                return await operation(*args, **kwargs)
            except (AMQPConnectionError, ConnectionError, AMQPError) as e:
                attempts += 1
                last_error = e

                if attempts >= self.max_reconnect_attempts:
                    logger.error(
                        f"Failed to execute RabbitMQ operation {operation.__name__} "
                        f"after {attempts} attempts: {e!s}"
                    )
                    break

                logger.warning(
                    f"RabbitMQ operation {operation.__name__} failed: {e!s}. "
                    f"Reconnecting (attempt {attempts}/{self.max_reconnect_attempts})..."
                )

                # Exponential backoff
                wait_time = self.reconnect_delay * (2 ** (attempts - 1))
                await asyncio.sleep(wait_time)

                try:
                    await self.reconnect()
                except Exception as reconnect_error:
                    logger.error(f"Reconnection failed: {reconnect_error!s}")

        if last_error:
            raise last_error

        # This should never happen, but it's here for type checking
        raise AMQPError("Failed to execute RabbitMQ operation for unknown reason")

    async def close(self) -> None:
        """Close the RabbitMQ connection and channel."""
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()
            self._channel = None
            logger.info("RabbitMQ channel closed")

        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            logger.info("RabbitMQ connection closed")

    async def __aenter__(self) -> "RabbitMQAutoReconnect":
        """Enter the async context manager."""
        await self.get_connection()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager."""
        await self.close()

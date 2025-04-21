"""
RabbitMQ Connector Module

This module provides a high-level interface for connecting to RabbitMQ and performing
common operations such as publishing messages, creating publishers and listeners,
and managing connections and channels.

The RabbitMQConnector class serves as a facade for the underlying RabbitMQClient,
QueueFactory, QueuePublisher, and QueueListener classes, providing a simplified API
for interacting with RabbitMQ.

Features:
- Connection pooling with configurable channel pool size
- Retry logic for connection failures
- Support for RabbitMQ clusters
- SSL connection support
- Heartbeat and connection timeout configuration
- Message acknowledgment and persistence
- Dead letter exchanges
- Publisher confirms
- Comprehensive error handling and logging
"""

import logging
import ssl
from datetime import timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

from aio_pika import Channel, DeliveryMode, Message
from aio_pika.exceptions import AMQPConnectionError, AMQPError

from .rpc.queue_factory import QueueFactory
from .rpc.queue_listener import QueueListener
from .rpc.queue_publisher import QueuePublisher
from .rpc.queue_reader import QueueReader
from .rpc.rabbitmq_client import RabbitMQClient

# Configure logger
logger = logging.getLogger(__name__)

# Generic type variable for queue classes
T = TypeVar("T")


class RabbitMQConnector:
    """
    A high-level connector for RabbitMQ operations.

    This class provides methods for connecting to RabbitMQ, publishing messages,
    creating publishers and listeners, and managing connections and channels.

    Attributes:
        host: The RabbitMQ server hostname or IP address (or comma-separated list for cluster)
        port: The RabbitMQ server port
        user: The username for authentication
        password: The password for authentication
        virtual_host: The RabbitMQ virtual host
        connection_name: Optional name for the connection (useful for debugging)
        ssl_enabled: Whether to use SSL for the connection
        ssl_context: Optional SSL context for secure connections
        heartbeat: Heartbeat interval in seconds
        connection_timeout: Connection timeout in seconds
        retry_attempts: Number of connection retry attempts
        retry_delay: Delay between retry attempts in seconds
        channel_pool_size: Maximum number of channels to keep in the pool
        client: The underlying RabbitMQClient instance (None until connect() is called)
    """

    def __init__(
        self,
        host: str,
        port: str,
        user: str,
        password: str,
        virtual_host: str,
        connection_name: Optional[str] = None,
        ssl_enabled: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None,
        heartbeat: int = 60,
        connection_timeout: float = 10.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        channel_pool_size: int = 10,
    ):
        """
        Initialize a new RabbitMQConnector.

        Args:
            host: The RabbitMQ server hostname or IP address (or comma-separated list for cluster)
            port: The RabbitMQ server port (as a string)
            user: The username for authentication
            password: The password for authentication
            virtual_host: The RabbitMQ virtual host
            connection_name: Optional name for the connection (useful for debugging)
            ssl_enabled: Whether to use SSL for the connection
            ssl_context: Optional SSL context for secure connections
            heartbeat: Heartbeat interval in seconds
            connection_timeout: Connection timeout in seconds
            retry_attempts: Number of connection retry attempts
            retry_delay: Delay between retry attempts in seconds
            channel_pool_size: Maximum number of channels to keep in the pool
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.virtual_host = virtual_host
        self.connection_name = connection_name
        self.ssl_enabled = ssl_enabled
        self.ssl_context = ssl_context
        self.heartbeat = heartbeat
        self.connection_timeout = connection_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.channel_pool_size = channel_pool_size
        self.client = None

    async def connect(self) -> RabbitMQClient:
        """
        Connect to the RabbitMQ server.

        This method creates a new RabbitMQClient instance and establishes
        a connection to the RabbitMQ server using the connection parameters
        provided during initialization.

        Returns:
            The connected RabbitMQClient instance

        Raises:
            AMQPConnectionError: If the connection to RabbitMQ fails after all retry attempts
        """
        try:
            logger.info(f"Connecting to RabbitMQ at {self.host}:{self.port}")
            self.client = RabbitMQClient(
                host=self.host,
                port=int(self.port),
                login=self.user,
                password=self.password,
                connection_name=self.connection_name,
                virtual_host=self.virtual_host,
                ssl_context=self.ssl_context if self.ssl_enabled else None,
                heartbeat=self.heartbeat,
                connection_timeout=self.connection_timeout,
                retry_attempts=self.retry_attempts,
                retry_delay=self.retry_delay,
                channel_pool_size=self.channel_pool_size,
            )
            await self.client.connect()
            logger.info("Successfully connected to RabbitMQ")
            return self.client
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    async def get_channel(self) -> Channel:
        """
        Get a RabbitMQ channel.

        This method returns a channel from the current connection.
        If no connection exists, it first establishes a connection.

        Returns:
            A new RabbitMQ channel

        Raises:
            AMQPConnectionError: If the connection to RabbitMQ fails
        """
        if not self.client:
            await self.connect()

        try:
            channel = await self.client.create_channel()
            logger.debug("Created new RabbitMQ channel")
            return channel
        except AMQPError as e:
            logger.error(f"Failed to create RabbitMQ channel: {str(e)}")
            raise

    async def return_channel(self, channel: Channel) -> None:
        """
        Return a channel to the pool for reuse.

        This method adds a channel back to the pool if it's still open
        and the pool is not full. Otherwise, it closes the channel.

        Args:
            channel: The channel to return to the pool
        """
        if not self.client:
            await self.close_channel(channel)
            return

        await self.client.return_channel(channel)

    async def close_channel(self, channel: Channel) -> None:
        """
        Close a RabbitMQ channel.

        This method closes the specified channel if it's open.

        Args:
            channel: The channel to close
        """
        if not self.client:
            return

        await self.client.close_channel(channel)

    async def publish(
        self, 
        channel: Channel, 
        routing_key: str, 
        body: bytes, 
        persistent: bool = True,
        content_type: str = "application/octet-stream",
        content_encoding: str = "utf-8",
        priority: Optional[int] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        expiration: Optional[Union[int, float, timedelta]] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        Publish a message to a RabbitMQ queue.

        This method creates a message from the provided body and additional parameters,
        then publishes it to the default exchange with the specified routing key.

        Args:
            channel: The RabbitMQ channel to use for publishing
            routing_key: The routing key (usually the queue name)
            body: The message body as bytes
            persistent: Whether the message should be persisted to disk
            content_type: MIME content type
            content_encoding: MIME content encoding
            priority: Message priority, 0-9
            correlation_id: Correlation ID for RPC
            reply_to: Queue name for RPC response
            expiration: Message expiration in seconds or as timedelta
            message_id: Application-specific message ID
            timestamp: Message timestamp
            headers: Message headers
            **kwargs: Additional parameters for the Message constructor

        Raises:
            AMQPError: If the message cannot be published
        """
        try:
            # Set delivery mode based on persistence
            delivery_mode = DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT

            # Convert timedelta to milliseconds if provided
            if isinstance(expiration, timedelta):
                expiration = int(expiration.total_seconds() * 1000)
            elif isinstance(expiration, (int, float)):
                expiration = int(expiration * 1000)

            # Create the message
            message = Message(
                body=body,
                content_type=content_type,
                content_encoding=content_encoding,
                priority=priority,
                correlation_id=correlation_id,
                reply_to=reply_to,
                expiration=expiration,
                message_id=message_id,
                timestamp=timestamp,
                headers=headers,
                delivery_mode=delivery_mode,
                **kwargs
            )

            # Publish the message
            logger.debug(f"Publishing message to {routing_key}")
            await channel.default_exchange.publish(message, routing_key=routing_key)
            logger.debug(f"Message published to {routing_key}")
        except AMQPError as e:
            logger.error(f"Failed to publish message to {routing_key}: {str(e)}")
            raise

    async def create_queue(
        self,
        channel: Channel,
        queue_name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None,
        message_ttl: Optional[Union[int, timedelta]] = None,
        dead_letter_exchange: Optional[str] = None,
        dead_letter_routing_key: Optional[str] = None,
        max_length: Optional[int] = None,
        max_priority: Optional[int] = None,
    ) -> None:
        """
        Create a queue with the specified parameters.

        This method creates a queue with the specified name and parameters.
        If the queue already exists, it verifies that the existing queue
        has the same parameters.

        Args:
            channel: The RabbitMQ channel to use
            queue_name: The name of the queue to create
            durable: Whether the queue should survive broker restarts
            exclusive: Whether the queue should be used by only one connection
            auto_delete: Whether the queue should be deleted when no longer used
            arguments: Additional arguments for the queue
            message_ttl: Time-to-live for messages in the queue (in seconds or as timedelta)
            dead_letter_exchange: Exchange to which dead letters will be published
            dead_letter_routing_key: Routing key for dead letters
            max_length: Maximum number of messages in the queue
            max_priority: Maximum priority for the queue (enables priority queue)

        Raises:
            AMQPError: If the queue cannot be created
        """
        try:
            # Prepare queue arguments
            if arguments is None:
                arguments = {}

            # Add message TTL if specified
            if message_ttl is not None:
                if isinstance(message_ttl, timedelta):
                    arguments["x-message-ttl"] = int(message_ttl.total_seconds() * 1000)
                else:
                    arguments["x-message-ttl"] = int(message_ttl * 1000)

            # Add dead letter exchange if specified
            if dead_letter_exchange is not None:
                arguments["x-dead-letter-exchange"] = dead_letter_exchange

            # Add dead letter routing key if specified
            if dead_letter_routing_key is not None:
                arguments["x-dead-letter-routing-key"] = dead_letter_routing_key

            # Add max length if specified
            if max_length is not None:
                arguments["x-max-length"] = max_length

            # Add max priority if specified
            if max_priority is not None:
                arguments["x-max-priority"] = max_priority

            # Create the queue
            logger.debug(f"Creating queue {queue_name}")
            await channel.declare_queue(
                name=queue_name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete,
                arguments=arguments,
            )
            logger.debug(f"Queue {queue_name} created")
        except AMQPError as e:
            logger.error(f"Failed to create queue {queue_name}: {str(e)}")
            raise

    async def create_publisher(
        self, 
        queue_class: type[T],
        passive: bool = False,
        message_ttl: Optional[timedelta] = None,
    ) -> "QueuePublisher[T]":
        """
        Create a publisher for the specified queue class.

        This method creates a QueuePublisher instance for the specified queue class
        using the QueueFactory. If no connection exists, it first establishes a connection.

        Args:
            queue_class: The queue class to create a publisher for
            passive: Whether to use passive queue declaration
            message_ttl: Time-to-live for messages in the queue

        Returns:
            A QueuePublisher instance for the specified queue class

        Raises:
            AMQPConnectionError: If the connection to RabbitMQ fails
        """
        if not self.client:
            await self.connect()

        try:
            factory = QueueFactory()
            publisher = await factory.connect_publisher(
                name=queue_class.queue_name,
                client=self.client,
                passive=passive,
                message_ttl=message_ttl,
            )
            logger.debug(f"Created publisher for queue {queue_class.queue_name}")
            return publisher
        except AMQPError as e:
            logger.error(f"Failed to create publisher for queue {queue_class.queue_name}: {str(e)}")
            raise

    async def create_listener(
        self, 
        queue_class: type[T], 
        on_message_callback: Callable,
        passive: bool = False,
        message_ttl: Optional[timedelta] = None,
    ) -> QueueListener:
        """
        Create a listener for the specified queue class with a callback for received messages.

        This method creates a QueueListener instance for the specified queue class
        using the QueueFactory. The listener will call the provided callback function
        when a message is received. If no connection exists, it first establishes a connection.

        Args:
            queue_class: The queue class to create a listener for
            on_message_callback: The callback function to call when a message is received
            passive: Whether to use passive queue declaration
            message_ttl: Time-to-live for messages in the queue

        Returns:
            A QueueListener instance for the specified queue class

        Raises:
            AMQPConnectionError: If the connection to RabbitMQ fails
        """
        if not self.client:
            await self.connect()

        try:
            factory = QueueFactory()
            listener = await factory.connect_listener(
                name=queue_class.queue_name,
                client=self.client,
                on_msg=on_message_callback,
                passive=passive,
                message_ttl=message_ttl,
            )
            logger.debug(f"Created listener for queue {queue_class.queue_name}")
            return listener
        except AMQPError as e:
            logger.error(f"Failed to create listener for queue {queue_class.queue_name}: {str(e)}")
            raise

    async def create_reader(
        self, 
        queue_class: type[T],
        passive: bool = False,
        message_ttl: Optional[timedelta] = None,
    ) -> QueueReader:
        """
        Create a reader for the specified queue class.

        This method creates a QueueReader instance for the specified queue class
        using the QueueFactory. If no connection exists, it first establishes a connection.

        Args:
            queue_class: The queue class to create a reader for
            passive: Whether to use passive queue declaration
            message_ttl: Time-to-live for messages in the queue

        Returns:
            A QueueReader instance for the specified queue class

        Raises:
            AMQPConnectionError: If the connection to RabbitMQ fails
        """
        if not self.client:
            await self.connect()

        try:
            factory = QueueFactory()
            reader = await factory.connect_reader(
                name=queue_class.queue_name,
                client=self.client,
                passive=passive,
                message_ttl=message_ttl,
            )
            logger.debug(f"Created reader for queue {queue_class.queue_name}")
            return reader
        except AMQPError as e:
            logger.error(f"Failed to create reader for queue {queue_class.queue_name}: {str(e)}")
            raise

    async def close(self) -> None:
        """
        Close the connection to the RabbitMQ server.

        This method closes the underlying RabbitMQClient connection
        and sets the client attribute to None. If no connection exists,
        this method does nothing.
        """
        if self.client:
            try:
                logger.info("Closing RabbitMQ connection")
                await self.client.close()
                logger.info("RabbitMQ connection closed")
            except AMQPError as e:
                logger.warning(f"Error closing RabbitMQ connection: {str(e)}")
            finally:
                self.client = None

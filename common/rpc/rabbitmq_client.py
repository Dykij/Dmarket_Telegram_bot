"""
RabbitMQ Client Module

This module provides a client for connecting to RabbitMQ and performing
common operations such as creating channels and managing connections.

Features:
- Connection pooling with configurable channel pool size
- Retry logic for connection failures
- Support for RabbitMQ clusters
- SSL connection support
- Heartbeat and connection timeout configuration
- Comprehensive error handling and logging
"""

import asyncio
import logging
import ssl
from typing import Dict, List, Optional, Union

from aio_pika import Channel, Connection, connect_robust
from aio_pika.abc import AbstractChannel, AbstractConnection
from aio_pika.exceptions import AMQPConnectionError, AMQPError

# Configure logger
logger = logging.getLogger(__name__)


class RabbitMQClient:
    """
    A client for connecting to RabbitMQ and performing common operations.

    This class provides methods for connecting to RabbitMQ, creating channels,
    and managing connections. It uses aio_pika for asynchronous operations.

    Attributes:
        host: The RabbitMQ server hostname or IP address (or comma-separated list for cluster)
        port: The RabbitMQ server port
        login: The username for authentication
        password: The password for authentication
        connection_name: Optional name for the connection (useful for debugging)
        virtual_host: The RabbitMQ virtual host
        ssl_context: Optional SSL context for secure connections
        heartbeat: Heartbeat interval in seconds
        connection_timeout: Connection timeout in seconds
        retry_attempts: Number of connection retry attempts
        retry_delay: Delay between retry attempts in seconds
        channel_pool_size: Maximum number of channels to keep in the pool
        connection: The underlying RabbitMQ connection (None until connect() is called)
        channel_pool: A pool of reusable channels
    """

    def __init__(
        self,
        host: str,
        port: int,
        login: str,
        password: str,
        connection_name: Optional[str] = None,
        virtual_host: str = "/",
        ssl_context: Optional[ssl.SSLContext] = None,
        heartbeat: int = 60,
        connection_timeout: float = 10.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        channel_pool_size: int = 10,
    ):
        """
        Initialize a new RabbitMQClient.

        Args:
            host: The RabbitMQ server hostname or IP address (or comma-separated list for cluster)
            port: The RabbitMQ server port
            login: The username for authentication
            password: The password for authentication
            connection_name: Optional name for the connection (useful for debugging)
            virtual_host: The RabbitMQ virtual host
            ssl_context: Optional SSL context for secure connections
            heartbeat: Heartbeat interval in seconds
            connection_timeout: Connection timeout in seconds
            retry_attempts: Number of connection retry attempts
            retry_delay: Delay between retry attempts in seconds
            channel_pool_size: Maximum number of channels to keep in the pool
        """
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.connection_name = connection_name
        self.virtual_host = virtual_host
        self.ssl_context = ssl_context
        self.heartbeat = heartbeat
        self.connection_timeout = connection_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.channel_pool_size = channel_pool_size
        self.connection: Optional[Connection] = None
        self.channel_pool: List[Channel] = []

    async def connect(self) -> "RabbitMQClient":
        """
        Connect to the RabbitMQ server.

        This method establishes a connection to the RabbitMQ server using the
        connection parameters provided during initialization. It will retry
        the connection if it fails, up to the configured number of retry attempts.

        Returns:
            The RabbitMQClient instance (self) for method chaining

        Raises:
            AMQPConnectionError: If the connection to RabbitMQ fails after all retry attempts
        """
        # If we already have a connection, return it
        if self.connection and not self.connection.is_closed:
            return self

        # Parse hosts for cluster support
        hosts = [h.strip() for h in self.host.split(",")]

        # Try to connect to each host in the cluster
        for attempt in range(self.retry_attempts):
            for host in hosts:
                try:
                    logger.info(f"Connecting to RabbitMQ at {host}:{self.port} (attempt {attempt + 1}/{self.retry_attempts})")

                    # Build the connection URL
                    connection_url = f"amqp://{self.login}:{self.password}@{host}:{self.port}/{self.virtual_host}"

                    # Connect to RabbitMQ
                    self.connection = await connect_robust(
                        connection_url,
                        client_properties={
                            "connection_name": self.connection_name or "rabbitmq_client"
                        },
                        ssl=self.ssl_context,
                        heartbeat=self.heartbeat,
                        timeout=self.connection_timeout,
                    )

                    # Set up connection close callback
                    self.connection.add_close_callback(self._on_connection_closed)

                    logger.info(f"Successfully connected to RabbitMQ at {host}:{self.port}")
                    return self

                except AMQPConnectionError as e:
                    logger.warning(f"Failed to connect to RabbitMQ at {host}:{self.port}: {str(e)}")
                    continue

            # If we've tried all hosts and none worked, wait before retrying
            if attempt < self.retry_attempts - 1:
                logger.warning(f"Failed to connect to any RabbitMQ host, retrying in {self.retry_delay} seconds")
                await asyncio.sleep(self.retry_delay)

        # If we've exhausted all retry attempts, raise an error
        error_msg = f"Failed to connect to RabbitMQ after {self.retry_attempts} attempts"
        logger.error(error_msg)
        raise AMQPConnectionError(error_msg)

    def _on_connection_closed(self, connection: AbstractConnection, exception: Optional[Exception] = None) -> None:
        """
        Handle connection closed events.

        This callback is called when the connection to RabbitMQ is closed,
        either by the client or due to an error.

        Args:
            connection: The connection that was closed
            exception: The exception that caused the connection to close, if any
        """
        if exception:
            logger.warning(f"RabbitMQ connection closed unexpectedly: {str(exception)}")
        else:
            logger.info("RabbitMQ connection closed")

        # Clear the channel pool
        self.channel_pool = []

    async def create_channel(self) -> Channel:
        """
        Create a new RabbitMQ channel.

        This method creates a new channel on the current connection.
        If no connection exists, it first establishes a connection.
        It attempts to reuse channels from the pool if available.

        Returns:
            A new RabbitMQ channel

        Raises:
            AMQPConnectionError: If the connection to RabbitMQ fails
        """
        # Ensure we have a connection
        if not self.connection or self.connection.is_closed:
            await self.connect()

        # Try to get a channel from the pool
        if self.channel_pool:
            channel = self.channel_pool.pop()
            if not channel.is_closed:
                return channel

        # Create a new channel
        try:
            logger.debug("Creating new RabbitMQ channel")
            channel = await self.connection.channel()

            # Set up channel close callback
            channel.add_close_callback(self._on_channel_closed)

            return channel
        except AMQPError as e:
            logger.error(f"Failed to create RabbitMQ channel: {str(e)}")
            raise

    def _on_channel_closed(self, channel: AbstractChannel, exception: Optional[Exception] = None) -> None:
        """
        Handle channel closed events.

        This callback is called when a channel is closed,
        either by the client or due to an error.

        Args:
            channel: The channel that was closed
            exception: The exception that caused the channel to close, if any
        """
        if exception:
            logger.warning(f"RabbitMQ channel closed unexpectedly: {str(exception)}")
        else:
            logger.debug("RabbitMQ channel closed")

    async def return_channel(self, channel: Channel) -> None:
        """
        Return a channel to the pool for reuse.

        This method adds a channel back to the pool if it's still open
        and the pool is not full. Otherwise, it closes the channel.

        Args:
            channel: The channel to return to the pool
        """
        if not channel.is_closed and len(self.channel_pool) < self.channel_pool_size:
            self.channel_pool.append(channel)
        else:
            await self.close_channel(channel)

    async def close_channel(self, channel: Channel) -> None:
        """
        Close a RabbitMQ channel.

        This method closes the specified channel if it's open.

        Args:
            channel: The channel to close
        """
        if not channel.is_closed:
            try:
                await channel.close()
                logger.debug("RabbitMQ channel closed")
            except AMQPError as e:
                logger.warning(f"Error closing RabbitMQ channel: {str(e)}")

    async def close(self) -> None:
        """
        Close the connection to the RabbitMQ server.

        This method closes all channels in the pool and then closes
        the underlying RabbitMQ connection. If no connection exists,
        this method does nothing.
        """
        # Close all channels in the pool
        for channel in self.channel_pool:
            await self.close_channel(channel)
        self.channel_pool = []

        # Close the connection
        if self.connection and not self.connection.is_closed:
            try:
                logger.info("Closing RabbitMQ connection")
                await self.connection.close()
                logger.info("RabbitMQ connection closed successfully")
            except AMQPError as e:
                logger.warning(f"Error closing RabbitMQ connection: {str(e)}")
            finally:
                self.connection = None

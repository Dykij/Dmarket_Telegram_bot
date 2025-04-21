"""
Redis Connector Module

This module provides a high-level interface for connecting to Redis and performing
common operations. It supports both asynchronous and synchronous Redis clients.

The RedisConnector class manages asynchronous connections to Redis using aioredis,
while the static create method provides a way to create synchronous Redis clients
using the redis package.

Features:
- Connection pooling with configurable pool size
- Retry logic for connection failures
- Support for Redis Sentinel for high availability
- Support for Redis Cluster for scalability
- SSL connection support
- Comprehensive error handling and logging
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import time

import aioredis
from aioredis import Redis as AsyncRedis
import redis  # Synchronous Redis client
from redis.exceptions import ConnectionError, RedisError, TimeoutError
from redis.sentinel import Sentinel

# Configure logger
logger = logging.getLogger(__name__)


class RedisConnector:
    """
    A high-level connector for Redis operations.

    This class provides methods for connecting to Redis, getting clients,
    and managing connections. It uses aioredis for asynchronous operations.

    Attributes:
        host: The Redis server hostname or IP address (or comma-separated list for cluster)
        port: The Redis server port
        db: The Redis database number
        password: Optional password for authentication
        client: The underlying Redis client instance (None until get_client() is called)
        max_connections: Maximum number of connections in the pool
        min_connections: Minimum number of connections in the pool
        retry_attempts: Number of connection retry attempts
        retry_delay: Delay between retry attempts in seconds
        sentinel_master: Name of the master node when using Redis Sentinel
        sentinel_nodes: List of sentinel nodes when using Redis Sentinel
        cluster_mode: Whether to use Redis Cluster mode
        ssl: Whether to use SSL for the connection
        ssl_cert_reqs: SSL certificate requirements ('none', 'optional', or 'required')
        ssl_ca_certs: Path to CA certificates file
        ssl_certfile: Path to client certificate file
        ssl_keyfile: Path to client key file
    """

    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        password: Optional[str] = None,
        max_connections: int = 10,
        min_connections: int = 1,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        sentinel_master: Optional[str] = None,
        sentinel_nodes: Optional[List[Tuple[str, int]]] = None,
        cluster_mode: bool = False,
        ssl: bool = False,
        ssl_cert_reqs: str = "required",
        ssl_ca_certs: Optional[str] = None,
        ssl_certfile: Optional[str] = None,
        ssl_keyfile: Optional[str] = None,
    ):
        """
        Initialize a new RedisConnector.

        Args:
            host: The Redis server hostname or IP address (or comma-separated list for cluster)
            port: The Redis server port
            db: The Redis database number
            password: Optional password for authentication
            max_connections: Maximum number of connections in the pool
            min_connections: Minimum number of connections in the pool
            retry_attempts: Number of connection retry attempts
            retry_delay: Delay between retry attempts in seconds
            sentinel_master: Name of the master node when using Redis Sentinel
            sentinel_nodes: List of sentinel nodes when using Redis Sentinel
            cluster_mode: Whether to use Redis Cluster mode
            ssl: Whether to use SSL for the connection
            ssl_cert_reqs: SSL certificate requirements ('none', 'optional', or 'required')
            ssl_ca_certs: Path to CA certificates file
            ssl_certfile: Path to client certificate file
            ssl_keyfile: Path to client key file
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.sentinel_master = sentinel_master
        self.sentinel_nodes = sentinel_nodes
        self.cluster_mode = cluster_mode
        self.ssl = ssl
        self.ssl_cert_reqs = ssl_cert_reqs
        self.ssl_ca_certs = ssl_ca_certs
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self.client: Optional[AsyncRedis] = None

    async def get_client(self) -> AsyncRedis:
        """
        Get a Redis client, creating it if necessary.

        This method returns the existing Redis client if one exists,
        or creates a new one if none exists yet. The client is stored
        in the instance for reuse in future calls.

        Returns:
            An asynchronous Redis client for interacting with the database

        Raises:
            ConnectionError: If the connection to Redis fails after all retry attempts
        """
        if self.client is None:
            for attempt in range(self.retry_attempts):
                try:
                    if self.sentinel_master and self.sentinel_nodes:
                        # Use Redis Sentinel for high availability
                        logger.info(f"Connecting to Redis Sentinel master '{self.sentinel_master}'")
                        # Create a connection URL for Sentinel
                        sentinel_urls = [
                            f"redis://{node[0]}:{node[1]}" for node in self.sentinel_nodes
                        ]
                        self.client = await aioredis.create_redis_pool(
                            sentinel_urls,
                            db=self.db,
                            password=self.password,
                            maxsize=self.max_connections,
                            minsize=self.min_connections,
                            sentinel=True,
                            sentinel_master=self.sentinel_master,
                            ssl=self.ssl,
                            ssl_cert_reqs=self.ssl_cert_reqs,
                            ssl_ca_certs=self.ssl_ca_certs,
                            ssl_certfile=self.ssl_certfile,
                            ssl_keyfile=self.ssl_keyfile,
                        )
                    elif self.cluster_mode:
                        # Use Redis Cluster mode for scalability
                        logger.info("Connecting to Redis Cluster")
                        # Parse comma-separated hosts into a list of addresses
                        cluster_nodes = [
                            {"host": h.strip(), "port": self.port}
                            for h in self.host.split(",")
                        ]
                        self.client = await aioredis.create_redis_pool(
                            [f"redis://{node['host']}:{node['port']}" for node in cluster_nodes],
                            db=self.db,
                            password=self.password,
                            maxsize=self.max_connections,
                            minsize=self.min_connections,
                            ssl=self.ssl,
                            ssl_cert_reqs=self.ssl_cert_reqs,
                            ssl_ca_certs=self.ssl_ca_certs,
                            ssl_certfile=self.ssl_certfile,
                            ssl_keyfile=self.ssl_keyfile,
                        )
                    else:
                        # Standard Redis connection
                        logger.info(f"Connecting to Redis at {self.host}:{self.port}")
                        self.client = await aioredis.create_redis_pool(
                            f"redis://{self.host}:{self.port}",
                            db=self.db,
                            password=self.password,
                            maxsize=self.max_connections,
                            minsize=self.min_connections,
                            ssl=self.ssl,
                            ssl_cert_reqs=self.ssl_cert_reqs,
                            ssl_ca_certs=self.ssl_ca_certs,
                            ssl_certfile=self.ssl_certfile,
                            ssl_keyfile=self.ssl_keyfile,
                        )
                    logger.info("Successfully connected to Redis")
                    break
                except (ConnectionError, OSError, asyncio.TimeoutError) as e:
                    if attempt < self.retry_attempts - 1:
                        logger.warning(
                            f"Failed to connect to Redis (attempt {attempt + 1}/{self.retry_attempts}): {str(e)}"
                        )
                        await asyncio.sleep(self.retry_delay)
                    else:
                        logger.error(f"Failed to connect to Redis after {self.retry_attempts} attempts: {str(e)}")
                        raise ConnectionError(f"Failed to connect to Redis: {str(e)}")
        return self.client

    async def close(self) -> None:
        """
        Close the connection to the Redis server.

        This method closes the underlying Redis client connection
        and sets the client attribute to None. If no connection exists,
        this method does nothing.
        """
        if self.client:
            logger.info("Closing Redis connection")
            try:
                # Close the connection and wait for it to fully close
                self.client.close()
                await self.client.wait_closed()
                logger.info("Redis connection closed successfully")
            except Exception as e:
                logger.warning(f"Error while closing Redis connection: {str(e)}")
            finally:
                self.client = None

    async def execute_with_retry(self, command: str, *args, **kwargs) -> Any:
        """
        Execute a Redis command with retry logic.

        This method attempts to execute the specified Redis command,
        retrying if a connection error occurs.

        Args:
            command: The Redis command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
            The result of the Redis command

        Raises:
            RedisError: If the command fails after all retry attempts
        """
        client = await self.get_client()
        for attempt in range(self.retry_attempts):
            try:
                method = getattr(client, command)
                return await method(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                if attempt < self.retry_attempts - 1:
                    logger.warning(
                        f"Redis command '{command}' failed (attempt {attempt + 1}/{self.retry_attempts}): {str(e)}"
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Redis command '{command}' failed after {self.retry_attempts} attempts: {str(e)}")
                    raise

    @staticmethod
    def create(
        host: str,
        port: str,
        db: str,
        password: Optional[str] = None,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        max_connections: int = 10,
        sentinel_master: Optional[str] = None,
        sentinel_nodes: Optional[List[Tuple[str, int]]] = None,
        cluster_mode: bool = False,
        ssl: bool = False,
        ssl_cert_reqs: str = "required",
        ssl_ca_certs: Optional[str] = None,
        ssl_certfile: Optional[str] = None,
        ssl_keyfile: Optional[str] = None,
    ) -> Union[redis.Redis, redis.sentinel.SentinelConnectionPool, redis.cluster.RedisCluster]:
        """
        Create a synchronous Redis client.

        This static method creates a new synchronous Redis client using the redis package.
        It's useful for operations that don't need to be asynchronous or for compatibility
        with code that expects a synchronous Redis client.

        Args:
            host: The Redis server hostname or IP address (or comma-separated list for cluster)
            port: The Redis server port (as a string)
            db: The Redis database number (as a string)
            password: Optional password for authentication
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            max_connections: Maximum number of connections in the pool
            sentinel_master: Name of the master node when using Redis Sentinel
            sentinel_nodes: List of sentinel nodes when using Redis Sentinel
            cluster_mode: Whether to use Redis Cluster mode
            ssl: Whether to use SSL for the connection
            ssl_cert_reqs: SSL certificate requirements ('none', 'optional', or 'required')
            ssl_ca_certs: Path to CA certificates file
            ssl_certfile: Path to client certificate file
            ssl_keyfile: Path to client key file

        Returns:
            A synchronous Redis client

        Raises:
            ConnectionError: If the connection to Redis fails
        """
        # Convert port and db from strings to integers
        port_int = int(port)
        db_int = int(db)

        # Common connection parameters
        connection_kwargs = {
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            "retry_on_timeout": retry_on_timeout,
            "decode_responses": False,  # Keep the default behavior
        }

        # SSL parameters if SSL is enabled
        if ssl:
            connection_kwargs.update({
                "ssl": True,
                "ssl_cert_reqs": ssl_cert_reqs,
                "ssl_ca_certs": ssl_ca_certs,
                "ssl_certfile": ssl_certfile,
                "ssl_keyfile": ssl_keyfile,
            })

        # Add password if provided
        if password:
            connection_kwargs["password"] = password

        try:
            if sentinel_master and sentinel_nodes:
                # Use Redis Sentinel for high availability
                logger.info(f"Creating synchronous Redis Sentinel client for master '{sentinel_master}'")
                sentinel = Sentinel(
                    sentinel_nodes,
                    socket_timeout=socket_timeout,
                    password=password,
                    ssl=ssl,
                    ssl_cert_reqs=ssl_cert_reqs,
                    ssl_ca_certs=ssl_ca_certs,
                    ssl_certfile=ssl_certfile,
                    ssl_keyfile=ssl_keyfile,
                )
                return sentinel.master_for(
                    sentinel_master,
                    socket_timeout=socket_timeout,
                    db=db_int,
                    **connection_kwargs
                )
            elif cluster_mode:
                # Use Redis Cluster mode for scalability
                logger.info("Creating synchronous Redis Cluster client")
                # Parse comma-separated hosts into a list of addresses
                cluster_nodes = [
                    {"host": h.strip(), "port": port_int}
                    for h in host.split(",")
                ]
                return redis.cluster.RedisCluster(
                    startup_nodes=cluster_nodes,
                    decode_responses=False,
                    **connection_kwargs
                )
            else:
                # Standard Redis connection
                logger.info(f"Creating synchronous Redis client for {host}:{port_int}")
                connection_pool = redis.ConnectionPool(
                    host=host,
                    port=port_int,
                    db=db_int,
                    max_connections=max_connections,
                    **connection_kwargs
                )
                return redis.Redis(connection_pool=connection_pool)
        except (ConnectionError, redis.RedisError) as e:
            logger.error(f"Failed to create synchronous Redis client: {str(e)}")
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}")

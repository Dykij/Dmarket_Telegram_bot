import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from common.redis_connector import RedisConnector
from redis.exceptions import ConnectionError, TimeoutError, RedisError


@pytest.fixture
def mock_aioredis_create_redis_pool():
    """Fixture to mock aioredis.create_redis_pool."""
    with patch("aioredis.create_redis_pool") as mock_create_pool:
        # Create a mock Redis client
        mock_client = AsyncMock()
        mock_create_pool.return_value = mock_client
        yield mock_create_pool, mock_client


@pytest.mark.asyncio
async def test_redis_connector_init():
    """Test RedisConnector initialization with default parameters."""
    connector = RedisConnector(host="localhost", port=6379, db=0)
    
    assert connector.host == "localhost"
    assert connector.port == 6379
    assert connector.db == 0
    assert connector.password is None
    assert connector.max_connections == 10
    assert connector.min_connections == 1
    assert connector.retry_attempts == 3
    assert connector.retry_delay == 1.0
    assert connector.sentinel_master is None
    assert connector.sentinel_nodes is None
    assert connector.cluster_mode is False
    assert connector.ssl is False
    assert connector.client is None


@pytest.mark.asyncio
async def test_redis_connector_init_with_params():
    """Test RedisConnector initialization with custom parameters."""
    connector = RedisConnector(
        host="redis.example.com",
        port=6380,
        db=1,
        password="secret",
        max_connections=20,
        min_connections=5,
        retry_attempts=5,
        retry_delay=2.0,
        sentinel_master="mymaster",
        sentinel_nodes=[("sentinel1.example.com", 26379)],
        cluster_mode=True,
        ssl=True,
        ssl_cert_reqs="required",
        ssl_ca_certs="/path/to/ca.pem"
    )
    
    assert connector.host == "redis.example.com"
    assert connector.port == 6380
    assert connector.db == 1
    assert connector.password == "secret"
    assert connector.max_connections == 20
    assert connector.min_connections == 5
    assert connector.retry_attempts == 5
    assert connector.retry_delay == 2.0
    assert connector.sentinel_master == "mymaster"
    assert connector.sentinel_nodes == [("sentinel1.example.com", 26379)]
    assert connector.cluster_mode is True
    assert connector.ssl is True
    assert connector.ssl_cert_reqs == "required"
    assert connector.ssl_ca_certs == "/path/to/ca.pem"
    assert connector.client is None


@pytest.mark.asyncio
async def test_get_client_standard_connection(mock_aioredis_create_redis_pool):
    """Test getting a Redis client with standard connection."""
    mock_create_pool, mock_client = mock_aioredis_create_redis_pool
    
    connector = RedisConnector(host="localhost", port=6379, db=0, password="secret")
    client = await connector.get_client()
    
    assert client == mock_client
    mock_create_pool.assert_called_once_with(
        "redis://localhost:6379",
        db=0,
        password="secret",
        maxsize=10,
        minsize=1,
        ssl=False,
        ssl_cert_reqs="required",
        ssl_ca_certs=None,
        ssl_certfile=None,
        ssl_keyfile=None
    )


@pytest.mark.asyncio
async def test_get_client_sentinel_connection(mock_aioredis_create_redis_pool):
    """Test getting a Redis client with Sentinel connection."""
    mock_create_pool, mock_client = mock_aioredis_create_redis_pool
    
    connector = RedisConnector(
        host="sentinel.example.com",
        port=26379,
        db=0,
        password="secret",
        sentinel_master="mymaster",
        sentinel_nodes=[
            ("sentinel1.example.com", 26379),
            ("sentinel2.example.com", 26379)
        ]
    )
    client = await connector.get_client()
    
    assert client == mock_client
    mock_create_pool.assert_called_once_with(
        ["redis://sentinel1.example.com:26379", "redis://sentinel2.example.com:26379"],
        db=0,
        password="secret",
        maxsize=10,
        minsize=1,
        sentinel=True,
        sentinel_master="mymaster",
        ssl=False,
        ssl_cert_reqs="required",
        ssl_ca_certs=None,
        ssl_certfile=None,
        ssl_keyfile=None
    )


@pytest.mark.asyncio
async def test_get_client_cluster_connection(mock_aioredis_create_redis_pool):
    """Test getting a Redis client with Cluster connection."""
    mock_create_pool, mock_client = mock_aioredis_create_redis_pool
    
    connector = RedisConnector(
        host="redis1.example.com,redis2.example.com",
        port=6379,
        db=0,
        password="secret",
        cluster_mode=True
    )
    client = await connector.get_client()
    
    assert client == mock_client
    mock_create_pool.assert_called_once_with(
        ["redis://redis1.example.com:6379", "redis://redis2.example.com:6379"],
        db=0,
        password="secret",
        maxsize=10,
        minsize=1,
        ssl=False,
        ssl_cert_reqs="required",
        ssl_ca_certs=None,
        ssl_certfile=None,
        ssl_keyfile=None
    )


@pytest.mark.asyncio
async def test_get_client_ssl_connection(mock_aioredis_create_redis_pool):
    """Test getting a Redis client with SSL connection."""
    mock_create_pool, mock_client = mock_aioredis_create_redis_pool
    
    connector = RedisConnector(
        host="localhost",
        port=6379,
        db=0,
        password="secret",
        ssl=True,
        ssl_cert_reqs="required",
        ssl_ca_certs="/path/to/ca.pem",
        ssl_certfile="/path/to/cert.pem",
        ssl_keyfile="/path/to/key.pem"
    )
    client = await connector.get_client()
    
    assert client == mock_client
    mock_create_pool.assert_called_once_with(
        "redis://localhost:6379",
        db=0,
        password="secret",
        maxsize=10,
        minsize=1,
        ssl=True,
        ssl_cert_reqs="required",
        ssl_ca_certs="/path/to/ca.pem",
        ssl_certfile="/path/to/cert.pem",
        ssl_keyfile="/path/to/key.pem"
    )


@pytest.mark.asyncio
async def test_get_client_connection_retry(mock_aioredis_create_redis_pool):
    """Test retry logic when connection fails."""
    mock_create_pool, mock_client = mock_aioredis_create_redis_pool
    
    # Make the first two attempts fail, then succeed
    mock_create_pool.side_effect = [
        ConnectionError("Connection refused"),
        ConnectionError("Connection refused"),
        mock_client
    ]
    
    connector = RedisConnector(
        host="localhost",
        port=6379,
        db=0,
        retry_attempts=3,
        retry_delay=0.1  # Short delay for testing
    )
    
    # Mock asyncio.sleep to avoid actual delays in tests
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        client = await connector.get_client()
    
    assert client == mock_client
    assert mock_create_pool.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(0.1)


@pytest.mark.asyncio
async def test_get_client_connection_retry_exhausted(mock_aioredis_create_redis_pool):
    """Test that an exception is raised when all retry attempts fail."""
    mock_create_pool, _ = mock_aioredis_create_redis_pool
    
    # Make all attempts fail
    mock_create_pool.side_effect = ConnectionError("Connection refused")
    
    connector = RedisConnector(
        host="localhost",
        port=6379,
        db=0,
        retry_attempts=3,
        retry_delay=0.1  # Short delay for testing
    )
    
    # Mock asyncio.sleep to avoid actual delays in tests
    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ConnectionError):
            await connector.get_client()
    
    assert mock_create_pool.call_count == 3


@pytest.mark.asyncio
async def test_close(mock_aioredis_create_redis_pool):
    """Test closing the Redis connection."""
    _, mock_client = mock_aioredis_create_redis_pool
    
    connector = RedisConnector(host="localhost", port=6379, db=0)
    connector.client = mock_client
    
    await connector.close()
    
    mock_client.close.assert_called_once()
    mock_client.wait_closed.assert_called_once()
    assert connector.client is None


@pytest.mark.asyncio
async def test_close_no_client():
    """Test closing when no client exists."""
    connector = RedisConnector(host="localhost", port=6379, db=0)
    connector.client = None
    
    # This should not raise an exception
    await connector.close()


@pytest.mark.asyncio
async def test_execute_with_retry_success(mock_aioredis_create_redis_pool):
    """Test successful execution of a Redis command with retry logic."""
    _, mock_client = mock_aioredis_create_redis_pool
    
    # Set up the mock client to return a value for the 'get' command
    mock_get = AsyncMock(return_value=b"test_value")
    mock_client.get = mock_get
    
    connector = RedisConnector(host="localhost", port=6379, db=0)
    connector.client = mock_client
    
    result = await connector.execute_with_retry("get", "test_key")
    
    assert result == b"test_value"
    mock_get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_execute_with_retry_temporary_failure(mock_aioredis_create_redis_pool):
    """Test retry logic when a Redis command fails temporarily."""
    _, mock_client = mock_aioredis_create_redis_pool
    
    # Set up the mock client to fail twice, then succeed
    mock_get = AsyncMock(side_effect=[
        ConnectionError("Connection lost"),
        TimeoutError("Command timed out"),
        b"test_value"
    ])
    mock_client.get = mock_get
    
    connector = RedisConnector(
        host="localhost",
        port=6379,
        db=0,
        retry_attempts=3,
        retry_delay=0.1  # Short delay for testing
    )
    connector.client = mock_client
    
    # Mock asyncio.sleep to avoid actual delays in tests
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await connector.execute_with_retry("get", "test_key")
    
    assert result == b"test_value"
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(0.1)


@pytest.mark.asyncio
async def test_execute_with_retry_persistent_failure(mock_aioredis_create_redis_pool):
    """Test that an exception is raised when a Redis command fails persistently."""
    _, mock_client = mock_aioredis_create_redis_pool
    
    # Set up the mock client to always fail
    mock_get = AsyncMock(side_effect=ConnectionError("Connection lost"))
    mock_client.get = mock_get
    
    connector = RedisConnector(
        host="localhost",
        port=6379,
        db=0,
        retry_attempts=3,
        retry_delay=0.1  # Short delay for testing
    )
    connector.client = mock_client
    
    # Mock asyncio.sleep to avoid actual delays in tests
    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ConnectionError):
            await connector.execute_with_retry("get", "test_key")
    
    assert mock_get.call_count == 3


@pytest.mark.asyncio
async def test_create_sync_redis_standard():
    """Test creating a synchronous Redis client with standard connection."""
    with patch("redis.ConnectionPool") as mock_pool, \
         patch("redis.Redis") as mock_redis:
        
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        
        result = RedisConnector.create(
            host="localhost",
            port="6379",
            db="0",
            password="secret",
            socket_timeout=10.0,
            max_connections=20
        )
        
        assert result == mock_redis_instance
        mock_pool.assert_called_once()
        mock_redis.assert_called_once()


@pytest.mark.asyncio
async def test_create_sync_redis_sentinel():
    """Test creating a synchronous Redis client with Sentinel connection."""
    with patch("redis.sentinel.Sentinel") as mock_sentinel:
        
        mock_master = MagicMock()
        mock_sentinel_instance = MagicMock()
        mock_sentinel_instance.master_for.return_value = mock_master
        mock_sentinel.return_value = mock_sentinel_instance
        
        result = RedisConnector.create(
            host="sentinel.example.com",
            port="26379",
            db="0",
            password="secret",
            sentinel_master="mymaster",
            sentinel_nodes=[
                ("sentinel1.example.com", 26379),
                ("sentinel2.example.com", 26379)
            ]
        )
        
        assert result == mock_master
        mock_sentinel.assert_called_once_with(
            [("sentinel1.example.com", 26379), ("sentinel2.example.com", 26379)],
            socket_timeout=5.0,
            password="secret",
            ssl=False,
            ssl_cert_reqs="required",
            ssl_ca_certs=None,
            ssl_certfile=None,
            ssl_keyfile=None
        )
        mock_sentinel_instance.master_for.assert_called_once()


@pytest.mark.asyncio
async def test_create_sync_redis_cluster():
    """Test creating a synchronous Redis client with Cluster connection."""
    with patch("redis.cluster.RedisCluster") as mock_cluster:
        
        mock_cluster_instance = MagicMock()
        mock_cluster.return_value = mock_cluster_instance
        
        result = RedisConnector.create(
            host="redis1.example.com,redis2.example.com",
            port="6379",
            db="0",
            password="secret",
            cluster_mode=True
        )
        
        assert result == mock_cluster_instance
        mock_cluster.assert_called_once()
        # Check that startup_nodes contains both hosts
        call_kwargs = mock_cluster.call_args.kwargs
        startup_nodes = call_kwargs.get("startup_nodes", [])
        assert len(startup_nodes) == 2
        assert {"host": "redis1.example.com", "port": 6379} in startup_nodes
        assert {"host": "redis2.example.com", "port": 6379} in startup_nodes


@pytest.mark.asyncio
async def test_create_sync_redis_ssl():
    """Test creating a synchronous Redis client with SSL connection."""
    with patch("redis.ConnectionPool") as mock_pool, \
         patch("redis.Redis") as mock_redis:
        
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        
        result = RedisConnector.create(
            host="localhost",
            port="6379",
            db="0",
            password="secret",
            ssl=True,
            ssl_cert_reqs="required",
            ssl_ca_certs="/path/to/ca.pem",
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem"
        )
        
        assert result == mock_redis_instance
        mock_pool.assert_called_once()
        # Check that SSL parameters are passed correctly
        call_kwargs = mock_pool.call_args.kwargs
        assert call_kwargs.get("ssl") is True
        assert call_kwargs.get("ssl_cert_reqs") == "required"
        assert call_kwargs.get("ssl_ca_certs") == "/path/to/ca.pem"
        assert call_kwargs.get("ssl_certfile") == "/path/to/cert.pem"
        assert call_kwargs.get("ssl_keyfile") == "/path/to/key.pem"
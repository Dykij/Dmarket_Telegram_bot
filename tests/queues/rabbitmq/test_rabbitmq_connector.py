import asyncio
import ssl
from datetime import timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from aio_pika import Channel, DeliveryMode, Message
from aio_pika.exceptions import AMQPConnectionError, AMQPError

from common.rabbitmq_connector import RabbitMQConnector
from common.rpc.rabbitmq_client import RabbitMQClient


@pytest.fixture
def mock_rabbitmq_client():
    """Fixture to mock RabbitMQClient."""
    with patch("common.rpc.rabbitmq_client.RabbitMQClient") as mock_client_class:
        mock_client = MagicMock(spec=RabbitMQClient)
        mock_client.connect = AsyncMock()
        mock_client.create_channel = AsyncMock()
        mock_client.return_channel = AsyncMock()
        mock_client.close_channel = AsyncMock()
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client
        yield mock_client_class, mock_client


@pytest.fixture
def mock_channel():
    """Fixture to mock aio_pika Channel."""
    mock_channel = MagicMock(spec=Channel)
    mock_channel.declare_queue = AsyncMock()
    mock_exchange = MagicMock()
    mock_exchange.publish = AsyncMock()
    mock_channel.default_exchange = mock_exchange
    return mock_channel


@pytest.fixture
def mock_queue_factory():
    """Fixture to mock QueueFactory."""
    with patch("common.rpc.queue_factory.QueueFactory") as mock_factory_class:
        mock_factory = MagicMock()
        mock_factory.connect_publisher = AsyncMock()
        mock_factory.connect_listener = AsyncMock()
        mock_factory.connect_reader = AsyncMock()
        mock_factory_class.return_value = mock_factory
        yield mock_factory_class, mock_factory


@pytest.mark.asyncio
async def test_rabbitmq_connector_init():
    """Test RabbitMQConnector initialization with default parameters."""
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    assert connector.host == "localhost"
    assert connector.port == "5672"
    assert connector.user == "guest"
    assert connector.password == "guest"
    assert connector.virtual_host == "/"
    assert connector.connection_name is None
    assert connector.ssl_enabled is False
    assert connector.ssl_context is None
    assert connector.heartbeat == 60
    assert connector.connection_timeout == 10.0
    assert connector.retry_attempts == 3
    assert connector.retry_delay == 1.0
    assert connector.channel_pool_size == 10
    assert connector.client is None


@pytest.mark.asyncio
async def test_rabbitmq_connector_init_with_params():
    """Test RabbitMQConnector initialization with custom parameters."""
    ssl_context = ssl.create_default_context()
    
    connector = RabbitMQConnector(
        host="rabbitmq.example.com",
        port="5673",
        user="admin",
        password="secret",
        virtual_host="/test",
        connection_name="test_connection",
        ssl_enabled=True,
        ssl_context=ssl_context,
        heartbeat=30,
        connection_timeout=5.0,
        retry_attempts=5,
        retry_delay=2.0,
        channel_pool_size=20
    )
    
    assert connector.host == "rabbitmq.example.com"
    assert connector.port == "5673"
    assert connector.user == "admin"
    assert connector.password == "secret"
    assert connector.virtual_host == "/test"
    assert connector.connection_name == "test_connection"
    assert connector.ssl_enabled is True
    assert connector.ssl_context == ssl_context
    assert connector.heartbeat == 30
    assert connector.connection_timeout == 5.0
    assert connector.retry_attempts == 5
    assert connector.retry_delay == 2.0
    assert connector.channel_pool_size == 20
    assert connector.client is None


@pytest.mark.asyncio
async def test_connect(mock_rabbitmq_client):
    """Test connecting to RabbitMQ."""
    mock_client_class, mock_client = mock_rabbitmq_client
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    result = await connector.connect()
    
    assert result == mock_client
    assert connector.client == mock_client
    mock_client_class.assert_called_once_with(
        host="localhost",
        port=5672,
        login="guest",
        password="guest",
        connection_name=None,
        virtual_host="/",
        ssl_context=None,
        heartbeat=60,
        connection_timeout=10.0,
        retry_attempts=3,
        retry_delay=1.0,
        channel_pool_size=10
    )
    mock_client.connect.assert_called_once()


@pytest.mark.asyncio
async def test_connect_with_ssl(mock_rabbitmq_client):
    """Test connecting to RabbitMQ with SSL."""
    mock_client_class, mock_client = mock_rabbitmq_client
    ssl_context = ssl.create_default_context()
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/",
        ssl_enabled=True,
        ssl_context=ssl_context
    )
    
    result = await connector.connect()
    
    assert result == mock_client
    mock_client_class.assert_called_once_with(
        host="localhost",
        port=5672,
        login="guest",
        password="guest",
        connection_name=None,
        virtual_host="/",
        ssl_context=ssl_context,
        heartbeat=60,
        connection_timeout=10.0,
        retry_attempts=3,
        retry_delay=1.0,
        channel_pool_size=10
    )


@pytest.mark.asyncio
async def test_connect_with_cluster(mock_rabbitmq_client):
    """Test connecting to RabbitMQ cluster."""
    mock_client_class, mock_client = mock_rabbitmq_client
    
    connector = RabbitMQConnector(
        host="rabbit1.example.com,rabbit2.example.com,rabbit3.example.com",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    result = await connector.connect()
    
    assert result == mock_client
    mock_client_class.assert_called_once_with(
        host="rabbit1.example.com,rabbit2.example.com,rabbit3.example.com",
        port=5672,
        login="guest",
        password="guest",
        connection_name=None,
        virtual_host="/",
        ssl_context=None,
        heartbeat=60,
        connection_timeout=10.0,
        retry_attempts=3,
        retry_delay=1.0,
        channel_pool_size=10
    )


@pytest.mark.asyncio
async def test_connect_error(mock_rabbitmq_client):
    """Test error handling when connecting to RabbitMQ."""
    mock_client_class, mock_client = mock_rabbitmq_client
    mock_client.connect.side_effect = AMQPConnectionError("Connection refused")
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    with pytest.raises(AMQPConnectionError):
        await connector.connect()


@pytest.mark.asyncio
async def test_get_channel(mock_rabbitmq_client, mock_channel):
    """Test getting a channel."""
    _, mock_client = mock_rabbitmq_client
    mock_client.create_channel.return_value = mock_channel
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    result = await connector.get_channel()
    
    assert result == mock_channel
    mock_client.create_channel.assert_called_once()


@pytest.mark.asyncio
async def test_get_channel_no_client(mock_rabbitmq_client, mock_channel):
    """Test getting a channel when no client exists."""
    _, mock_client = mock_rabbitmq_client
    mock_client.create_channel.return_value = mock_channel
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = None
    
    # Mock connect to avoid actual connection
    connector.connect = AsyncMock(return_value=mock_client)
    
    result = await connector.get_channel()
    
    assert result == mock_channel
    connector.connect.assert_called_once()
    mock_client.create_channel.assert_called_once()


@pytest.mark.asyncio
async def test_get_channel_error(mock_rabbitmq_client):
    """Test error handling when getting a channel."""
    _, mock_client = mock_rabbitmq_client
    mock_client.create_channel.side_effect = AMQPError("Channel error")
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    with pytest.raises(AMQPError):
        await connector.get_channel()


@pytest.mark.asyncio
async def test_return_channel(mock_rabbitmq_client, mock_channel):
    """Test returning a channel to the pool."""
    _, mock_client = mock_rabbitmq_client
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    await connector.return_channel(mock_channel)
    
    mock_client.return_channel.assert_called_once_with(mock_channel)


@pytest.mark.asyncio
async def test_return_channel_no_client(mock_channel):
    """Test returning a channel when no client exists."""
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = None
    
    # Mock close_channel to avoid actual closing
    connector.close_channel = AsyncMock()
    
    await connector.return_channel(mock_channel)
    
    connector.close_channel.assert_called_once_with(mock_channel)


@pytest.mark.asyncio
async def test_close_channel(mock_rabbitmq_client, mock_channel):
    """Test closing a channel."""
    _, mock_client = mock_rabbitmq_client
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    await connector.close_channel(mock_channel)
    
    mock_client.close_channel.assert_called_once_with(mock_channel)


@pytest.mark.asyncio
async def test_close_channel_no_client(mock_channel):
    """Test closing a channel when no client exists."""
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = None
    
    # This should not raise an exception
    await connector.close_channel(mock_channel)


@pytest.mark.asyncio
async def test_publish(mock_channel):
    """Test publishing a message."""
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    await connector.publish(
        channel=mock_channel,
        routing_key="test_queue",
        body=b"test message",
        persistent=True,
        content_type="text/plain",
        priority=5,
        correlation_id="123",
        reply_to="reply_queue",
        expiration=timedelta(minutes=5),
        message_id="msg_123",
        headers={"source": "test"}
    )
    
    mock_channel.default_exchange.publish.assert_called_once()
    # Check that the message was created with the correct parameters
    call_args = mock_channel.default_exchange.publish.call_args
    message = call_args[0][0]
    assert message.body == b"test message"
    assert message.content_type == "text/plain"
    assert message.priority == 5
    assert message.correlation_id == "123"
    assert message.reply_to == "reply_queue"
    assert message.message_id == "msg_123"
    assert message.headers == {"source": "test"}
    assert message.delivery_mode == DeliveryMode.PERSISTENT
    # Check that the routing key was correct
    assert call_args[1]["routing_key"] == "test_queue"


@pytest.mark.asyncio
async def test_publish_not_persistent(mock_channel):
    """Test publishing a non-persistent message."""
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    await connector.publish(
        channel=mock_channel,
        routing_key="test_queue",
        body=b"test message",
        persistent=False
    )
    
    mock_channel.default_exchange.publish.assert_called_once()
    # Check that the message was created with the correct delivery mode
    call_args = mock_channel.default_exchange.publish.call_args
    message = call_args[0][0]
    assert message.delivery_mode == DeliveryMode.NOT_PERSISTENT


@pytest.mark.asyncio
async def test_publish_error(mock_channel):
    """Test error handling when publishing a message."""
    mock_channel.default_exchange.publish.side_effect = AMQPError("Publish error")
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    with pytest.raises(AMQPError):
        await connector.publish(
            channel=mock_channel,
            routing_key="test_queue",
            body=b"test message"
        )


@pytest.mark.asyncio
async def test_create_queue(mock_channel):
    """Test creating a queue."""
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    await connector.create_queue(
        channel=mock_channel,
        queue_name="test_queue",
        durable=True,
        exclusive=False,
        auto_delete=False,
        message_ttl=timedelta(hours=1),
        dead_letter_exchange="dlx",
        dead_letter_routing_key="dlq",
        max_length=1000,
        max_priority=10
    )
    
    mock_channel.declare_queue.assert_called_once_with(
        name="test_queue",
        durable=True,
        exclusive=False,
        auto_delete=False,
        arguments={
            "x-message-ttl": 3600000,  # 1 hour in milliseconds
            "x-dead-letter-exchange": "dlx",
            "x-dead-letter-routing-key": "dlq",
            "x-max-length": 1000,
            "x-max-priority": 10
        }
    )


@pytest.mark.asyncio
async def test_create_queue_minimal(mock_channel):
    """Test creating a queue with minimal parameters."""
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    await connector.create_queue(
        channel=mock_channel,
        queue_name="test_queue"
    )
    
    mock_channel.declare_queue.assert_called_once_with(
        name="test_queue",
        durable=True,
        exclusive=False,
        auto_delete=False,
        arguments={}
    )


@pytest.mark.asyncio
async def test_create_queue_error(mock_channel):
    """Test error handling when creating a queue."""
    mock_channel.declare_queue.side_effect = AMQPError("Queue error")
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    
    with pytest.raises(AMQPError):
        await connector.create_queue(
            channel=mock_channel,
            queue_name="test_queue"
        )


@pytest.mark.asyncio
async def test_create_publisher(mock_rabbitmq_client, mock_queue_factory):
    """Test creating a publisher."""
    _, mock_client = mock_rabbitmq_client
    _, mock_factory = mock_queue_factory
    mock_publisher = MagicMock()
    mock_factory.connect_publisher.return_value = mock_publisher
    
    # Create a mock queue class
    class TestQueue:
        queue_name = "test_queue"
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    result = await connector.create_publisher(
        queue_class=TestQueue,
        passive=True,
        message_ttl=timedelta(hours=1)
    )
    
    assert result == mock_publisher
    mock_factory.connect_publisher.assert_called_once_with(
        name="test_queue",
        client=mock_client,
        passive=True,
        message_ttl=timedelta(hours=1)
    )


@pytest.mark.asyncio
async def test_create_publisher_no_client(mock_rabbitmq_client, mock_queue_factory):
    """Test creating a publisher when no client exists."""
    _, mock_client = mock_rabbitmq_client
    _, mock_factory = mock_queue_factory
    mock_publisher = MagicMock()
    mock_factory.connect_publisher.return_value = mock_publisher
    
    # Create a mock queue class
    class TestQueue:
        queue_name = "test_queue"
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = None
    
    # Mock connect to avoid actual connection
    connector.connect = AsyncMock(return_value=mock_client)
    
    result = await connector.create_publisher(
        queue_class=TestQueue
    )
    
    assert result == mock_publisher
    connector.connect.assert_called_once()
    mock_factory.connect_publisher.assert_called_once()


@pytest.mark.asyncio
async def test_create_publisher_error(mock_rabbitmq_client, mock_queue_factory):
    """Test error handling when creating a publisher."""
    _, mock_client = mock_rabbitmq_client
    _, mock_factory = mock_queue_factory
    mock_factory.connect_publisher.side_effect = AMQPError("Publisher error")
    
    # Create a mock queue class
    class TestQueue:
        queue_name = "test_queue"
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    with pytest.raises(AMQPError):
        await connector.create_publisher(
            queue_class=TestQueue
        )


@pytest.mark.asyncio
async def test_create_listener(mock_rabbitmq_client, mock_queue_factory):
    """Test creating a listener."""
    _, mock_client = mock_rabbitmq_client
    _, mock_factory = mock_queue_factory
    mock_listener = MagicMock()
    mock_factory.connect_listener.return_value = mock_listener
    
    # Create a mock queue class
    class TestQueue:
        queue_name = "test_queue"
    
    # Create a mock callback
    async def callback(message):
        pass
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    result = await connector.create_listener(
        queue_class=TestQueue,
        on_message_callback=callback,
        passive=True,
        message_ttl=timedelta(hours=1)
    )
    
    assert result == mock_listener
    mock_factory.connect_listener.assert_called_once_with(
        name="test_queue",
        client=mock_client,
        on_msg=callback,
        passive=True,
        message_ttl=timedelta(hours=1)
    )


@pytest.mark.asyncio
async def test_create_reader(mock_rabbitmq_client, mock_queue_factory):
    """Test creating a reader."""
    _, mock_client = mock_rabbitmq_client
    _, mock_factory = mock_queue_factory
    mock_reader = MagicMock()
    mock_factory.connect_reader.return_value = mock_reader
    
    # Create a mock queue class
    class TestQueue:
        queue_name = "test_queue"
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    result = await connector.create_reader(
        queue_class=TestQueue,
        passive=True,
        message_ttl=timedelta(hours=1)
    )
    
    assert result == mock_reader
    mock_factory.connect_reader.assert_called_once_with(
        name="test_queue",
        client=mock_client,
        passive=True,
        message_ttl=timedelta(hours=1)
    )


@pytest.mark.asyncio
async def test_close(mock_rabbitmq_client):
    """Test closing the RabbitMQ connection."""
    _, mock_client = mock_rabbitmq_client
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    await connector.close()
    
    mock_client.close.assert_called_once()
    assert connector.client is None


@pytest.mark.asyncio
async def test_close_no_client():
    """Test closing when no client exists."""
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = None
    
    # This should not raise an exception
    await connector.close()


@pytest.mark.asyncio
async def test_close_error(mock_rabbitmq_client):
    """Test error handling when closing the connection."""
    _, mock_client = mock_rabbitmq_client
    mock_client.close.side_effect = AMQPError("Close error")
    
    connector = RabbitMQConnector(
        host="localhost",
        port="5672",
        user="guest",
        password="guest",
        virtual_host="/"
    )
    connector.client = mock_client
    
    # This should not raise an exception
    await connector.close()
    
    # The client should still be set to None
    assert connector.client is None
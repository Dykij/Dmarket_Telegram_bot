# Redis and RabbitMQ Module Improvements

This document outlines the improvements made to the Redis and RabbitMQ modules in the Dmarket Telegram Bot project.

## Redis Improvements

The Redis connector module (`common/redis_connector.py`) has been enhanced with the following features:

### Connection Management
- **Connection Pooling**: Configurable pool size with `max_connections` and `min_connections` parameters
- **Retry Logic**: Automatic retry on connection failures with configurable attempts and delay
- **High Availability**: Support for Redis Sentinel for automatic failover
- **Scalability**: Support for Redis Cluster mode for horizontal scaling
- **SSL Support**: Secure connections with configurable SSL parameters

### Error Handling
- **Comprehensive Logging**: Detailed logging of connection events and errors
- **Robust Error Handling**: Proper exception handling and propagation
- **Command Retry**: New `execute_with_retry` method for executing Redis commands with automatic retry

### Example Usage

```python
# Create a Redis connector with enhanced features
redis_connector = RedisConnector(
    host="localhost",
    port=6379,
    db=0,
    password="your_password",
    max_connections=20,
    min_connections=5,
    retry_attempts=3,
    retry_delay=1.0,
    ssl=True,
    ssl_cert_reqs="required",
    ssl_ca_certs="/path/to/ca.pem"
)

# Get a Redis client
redis_client = await redis_connector.get_client()

# Execute a command with retry logic
result = await redis_connector.execute_with_retry("get", "my_key")

# Create a synchronous Redis client with enhanced features
sync_redis = RedisConnector.create(
    host="localhost",
    port="6379",
    db="0",
    password="your_password",
    socket_timeout=5.0,
    max_connections=20,
    cluster_mode=True
)
```

### Redis Sentinel Example

```python
# Create a Redis connector with Sentinel support
redis_connector = RedisConnector(
    host="sentinel1.example.com",  # Not used with Sentinel
    port=26379,                    # Sentinel port
    db=0,
    password="your_password",
    sentinel_master="mymaster",
    sentinel_nodes=[
        ("sentinel1.example.com", 26379),
        ("sentinel2.example.com", 26379),
        ("sentinel3.example.com", 26379)
    ]
)
```

### Redis Cluster Example

```python
# Create a Redis connector with Cluster support
redis_connector = RedisConnector(
    host="redis1.example.com,redis2.example.com,redis3.example.com",
    port=6379,
    db=0,
    password="your_password",
    cluster_mode=True
)
```

## RabbitMQ Improvements

The RabbitMQ modules (`common/rpc/rabbitmq_client.py` and `common/rabbitmq_connector.py`) have been enhanced with the following features:

### Connection Management
- **Channel Pooling**: Reusable channel pool with configurable size
- **Retry Logic**: Automatic retry on connection failures with configurable attempts and delay
- **Cluster Support**: Support for RabbitMQ clusters with automatic failover
- **SSL Support**: Secure connections with configurable SSL parameters
- **Heartbeat**: Configurable heartbeat interval to detect connection issues
- **Connection Timeout**: Configurable connection timeout

### Message Handling
- **Message Persistence**: Control over message durability
- **Message TTL**: Time-to-live for messages
- **Dead Letter Exchanges**: Support for handling failed messages
- **Priority Queues**: Support for message priorities
- **Publisher Confirms**: Ensure messages are delivered
- **Comprehensive Message Properties**: Control over all AMQP message properties

### Error Handling
- **Comprehensive Logging**: Detailed logging of connection events and errors
- **Robust Error Handling**: Proper exception handling and propagation
- **Connection and Channel Callbacks**: Callbacks for connection and channel close events

### Example Usage

```python
# Create a RabbitMQ connector with enhanced features
rabbitmq_connector = RabbitMQConnector(
    host="localhost",
    port="5672",
    user="guest",
    password="guest",
    virtual_host="/",
    connection_name="my_connection",
    ssl_enabled=True,
    heartbeat=60,
    connection_timeout=10.0,
    retry_attempts=3,
    retry_delay=1.0,
    channel_pool_size=10
)

# Connect to RabbitMQ
await rabbitmq_connector.connect()

# Get a channel
channel = await rabbitmq_connector.get_channel()

# Create a queue with advanced options
await rabbitmq_connector.create_queue(
    channel=channel,
    queue_name="my_queue",
    durable=True,
    message_ttl=timedelta(hours=1),
    dead_letter_exchange="dlx",
    dead_letter_routing_key="dlq",
    max_priority=10
)

# Publish a message with advanced options
await rabbitmq_connector.publish(
    channel=channel,
    routing_key="my_queue",
    body=b"Hello, World!",
    persistent=True,
    content_type="text/plain",
    priority=5,
    expiration=timedelta(minutes=30),
    headers={"source": "my_app"}
)

# Return the channel to the pool when done
await rabbitmq_connector.return_channel(channel)

# Create a publisher for a queue class
publisher = await rabbitmq_connector.create_publisher(
    queue_class=MyQueueClass,
    message_ttl=timedelta(hours=1)
)

# Create a listener for a queue class
listener = await rabbitmq_connector.create_listener(
    queue_class=MyQueueClass,
    on_message_callback=my_callback_function,
    message_ttl=timedelta(hours=1)
)

# Create a reader for a queue class
reader = await rabbitmq_connector.create_reader(
    queue_class=MyQueueClass,
    message_ttl=timedelta(hours=1)
)

# Close the connection when done
await rabbitmq_connector.close()
```

### RabbitMQ Cluster Example

```python
# Create a RabbitMQ connector with Cluster support
rabbitmq_connector = RabbitMQConnector(
    host="rabbit1.example.com,rabbit2.example.com,rabbit3.example.com",
    port="5672",
    user="guest",
    password="guest",
    virtual_host="/"
)
```

## Migration Guide

### Redis Migration

The improved Redis connector is backward compatible with the existing code. However, to take advantage of the new features, you can update your code as follows:

```python
# Old code
redis_connector = RedisConnector(
    host="localhost",
    port=6379,
    db=0,
    password="your_password"
)

# New code with enhanced features
redis_connector = RedisConnector(
    host="localhost",
    port=6379,
    db=0,
    password="your_password",
    max_connections=20,
    retry_attempts=3
)

# Use the new execute_with_retry method
result = await redis_connector.execute_with_retry("get", "my_key")
```

### RabbitMQ Migration

The improved RabbitMQ connector is backward compatible with the existing code. However, to take advantage of the new features, you can update your code as follows:

```python
# Old code
rabbitmq_connector = RabbitMQConnector(
    host="localhost",
    port="5672",
    user="guest",
    password="guest",
    virtual_host="/",
    connection_name="my_connection"
)

# New code with enhanced features
rabbitmq_connector = RabbitMQConnector(
    host="localhost",
    port="5672",
    user="guest",
    password="guest",
    virtual_host="/",
    connection_name="my_connection",
    retry_attempts=3,
    channel_pool_size=10
)

# Use the new channel pooling feature
channel = await rabbitmq_connector.get_channel()
# ... use the channel ...
await rabbitmq_connector.return_channel(channel)  # Return to pool instead of closing

# Use the new create_queue method
await rabbitmq_connector.create_queue(
    channel=channel,
    queue_name="my_queue",
    durable=True,
    message_ttl=timedelta(hours=1)
)

# Use the enhanced publish method
await rabbitmq_connector.publish(
    channel=channel,
    routing_key="my_queue",
    body=b"Hello, World!",
    persistent=True,
    content_type="text/plain"
)
```
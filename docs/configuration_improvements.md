# Configuration Management Improvements for Dmarket Telegram Bot

This document outlines the implementation of a centralized configuration management system for the Dmarket Telegram Bot project, addressing one of the key improvement areas identified in the repository analysis.

## Overview

The configuration management system will enable:
- Centralized management of all configuration parameters
- Environment-specific configuration (development, testing, production)
- Runtime configuration updates without service restarts
- Validation of configuration parameters
- Secure storage of sensitive configuration data

## Current Issues

The current configuration approach has several limitations:
- Some parameters are hardcoded in the codebase
- Multiple environment files need to be manually configured
- No centralized management of configuration
- Limited validation of configuration parameters
- No support for hot reloading configuration changes

## Implementation Details

### 1. Configuration Management System

We'll implement a comprehensive configuration management system using a combination of:
- Environment variables
- Configuration files (YAML/JSON)
- A configuration service for runtime updates
- Validation schemas for configuration parameters

#### Directory Structure:
```
Dmarket_Telegram_bot/
├── config/
│   ├── __init__.py
│   ├── config_manager.py
│   ├── validators.py
│   ├── defaults.py
│   └── schemas/
│       ├── __init__.py
│       ├── app_schema.py
│       ├── redis_schema.py
│       ├── rabbitmq_schema.py
│       └── telegram_schema.py
├── config_files/
│   ├── config.dev.yaml
│   ├── config.test.yaml
│   └── config.prod.yaml
```

### 2. Core Components

#### 1. Configuration Manager

```python
import os
import yaml
import json
import logging
from typing import Any, Dict, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Centralized configuration management system.

    This class provides a unified interface for accessing configuration
    parameters from various sources (environment variables, config files)
    with support for validation, defaults, and runtime updates.
    """

    def __init__(
        self,
        config_dir: str = "config_files",
        env_prefix: str = "DMARKET_",
        environment: Optional[str] = None,
        validate: bool = True
    ):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files
            env_prefix: Prefix for environment variables
            environment: Environment name (dev, test, prod)
            validate: Whether to validate configuration against schemas
        """
        self.config_dir = Path(config_dir)
        self.env_prefix = env_prefix
        self.environment = environment or os.getenv(f"{env_prefix}ENVIRONMENT", "dev")
        self.validate = validate

        # Internal configuration storage
        self._config: Dict[str, Any] = {}
        self._loaded = False

        # Load validators if validation is enabled
        if validate:
            from .validators import ConfigValidator
            self.validator = ConfigValidator()

    def load(self, reload: bool = False) -> None:
        """
        Load configuration from all sources.

        Args:
            reload: Force reload even if already loaded
        """
        if self._loaded and not reload:
            return

        # Start with default configuration
        from .defaults import DEFAULT_CONFIG
        self._config = DEFAULT_CONFIG.copy()

        # Load configuration from file
        self._load_from_file()

        # Override with environment variables
        self._load_from_env()

        # Validate configuration if enabled
        if self.validate:
            self._validate_config()

        self._loaded = True
        logger.info(f"Configuration loaded for environment: {self.environment}")

    def _load_from_file(self) -> None:
        """Load configuration from the appropriate config file."""
        config_file = self.config_dir / f"config.{self.environment}.yaml"

        if not config_file.exists():
            logger.warning(f"Configuration file not found: {config_file}")
            return

        try:
            with open(config_file, "r") as f:
                file_config = yaml.safe_load(f)

            if file_config:
                # Update configuration with file values
                self._update_nested_dict(self._config, file_config)
                logger.debug(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Get all environment variables with the specified prefix
        env_vars = {k: v for k, v in os.environ.items() if k.startswith(self.env_prefix)}

        for key, value in env_vars.items():
            # Remove prefix and convert to lowercase
            config_key = key[len(self.env_prefix):].lower()

            # Handle nested keys (e.g., REDIS_HOST -> redis.host)
            if "_" in config_key:
                parts = config_key.split("_")
                current = self._config

                # Navigate to the nested dictionary
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Set the value in the nested dictionary
                current[parts[-1]] = self._parse_env_value(value)
            else:
                # Set top-level key
                self._config[config_key] = self._parse_env_value(value)

        logger.debug(f"Loaded {len(env_vars)} configuration values from environment variables")

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to the appropriate type."""
        # Try to parse as JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Handle boolean values
            if value.lower() in ("true", "yes", "1"):
                return True
            elif value.lower() in ("false", "no", "0"):
                return False

            # Handle numeric values
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                # Return as string
                return value

    def _update_nested_dict(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Update a nested dictionary with values from another dictionary."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # Recursively update nested dictionaries
                self._update_nested_dict(target[key], value)
            else:
                # Update or add the value
                target[key] = value

    def _validate_config(self) -> None:
        """Validate the configuration against schemas."""
        try:
            self.validator.validate(self._config)
            logger.debug("Configuration validation successful")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (dot notation for nested keys)
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        if not self._loaded:
            self.load()

        # Handle nested keys (e.g., "redis.host")
        if "." in key:
            parts = key.split(".")
            current = self._config

            # Navigate to the nested value
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return default
                current = current[part]

            return current

        # Handle top-level keys
        return self._config.get(key, default)

    def set(self, key: str, value: Any, persist: bool = False) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (dot notation for nested keys)
            value: Configuration value
            persist: Whether to persist the change to the config file
        """
        if not self._loaded:
            self.load()

        # Handle nested keys (e.g., "redis.host")
        if "." in key:
            parts = key.split(".")
            current = self._config

            # Navigate to the nested dictionary
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value in the nested dictionary
            current[parts[-1]] = value
        else:
            # Set top-level key
            self._config[key] = value

        # Validate the updated configuration
        if self.validate:
            self._validate_config()

        # Persist the change if requested
        if persist:
            self._persist_changes()

        logger.debug(f"Configuration updated: {key} = {value}")

    def _persist_changes(self) -> None:
        """Persist configuration changes to the config file."""
        config_file = self.config_dir / f"config.{self.environment}.yaml"

        try:
            with open(config_file, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)

            logger.info(f"Configuration persisted to {config_file}")
        except Exception as e:
            logger.error(f"Failed to persist configuration to {config_file}: {e}")

    def reload(self) -> None:
        """Reload configuration from all sources."""
        self.load(reload=True)
        logger.info("Configuration reloaded")

    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary."""
        if not self._loaded:
            self.load()

        return self._config.copy()
```

#### 2. Configuration Validators

```python
import logging
from typing import Any, Dict
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Import schema models
from .schemas.app_schema import AppConfig
from .schemas.redis_schema import RedisConfig
from .schemas.rabbitmq_schema import RabbitMQConfig
from .schemas.telegram_schema import TelegramConfig

class ConfigValidator:
    """
    Validates configuration against predefined schemas.

    This class uses Pydantic models to validate configuration
    parameters against schemas, ensuring type safety and
    required fields.
    """

    def __init__(self):
        """Initialize the configuration validator."""
        self.schemas = {
            "app": AppConfig,
            "redis": RedisConfig,
            "rabbitmq": RabbitMQConfig,
            "telegram": TelegramConfig
        }

    def validate(self, config: Dict[str, Any]) -> None:
        """
        Validate the configuration against schemas.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValidationError: If validation fails
        """
        errors = []

        # Validate each section against its schema
        for section, schema in self.schemas.items():
            if section in config:
                try:
                    # Create a model instance to validate
                    schema(**config[section])
                except ValidationError as e:
                    errors.append(f"Validation error in {section} section: {e}")

        # Raise an exception if there are validation errors
        if errors:
            error_message = "\n".join(errors)
            logger.error(f"Configuration validation failed:\n{error_message}")
            raise ValidationError(error_message, self.__class__)
```

#### 3. Schema Definitions

Example schema for Redis configuration:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict, Any

class RedisConfig(BaseModel):
    """Schema for Redis configuration."""

    host: str = Field(default="localhost", description="Redis server hostname")
    port: int = Field(default=6379, description="Redis server port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")

    # Connection pool settings
    max_connections: int = Field(default=10, description="Maximum number of connections in the pool")
    min_connections: int = Field(default=1, description="Minimum number of connections in the pool")

    # Timeout settings
    socket_timeout: float = Field(default=5.0, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(default=1.0, description="Socket connect timeout in seconds")

    # Retry settings
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retry attempts in seconds")

    # High availability settings
    sentinel_master: Optional[str] = Field(default=None, description="Redis Sentinel master name")
    sentinel_nodes: Optional[List[str]] = Field(default=None, description="Redis Sentinel nodes")

    # Cluster settings
    cluster_mode: bool = Field(default=False, description="Enable Redis Cluster mode")

    # SSL settings
    ssl: bool = Field(default=False, description="Enable SSL")
    ssl_cert_reqs: Optional[str] = Field(default=None, description="SSL certificate requirements")
    ssl_ca_certs: Optional[str] = Field(default=None, description="SSL CA certificates file path")
```

#### 4. Default Configuration

```python
"""Default configuration values for the Dmarket Telegram Bot."""

DEFAULT_CONFIG = {
    "app": {
        "name": "Dmarket Telegram Bot",
        "version": "1.0.0",
        "debug": False,
        "log_level": "INFO",
        "timezone": "UTC"
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "max_connections": 10,
        "retry_attempts": 3,
        "retry_delay": 1.0
    },
    "rabbitmq": {
        "host": "localhost",
        "port": 5672,
        "user": "guest",
        "password": "guest",
        "virtual_host": "/",
        "connection_name": "dmarket_bot",
        "heartbeat": 60,
        "connection_timeout": 10.0,
        "retry_attempts": 3,
        "retry_delay": 1.0,
        "channel_pool_size": 5
    },
    "telegram": {
        "api_token": "",
        "whitelist": [],
        "polling_timeout": 30,
        "webhook_enabled": False,
        "webhook_url": "",
        "webhook_port": 8443
    },
    "dmarket": {
        "api_url": "https://api.dmarket.com",
        "commission_percent": 7.0,
        "profit_threshold_usd": 0.0,
        "batch_size": 100,
        "request_timeout": 30.0,
        "max_retries": 3,
        "retry_delay": 1.0
    },
    "monitoring": {
        "enabled": True,
        "port": 8080,
        "path": "/metrics",
        "health_check_interval": 60
    },
    "storage": {
        "ttl_seconds": 3600,
        "prefix": "dmarket:items"
    }
}
```

### 3. Sample Configuration Files

#### config.dev.yaml
```yaml
app:
  debug: true
  log_level: DEBUG

redis:
  host: localhost
  port: 6379
  db: 0

rabbitmq:
  host: localhost
  port: 5672
  user: guest
  password: guest

telegram:
  api_token: "your_dev_token_here"
  whitelist: [123456789]

dmarket:
  profit_threshold_usd: -30.0
  batch_size: 50
```

#### config.prod.yaml
```yaml
app:
  debug: false
  log_level: INFO

redis:
  host: redis.production.internal
  port: 6379
  db: 0
  max_connections: 20
  retry_attempts: 5

rabbitmq:
  host: rabbitmq.production.internal
  port: 5672
  user: dmarket_user
  password: strong_password
  virtual_host: /production
  channel_pool_size: 10

telegram:
  api_token: "your_prod_token_here"
  whitelist: [123456789, 987654321]
  webhook_enabled: true
  webhook_url: "https://your-bot-domain.com/webhook"
  webhook_port: 8443

dmarket:
  profit_threshold_usd: -10.0
  batch_size: 100
  request_timeout: 60.0
```

### 4. Integration with Existing Code

#### Environment Variables

Replace the current environment variable loading with the new configuration system:

```python
# Old approach
from dotenv import load_dotenv

load_dotenv("../worker.dev.env")

LOG_LEVEL = get_log_level()
RABBITMQ_HOST = get_rabbitmq_host()
RABBITMQ_PORT = get_rabbitmq_port()
# ... more variables ...

# New approach
from config import config_manager

# Initialize the configuration manager
config = config_manager.ConfigManager()
config.load()

# Get configuration values
LOG_LEVEL = config.get("app.log_level")
RABBITMQ_HOST = config.get("rabbitmq.host")
RABBITMQ_PORT = config.get("rabbitmq.port")
```

#### Worker Module Example

```python
"""
DMarket Worker Module

This module serves as the main worker for processing DMarket data.
It is responsible for:
1. Retrieving individual item data from the RabbitMQ queue ('dmarket_raw_items_queue')
2. Storing item data in Redis

Requirements:
- Configured RabbitMQ instance
- Configured Redis instance

The worker continuously listens for messages on the queue, processes them,
and stores the results in Redis for later retrieval by the Telegram bot.
"""

import asyncio
import logging
from typing import Optional

import aio_pika  # Library for RabbitMQ interaction

# Import the configuration manager
from config import config_manager

# Initialize the configuration manager
config = config_manager.ConfigManager()
config.load()

# Import connectors for external services
from common.rabbitmq_connector import RabbitMQConnector
from common.redis_connector import RedisConnector
from price_monitoring.logs import setup_logging

# Import the DMarket item model for deserialization
from price_monitoring.models.dmarket import DMarketItem
# Import the queue name constant
from price_monitoring.queues.rabbitmq.raw_items_queue import DMARKET_RAW_ITEMS_QUEUE_NAME
# Import storage class for Redis operations
from price_monitoring.storage.dmarket import DMarketStorage

# Set up logging with the configured log level
LOG_LEVEL = config.get("app.log_level", "INFO")
setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

async def process_raw_item_message(message: aio_pika.IncomingMessage, storage: DMarketStorage) -> None:
    """
    Process a raw item message from the RabbitMQ queue.

    This function deserializes the message body into a DMarketItem object
    and saves it to Redis using the provided storage instance.

    The message is automatically acknowledged when the processing is complete
    or rejected if an exception occurs during processing.

    Args:
        message: The incoming RabbitMQ message containing serialized item data
        storage: DMarketStorage instance for saving the item to Redis

    Returns:
        None

    Raises:
        Exception: Logs but doesn't propagate exceptions to allow continuous operation
    """
    async with message.process():  # Acknowledge message upon successful processing
        try:
            # Deserialize the message body into a DMarketItem object
            item = DMarketItem.load_bytes(message.body)
            logger.debug(f"Received item: {item.item_id} - {item.title}")

            # Save the item to Redis
            await storage.save_item(item)
            logger.info(f"Successfully saved item {item.item_id} ({item.title}) to Redis.")
        except Exception as e:
            # Log the error and truncate the message body to avoid flooding the logs
            logger.error(f"Failed to process message: {e}. Message body (first 100 bytes): {message.body[:100]}...")
            # Consider moving to a dead-letter queue instead of just logging


async def main() -> None:
    """
    Main function for running and managing the DMarket worker.

    This function performs the following actions:
    1. Initializes connections to RabbitMQ and Redis
    2. Creates a DMarketStorage instance for Redis operations
    3. Sets up listening on the 'dmarket_raw_items_queue' queue
    4. Processes incoming messages (deserializes and saves to Redis)
    5. Ensures proper cleanup of resources on shutdown

    The worker runs indefinitely until interrupted or an unrecoverable error occurs.

    Returns:
        None
    """
    logger.info("Starting DMarket Worker...")

    # Initialize RabbitMQ connector with connection details from configuration
    rabbitmq_connector = RabbitMQConnector(
        host=config.get("rabbitmq.host"),
        port=str(config.get("rabbitmq.port")),
        user=config.get("rabbitmq.user"),
        password=config.get("rabbitmq.password"),
        virtual_host=config.get("rabbitmq.virtual_host"),
    )

    # Initialize Redis connector with connection details from configuration
    redis_connector = RedisConnector(
        host=config.get("redis.host"), 
        port=int(config.get("redis.port")), 
        db=int(config.get("redis.db"))
    )

    # Initialize variables for resources that need to be cleaned up
    channel: Optional[aio_pika.Channel] = None
    redis_client = None

    try:
        # Connect to RabbitMQ and create a channel
        connection = await rabbitmq_connector.connect()
        channel = await connection.channel()

        # Set prefetch count to limit the number of unacknowledged messages
        # This prevents the worker from being overwhelmed with too many messages
        await channel.set_qos(prefetch_count=config.get("rabbitmq.prefetch_count", 10))

        # Declare the queue to ensure it exists
        # The durable=True parameter ensures the queue survives broker restarts
        queue = await channel.declare_queue(DMARKET_RAW_ITEMS_QUEUE_NAME, durable=True)

        # Connect to Redis and create a storage instance
        redis_client = await redis_connector.get_client()
        dmarket_storage = DMarketStorage(
            redis_client=redis_client,
            prefix=config.get("storage.prefix", "dmarket:items"),
            ttl_seconds=config.get("storage.ttl_seconds", 3600)
        )

        logger.info(f"Worker is listening for messages on queue '{DMARKET_RAW_ITEMS_QUEUE_NAME}'...")

        # Consume messages from the queue in an infinite loop
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await process_raw_item_message(message, dmarket_storage)

    except asyncio.CancelledError:
        # Handle graceful cancellation (e.g., when the event loop is stopped)
        logger.info("Worker task cancelled.")
    except Exception as e:
        # Log any unexpected errors
        logger.exception(f"An unexpected error occurred in the worker main loop: {e}")
    finally:
        # Ensure proper cleanup of resources
        logger.info("Shutting down DMarket Worker...")

        # Close the RabbitMQ channel if it exists and is not already closed
        if channel and not channel.is_closed:
            await channel.close()
            logger.info("RabbitMQ channel closed.")

        # Close the RabbitMQ connection
        if rabbitmq_connector:
            await rabbitmq_connector.close()

        # Close the Redis connection
        if redis_connector:
            await redis_connector.close()

        logger.info("DMarket Worker stopped.")


if __name__ == "__main__":
    try:
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        logger.info("Worker stopped by user.")
```

### 5. Configuration Service for Runtime Updates

For advanced use cases, we can implement a configuration service that allows runtime updates to configuration parameters:

```python
import asyncio
import logging
from typing import Any, Dict, Optional
from aiohttp import web

from config import config_manager

logger = logging.getLogger(__name__)

class ConfigService:
    """
    Service for managing configuration at runtime.

    This service provides an HTTP API for viewing and updating
    configuration parameters at runtime without restarting services.
    """

    def __init__(self, config: config_manager.ConfigManager, host: str = "localhost", port: int = 8081):
        """
        Initialize the configuration service.

        Args:
            config: Configuration manager instance
            host: Host to bind the HTTP server
            port: Port to bind the HTTP server
        """
        self.config = config
        self.host = host
        self.port = port
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self) -> None:
        """Set up HTTP routes for the configuration service."""
        self.app.router.add_get("/config", self.get_config)
        self.app.router.add_get("/config/{key}", self.get_config_key)
        self.app.router.add_post("/config/{key}", self.set_config_key)
        self.app.router.add_post("/config/reload", self.reload_config)

    async def get_config(self, request: web.Request) -> web.Response:
        """
        Get the entire configuration.

        Args:
            request: HTTP request

        Returns:
            HTTP response with the configuration
        """
        # Mask sensitive values
        config = self.config.get_all()
        masked_config = self._mask_sensitive_values(config)

        return web.json_response(masked_config)

    async def get_config_key(self, request: web.Request) -> web.Response:
        """
        Get a specific configuration value.

        Args:
            request: HTTP request with key parameter

        Returns:
            HTTP response with the configuration value
        """
        key = request.match_info["key"]
        value = self.config.get(key)

        if value is None:
            return web.json_response({"error": f"Configuration key not found: {key}"}, status=404)

        # Mask sensitive values
        if self._is_sensitive_key(key):
            value = "********"

        return web.json_response({key: value})

    async def set_config_key(self, request: web.Request) -> web.Response:
        """
        Set a specific configuration value.

        Args:
            request: HTTP request with key parameter and JSON body

        Returns:
            HTTP response with the updated configuration value
        """
        key = request.match_info["key"]

        try:
            body = await request.json()
            if "value" not in body:
                return web.json_response({"error": "Missing 'value' in request body"}, status=400)

            value = body["value"]
            persist = body.get("persist", False)

            self.config.set(key, value, persist=persist)

            return web.json_response({"success": True, "key": key, "updated": True})
        except Exception as e:
            logger.error(f"Failed to update configuration key {key}: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def reload_config(self, request: web.Request) -> web.Response:
        """
        Reload the configuration from all sources.

        Args:
            request: HTTP request

        Returns:
            HTTP response with reload status
        """
        try:
            self.config.reload()
            return web.json_response({"success": True, "reloaded": True})
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return web.json_response({"error": str(e)}, status=500)

    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a configuration key contains sensitive information."""
        sensitive_patterns = ["password", "token", "secret", "key"]
        return any(pattern in key.lower() for pattern in sensitive_patterns)

    def _mask_sensitive_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive values in the configuration."""
        masked_config = {}

        for key, value in config.items():
            if isinstance(value, dict):
                masked_config[key] = self._mask_sensitive_values(value)
            elif self._is_sensitive_key(key):
                masked_config[key] = "********"
            else:
                masked_config[key] = value

        return masked_config

    async def start(self) -> None:
        """Start the configuration service."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"Configuration service started at http://{self.host}:{self.port}")

        return runner
```

## Usage Examples

### Basic Configuration Usage

```python
from config import config_manager

# Initialize the configuration manager
config = config_manager.ConfigManager()
config.load()

# Get configuration values
redis_host = config.get("redis.host")
redis_port = config.get("redis.port")
log_level = config.get("app.log_level")

# Get a value with a default
debug_mode = config.get("app.debug", False)

# Set a configuration value
config.set("dmarket.profit_threshold_usd", -20.0)

# Set a configuration value and persist it to the config file
config.set("telegram.polling_timeout", 60, persist=True)

# Reload configuration from all sources
config.reload()
```

### Runtime Configuration Updates

```python
from config import config_manager
from config.config_service import ConfigService

# Initialize the configuration manager
config = config_manager.ConfigManager()
config.load()

# Create and start the configuration service
config_service = ConfigService(config, host="0.0.0.0", port=8081)
await config_service.start()

# Now you can update configuration at runtime via HTTP API:
# GET /config - Get all configuration
# GET /config/redis.host - Get specific configuration value
# POST /config/dmarket.profit_threshold_usd - Update configuration value
# POST /config/reload - Reload configuration from all sources
```

### Environment Variables

You can override any configuration value using environment variables:

```bash
# Set environment variables
DMARKET_APP_DEBUG=true
DMARKET_REDIS_HOST=redis.example.com
DMARKET_REDIS_PORT=6380
DMARKET_TELEGRAM_API_TOKEN=your_token_here
DMARKET_TELEGRAM_WHITELIST=[123456789,987654321]
DMARKET_DMARKET_PROFIT_THRESHOLD_USD=-15.0

# Run the application
python worker.py
```

## Implementation Plan

1. **Phase 1: Setup Configuration Infrastructure**
   - Create the config module with ConfigManager and validators
   - Set up the config_files directory structure
   - Create initial configuration schemas

2. **Phase 2: Migrate Environment Variables**
   - Replace dotenv loading with ConfigManager
   - Update all modules to use the new configuration system
   - Create environment-specific configuration files

3. **Phase 3: Implement Configuration Validation**
   - Create schema definitions for all configuration sections
   - Implement validation logic
   - Add error handling for invalid configurations

4. **Phase 4: Add Runtime Configuration Updates**
   - Implement the ConfigService for HTTP API
   - Add support for hot reloading configuration
   - Implement secure handling of sensitive configuration values

5. **Phase 5: Testing and Documentation**
   - Test the configuration system with different environments
   - Document the configuration workflow for contributors
   - Create guidelines for adding new configuration parameters

## Benefits

Implementing this configuration management system will:

1. Centralize all configuration parameters in one place
2. Provide type safety and validation for configuration values
3. Support different environments (development, testing, production)
4. Allow runtime updates to configuration without service restarts
5. Secure sensitive configuration data
6. Make the project more maintainable and easier to configure
7. Address one of the improvement areas identified in the repository analysis (7.5/10)

## Conclusion

The proposed configuration management system provides a comprehensive solution for centralizing and managing configuration in the Dmarket Telegram Bot project. By implementing this system, we can significantly improve the maintainability and flexibility of the application, addressing one of the key improvement areas identified in the repository analysis.

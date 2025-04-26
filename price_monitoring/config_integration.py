"""Configuration integration module for Dmarket Telegram Bot.

This module provides utility functions and examples for integrating
the new centralized configuration system with existing components.
"""

import logging
from typing import Any

# Import the configuration manager
from config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ConfigurationIntegrator:
    """Helper class for integrating the new configuration system with existing components.

    This class provides methods for migrating from environment variables and
    hardcoded values to the centralized configuration system.
    """

    def __init__(self, config_manager: ConfigManager):
        """Initialize the configuration integrator.

        Args:
            config_manager: The configuration manager instance
        """
        self.config = config_manager

    def get_redis_config(self) -> dict[str, Any]:
        """Get Redis configuration from the centralized configuration system.

        Returns:
            Dictionary with Redis configuration parameters
        """
        return {
            "host": self.config.get("redis.host", "localhost"),
            "port": self.config.get("redis.port", 6379),
            "db": self.config.get("redis.db", 0),
            "password": self.config.get("redis.password"),
            "max_connections": self.config.get("redis.max_connections", 10),
            "socket_timeout": self.config.get("redis.socket_timeout", 5.0),
            "retry_attempts": self.config.get("redis.retry_attempts", 3),
            "retry_delay": self.config.get("redis.retry_delay", 1.0),
        }

    def get_rabbitmq_config(self) -> dict[str, Any]:
        """Get RabbitMQ configuration from the centralized configuration system.

        Returns:
            Dictionary with RabbitMQ configuration parameters
        """
        return {
            "host": self.config.get("rabbitmq.host", "localhost"),
            "port": self.config.get("rabbitmq.port", 5672),
            "user": self.config.get("rabbitmq.user", "guest"),
            "password": self.config.get("rabbitmq.password", "guest"),
            "virtual_host": self.config.get("rabbitmq.virtual_host", "/"),
            "connection_name": self.config.get("rabbitmq.connection_name", "dmarket_bot"),
            "heartbeat": self.config.get("rabbitmq.heartbeat", 60),
            "connection_timeout": self.config.get("rabbitmq.connection_timeout", 10.0),
            "retry_attempts": self.config.get("rabbitmq.retry_attempts", 3),
            "retry_delay": self.config.get("rabbitmq.retry_delay", 1.0),
            "channel_pool_size": self.config.get("rabbitmq.channel_pool_size", 5),
            "prefetch_count": self.config.get("rabbitmq.prefetch_count", 10),
        }

    def get_telegram_config(self) -> dict[str, Any]:
        """Get Telegram configuration from the centralized configuration system.

        Returns:
            Dictionary with Telegram configuration parameters
        """
        return {
            "api_token": self.config.get("telegram.api_token", ""),
            "whitelist": self.config.get("telegram.whitelist", []),
            "polling_timeout": self.config.get("telegram.polling_timeout", 30),
            "webhook_enabled": self.config.get("telegram.webhook_enabled", False),
            "webhook_url": self.config.get("telegram.webhook_url", ""),
            "webhook_port": self.config.get("telegram.webhook_port", 8443),
        }

    def get_dmarket_config(self) -> dict[str, Any]:
        """Get DMarket configuration from the centralized configuration system.

        Returns:
            Dictionary with DMarket configuration parameters
        """
        return {
            "api_url": self.config.get("dmarket.api_url", "https://api.dmarket.com"),
            "commission_percent": self.config.get("dmarket.commission_percent", 7.0),
            "profit_threshold_usd": self.config.get("dmarket.profit_threshold_usd", 0.0),
            "batch_size": self.config.get("dmarket.batch_size", 100),
            "request_timeout": self.config.get("dmarket.request_timeout", 30.0),
            "max_retries": self.config.get("dmarket.max_retries", 3),
            "retry_delay": self.config.get("dmarket.retry_delay", 1.0),
        }

    def get_storage_config(self) -> dict[str, Any]:
        """Get storage configuration from the centralized configuration system.

        Returns:
            Dictionary with storage configuration parameters
        """
        return {
            "ttl_seconds": self.config.get("storage.ttl_seconds", 3600),
            "prefix": self.config.get("storage.prefix", "dmarket:items"),
            "compression_enabled": self.config.get("storage.compression_enabled", True),
            "compression_algorithm": self.config.get("storage.compression_algorithm", "gzip"),
            "serialization_format": self.config.get("storage.serialization_format", "json"),
            "compression_level": self.config.get("storage.compression_level", 6),
            "min_size_for_compression": self.config.get("storage.min_size_for_compression", 1024),
            "batch_size": self.config.get("storage.batch_size", 100),
            "max_concurrency": self.config.get("storage.max_concurrency", 5),
        }

    def get_monitoring_config(self) -> dict[str, Any]:
        """Get monitoring configuration from the centralized configuration system.

        Returns:
            Dictionary with monitoring configuration parameters
        """
        return {
            "enabled": self.config.get("monitoring.enabled", True),
            "port": self.config.get("monitoring.port", 8080),
            "path": self.config.get("monitoring.path", "/metrics"),
            "health_check_interval": self.config.get("monitoring.health_check_interval", 60),
        }

    def get_app_config(self) -> dict[str, Any]:
        """Get application configuration from the centralized configuration system.

        Returns:
            Dictionary with application configuration parameters
        """
        return {
            "name": self.config.get("app.name", "Dmarket Telegram Bot"),
            "version": self.config.get("app.version", "1.0.0"),
            "debug": self.config.get("app.debug", False),
            "log_level": self.config.get("app.log_level", "INFO"),
            "timezone": self.config.get("app.timezone", "UTC"),
        }

    def get_proxy_config(self) -> dict[str, Any]:
        """Get proxy configuration from the centralized configuration system.

        Returns:
            Dictionary with proxy configuration parameters
        """
        return {
            "enabled": self.config.get("proxy.enabled", False),
            "proxy_list_path": self.config.get("proxy.proxy_list_path", "proxies.txt"),
            "check_url": self.config.get("proxy.check_url", "https://api.dmarket.com"),
            "timeout": self.config.get("proxy.timeout", 10.0),
            "max_fails": self.config.get("proxy.max_fails", 3),
            "retry_delay": self.config.get("proxy.retry_delay", 60.0),
        }


# Example usage for different components


def configure_redis_connector(config_integrator: ConfigurationIntegrator):
    """Example of configuring Redis connector with the new configuration system.

    Args:
        config_integrator: Configuration integrator instance
    """
    from common.redis_connector import RedisConnector

    # Get Redis configuration
    redis_config = config_integrator.get_redis_config()

    # Create Redis connector
    redis_connector = RedisConnector(
        host=redis_config["host"],
        port=redis_config["port"],
        db=redis_config["db"],
        password=redis_config["password"],
    )

    return redis_connector


def configure_rabbitmq_connector(config_integrator: ConfigurationIntegrator):
    """Example of configuring RabbitMQ connector with the new configuration system.

    Args:
        config_integrator: Configuration integrator instance
    """
    from common.rabbitmq_connector import RabbitMQConnector

    # Get RabbitMQ configuration
    rabbitmq_config = config_integrator.get_rabbitmq_config()

    # Create RabbitMQ connector
    rabbitmq_connector = RabbitMQConnector(
        host=rabbitmq_config["host"],
        port=str(rabbitmq_config["port"]),
        user=rabbitmq_config["user"],
        password=rabbitmq_config["password"],
        virtual_host=rabbitmq_config["virtual_host"],
    )

    return rabbitmq_connector


def configure_dmarket_storage(config_integrator: ConfigurationIntegrator, redis_client):
    """Example of configuring DMarket storage with the new configuration system.

    Args:
        config_integrator: Configuration integrator instance
        redis_client: Redis client instance
    """
    from price_monitoring.storage.dmarket import DMarketStorage
    from price_monitoring.storage.integration import create_enhanced_storage

    # Get storage configuration
    storage_config = config_integrator.get_storage_config()

    # Create original storage
    original_storage = DMarketStorage(
        redis_client=redis_client,
        prefix=storage_config["prefix"],
        ttl_seconds=storage_config["ttl_seconds"],
    )

    # Create enhanced storage
    enhanced_storage = create_enhanced_storage(
        original_storage=original_storage,
        compression_enabled=storage_config["compression_enabled"],
        compression_algorithm=storage_config["compression_algorithm"],
        serialization_format=storage_config["serialization_format"],
        compression_level=storage_config["compression_level"],
        min_size_for_compression=storage_config["min_size_for_compression"],
        batch_size=storage_config["batch_size"],
        max_concurrency=storage_config["max_concurrency"],
    )

    return enhanced_storage


def configure_dmarket_parser(config_integrator: ConfigurationIntegrator):
    """Example of configuring DMarket parser with the new configuration system.

    Args:
        config_integrator: Configuration integrator instance
    """
    from price_monitoring.parsers.dmarket.dmarket_parser import DMarketParser

    # Get DMarket configuration
    dmarket_config = config_integrator.get_dmarket_config()

    # Create DMarket parser
    dmarket_parser = DMarketParser(
        api_url=dmarket_config["api_url"],
        request_timeout=dmarket_config["request_timeout"],
        max_retries=dmarket_config["max_retries"],
        retry_delay=dmarket_config["retry_delay"],
    )

    return dmarket_parser


def configure_telegram_bot(config_integrator: ConfigurationIntegrator):
    """Example of configuring Telegram bot with the new configuration system.

    Args:
        config_integrator: Configuration integrator instance
    """
    from price_monitoring.telegram.bot.bot import create_bot

    # Get Telegram configuration
    telegram_config = config_integrator.get_telegram_config()

    # Create Telegram bot
    bot = create_bot(token=telegram_config["api_token"], whitelist=telegram_config["whitelist"])

    return bot


def configure_proxy_manager(config_integrator: ConfigurationIntegrator):
    """Example of configuring proxy manager with the new configuration system.

    Args:
        config_integrator: Configuration integrator instance
    """
    from proxy_http.proxy import ProxyManager

    # Get proxy configuration
    proxy_config = config_integrator.get_proxy_config()

    # Create proxy manager
    proxy_manager = ProxyManager(
        proxy_list_path=proxy_config["proxy_list_path"],
        check_url=proxy_config["check_url"],
        timeout=proxy_config["timeout"],
        max_fails=proxy_config["max_fails"],
        retry_delay=proxy_config["retry_delay"],
    )

    return proxy_manager


def configure_logging(config_integrator: ConfigurationIntegrator):
    """Example of configuring logging with the new configuration system.

    Args:
        config_integrator: Configuration integrator instance
    """
    from price_monitoring.logs import setup_logging

    # Get application configuration
    app_config = config_integrator.get_app_config()

    # Set up logging
    setup_logging(app_config["log_level"])


# Main function to demonstrate configuration integration
async def main():
    """Main function to demonstrate configuration integration."""
    # Initialize configuration manager
    config_manager = ConfigManager()
    config_manager.load()

    # Create configuration integrator
    config_integrator = ConfigurationIntegrator(config_manager)

    # Configure logging
    configure_logging(config_integrator)

    # Configure Redis connector
    redis_connector = configure_redis_connector(config_integrator)
    redis_client = await redis_connector.get_client()

    # Configure RabbitMQ connector
    rabbitmq_connector = configure_rabbitmq_connector(config_integrator)
    await rabbitmq_connector.connect()

    # Configure DMarket storage
    configure_dmarket_storage(config_integrator, redis_client)

    # Configure DMarket parser
    configure_dmarket_parser(config_integrator)

    # Configure Telegram bot
    configure_telegram_bot(config_integrator)

    # Configure proxy manager
    configure_proxy_manager(config_integrator)

    # Log configuration status
    logger.info("All components configured with the new configuration system")

    # Clean up resources
    await redis_connector.close()
    await rabbitmq_connector.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

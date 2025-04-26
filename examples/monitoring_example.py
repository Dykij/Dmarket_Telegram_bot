"""Example script demonstrating how to use the monitoring and health check features.

This script shows how to:
1. Set up health checks for various components
2. Collect metrics for monitoring
3. Start a monitoring server to expose health and metrics endpoints

Usage:
    python examples/monitoring_example.py
"""

import asyncio
import contextlib
import logging
import sys
import time
from typing import Any

from common.rabbitmq_connector import RabbitMQConnector
from common.redis_connector import RedisConnector
from monitoring.health import (HealthCheck, MetricsCollector, check_dmarket_api,
                               check_rabbitmq_connection, check_redis_connection)
from monitoring.server import start_monitoring_server
from price_monitoring.parsers.dmarket.client import DMarketClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def simulate_api_requests(metrics: MetricsCollector) -> None:
    """Simulate API requests to demonstrate metrics collection.

    Args:
        metrics: MetricsCollector instance
    """
    while True:
        # Simulate API request
        start_time = time.time()

        # Increment request counter
        metrics.increment("api_requests_total")

        # Simulate request processing time (between 0.1 and 0.5 seconds)
        processing_time = 0.1 + (time.time() % 0.4)
        await asyncio.sleep(processing_time)

        # Record request duration
        duration = time.time() - start_time
        metrics.observe("request_duration_seconds", duration)

        # Randomly simulate errors (10% chance)
        if time.time() % 10 < 1:
            metrics.increment("api_errors_total")

        # Update active connections gauge
        active_connections = int(time.time() % 20)  # 0-19 connections
        metrics.set_gauge("active_connections", active_connections)

        # Wait before next request
        await asyncio.sleep(1.0)


async def custom_health_check() -> dict[str, Any]:
    """Custom health check function example.

    Returns:
        Health check result
    """
    # Simulate some health check logic
    is_healthy = (
        time.time() % 30
    ) > 5  # Healthy most of the time, unhealthy for 5 seconds every 30 seconds

    if is_healthy:
        return {
            "status": "healthy",
            "details": {
                "uptime": time.time(),
                "memory_usage_mb": 100 + (time.time() % 50),  # Simulate memory usage
            },
        }
    else:
        return {
            "status": "degraded",
            "details": {
                "uptime": time.time(),
                "memory_usage_mb": 100 + (time.time() % 50),
                "reason": "Simulated degradation for demonstration",
            },
        }


async def main() -> None:
    """Main function to run the monitoring example."""
    logger.info("Starting monitoring example...")

    # Create health check and metrics instances
    health_check = HealthCheck()
    metrics = MetricsCollector()

    # Initialize components (with dummy credentials for demonstration)
    try:
        # Redis connection
        redis_connector = RedisConnector(
            host="localhost",
            port=6379,
            db=0,
        )
        redis_client = await redis_connector.get_client()

        # RabbitMQ connection
        rabbitmq_connector = RabbitMQConnector(
            host="localhost",
            port="5672",
            user="guest",
            password="guest",
            virtual_host="/",
        )

        # DMarket client
        dmarket_client = DMarketClient(
            api_key="dummy_api_key",
            secret_key="dummy_secret_key",
            public_key="dummy_public_key",
        )

        # Register health checks
        health_check.register_check("redis", lambda: check_redis_connection(redis_client))
        health_check.register_check(
            "rabbitmq", lambda: check_rabbitmq_connection(rabbitmq_connector)
        )
        health_check.register_check("dmarket_api", lambda: check_dmarket_api(dmarket_client))
        health_check.register_check("custom", custom_health_check)

        # Start simulating API requests in the background
        asyncio.create_task(simulate_api_requests(metrics))

        # Start the monitoring server
        await start_monitoring_server(
            health_check=health_check,
            metrics=metrics,
            host="localhost",
            port=8080,
        )

        # Keep the application running
        logger.info("Monitoring server started at http://localhost:8080")
        logger.info("Health check endpoint: http://localhost:8080/health")
        logger.info("Metrics endpoint: http://localhost:8080/metrics")

        # Wait indefinitely
        while True:
            await asyncio.sleep(3600)

    except KeyboardInterrupt:
        logger.info("Monitoring example stopped by user.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        # Clean up resources
        logger.info("Cleaning up resources...")
        with contextlib.suppress(Exception):
            await redis_connector.close()
        with contextlib.suppress(Exception):
            await rabbitmq_connector.close()
        with contextlib.suppress(Exception):
            await dmarket_client.close_session()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Monitoring example stopped by user.")

#!/usr/bin/env python
"""Service Health Check Script.

This script checks if Redis, RabbitMQ, and other required
services are running and accessible.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

try:
    import aio_pika
    import redis.asyncio as redis
    from dotenv import load_dotenv
except ImportError:
    print("Required packages not found. Please install dependencies with:")
    print("poetry install")
    sys.exit(1)

# Default configuration
DEFAULT_CONFIG = {
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_DB": "0",
    "REDIS_PASSWORD": "",
    "RABBITMQ_HOST": "localhost",
    "RABBITMQ_PORT": "5672",
    "RABBITMQ_USER": "guest",
    "RABBITMQ_PASSWORD": "guest",
    "RABBITMQ_VIRTUAL_HOST": "/",
}


def load_env_config() -> Dict[str, str]:
    """Load configuration from environment variables or .env file."""
    # Try to load .env file
    load_dotenv()

    # Create configuration from environment variables
    config = {}
    for key, default in DEFAULT_CONFIG.items():
        config[key] = os.getenv(key, default)

    return config


async def check_redis(config: Dict[str, str]) -> Tuple[bool, str]:
    """Check if Redis is accessible."""
    try:
        # Create Redis client
        r = redis.Redis(
            host=config["REDIS_HOST"],
            port=int(config["REDIS_PORT"]),
            db=int(config["REDIS_DB"]),
            password=config["REDIS_PASSWORD"] or None,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

        # Try to ping Redis
        await r.ping()

        # Set and get a test value
        test_key = f"health_check_{datetime.now().timestamp()}"
        await r.set(test_key, "OK", ex=60)  # expires in 60 seconds
        result = await r.get(test_key)

        if result != b"OK":
            return False, f"Redis test key validation failed. Expected 'OK', got: {result}"

        # Get Redis info for detailed status
        info = await r.info()
        version = info.get("redis_version", "unknown")
        memory = info.get("used_memory_human", "unknown")

        await r.close()

        return True, f"Redis ({version}) is running. Memory usage: {memory}"
    except Exception as e:
        return False, f"Redis connection failed: {e!s}"


async def check_rabbitmq(config: Dict[str, str]) -> Tuple[bool, str]:
    """Check if RabbitMQ is accessible."""
    try:
        # Create connection string
        conn_str = (
            f"amqp://{config['RABBITMQ_USER']}:{config['RABBITMQ_PASSWORD']}@"
            f"{config['RABBITMQ_HOST']}:{config['RABBITMQ_PORT']}/"
            f"{config['RABBITMQ_VIRTUAL_HOST']}"
        )

        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(conn_str)

        # Create a channel and a temporary queue
        channel = await connection.channel()
        queue_name = f"health_check_{datetime.now().timestamp()}"
        queue = await channel.declare_queue(queue_name, auto_delete=True)

        # Publish and consume a test message
        test_message = f"Health check at {datetime.now().isoformat()}"
        await channel.default_exchange.publish(
            aio_pika.Message(body=test_message.encode()),
            routing_key=queue_name,
        )

        # Get the message back
        message = await queue.get(timeout=5)
        if message:
            await message.ack()
            received = message.body.decode()
            if received != test_message:
                return (
                    False,
                    f"RabbitMQ message content mismatch. Expected: {test_message}, Got: {received}",
                )
        else:
            return False, "RabbitMQ test message not received"

        # Close connection
        await connection.close()

        return True, "RabbitMQ is running and responsive"
    except Exception as e:
        return False, f"RabbitMQ connection failed: {e!s}"


async def run_health_checks() -> List[Dict]:
    """Run all health checks and return results."""
    config = load_env_config()
    results = []

    # Check Redis
    redis_ok, redis_message = await check_redis(config)
    results.append(
        {
            "service": "Redis",
            "status": "OK" if redis_ok else "FAIL",
            "message": redis_message,
        }
    )

    # Check RabbitMQ
    rabbitmq_ok, rabbitmq_message = await check_rabbitmq(config)
    results.append(
        {
            "service": "RabbitMQ",
            "status": "OK" if rabbitmq_ok else "FAIL",
            "message": rabbitmq_message,
        }
    )

    # Add more service checks here if needed

    return results


def print_results(results: List[Dict]) -> None:
    """Print health check results in a formatted way."""
    print("\n=== Service Health Check Results ===\n")

    all_ok = True
    for result in results:
        status_color = "\033[92m" if result["status"] == "OK" else "\033[91m"  # Green or Red
        reset_color = "\033[0m"

        print(f"{result['service']}: {status_color}{result['status']}{reset_color}")
        print(f"  {result['message']}")
        print()

        if result["status"] != "OK":
            all_ok = False

    if all_ok:
        print("\033[92mAll services are running correctly!\033[0m")
    else:
        print("\033[91mSome services have issues. Please check the details above.\033[0m")


async def main():
    """Main function."""
    try:
        print("Running service health checks...")
        results = await run_health_checks()
        print_results(results)

        # Exit with error code if any service is down
        if any(r["status"] != "OK" for r in results):
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nHealth check interrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"Error running health checks: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""Scheduler entry point for Dmarket Telegram Bot.

This script runs the scheduler that distributes parsing tasks
across multiple parser instances.
"""

import asyncio
import logging
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import contextlib

from common.redis_connector import RedisConnector
from scalability.work_distributor import WorkDistributor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the scheduler."""
    try:
        # Initialize Redis connector
        redis_connector = RedisConnector(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=os.environ.get("REDIS_PORT", "6379"),
            db=os.environ.get("REDIS_DB", "0"),
        )
        redis_client = await redis_connector.get_client()

        # Initialize work distributor
        distributor = WorkDistributor(
            redis_client=redis_client,
            default_interval=int(os.environ.get("PARSE_INTERVAL", "3600")),
        )

        # Schedule games
        game_ids = os.environ.get("GAME_IDS", "a8db,9a92,730").split(",")
        for i, game_id in enumerate(game_ids):
            await distributor.schedule_game(
                game_id=game_id.strip(),
                params={
                    "currency": os.environ.get("CURRENCY", "USD"),
                    "items_per_page": int(os.environ.get("ITEMS_PER_PAGE", "100")),
                    "api_request_delay": float(os.environ.get("API_REQUEST_DELAY", "1.0")),
                },
                interval=int(os.environ.get("PARSE_INTERVAL", "3600"))
                + i * 300,  # Stagger schedules
                priority=i % 10,  # Different priorities
            )

        # Run the scheduler
        logger.info("Starting scheduler loop")
        await distributor.run_scheduler(
            check_interval=int(os.environ.get("SCHEDULER_CHECK_INTERVAL", "60"))
        )

    except asyncio.CancelledError:
        logger.info("Scheduler cancelled")
    except Exception as e:
        logger.exception(f"Error in scheduler: {e}")
    finally:
        # Clean up
        with contextlib.suppress(Exception):
            await redis_connector.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")

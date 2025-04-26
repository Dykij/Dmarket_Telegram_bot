"""Work distribution system for Dmarket Telegram Bot.

This module manages the distribution of parsing tasks across multiple
parser instances, ensuring fair distribution and preventing duplicate work.
"""

import asyncio
import json
import logging
import time
from typing import Any, Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class WorkDistributor:
    """Work distributor for parsing tasks.

    This class manages the distribution of parsing tasks across multiple
    parser instances, ensuring fair distribution and preventing duplicate work.
    """

    def __init__(
        self,
        redis_client: Redis,
        work_queue_key: str = "dmarket:parser:work_queue",
        game_schedule_key: str = "dmarket:parser:game_schedule",
        default_interval: int = 3600,  # 1 hour
    ):
        """Initialize the work distributor.

        Args:
            redis_client: Redis client for coordination
            work_queue_key: Redis key for the work queue
            game_schedule_key: Redis key for game schedules
            default_interval: Default interval in seconds between parsing the same game
        """
        self.redis = redis_client
        self.work_queue_key = work_queue_key
        self.game_schedule_key = game_schedule_key
        self.default_interval = default_interval

    async def schedule_game(
        self,
        game_id: str,
        params: dict[str, Any],
        interval: Optional[int] = None,
        priority: int = 0,
    ) -> None:
        """Schedule a game for parsing.

        Args:
            game_id: ID of the game to parse
            params: Parameters for parsing
            interval: Interval in seconds between parsing (None = use default)
            priority: Priority (0-9, higher = more important)
        """
        interval = interval or self.default_interval

        # Store schedule information
        schedule_data = {
            "game_id": game_id,
            "params": params,
            "interval": interval,
            "priority": priority,
            "last_scheduled": time.time(),
            "next_scheduled": time.time() + interval,
        }

        await self.redis.hset(self.game_schedule_key, game_id, json.dumps(schedule_data))

        # Add to work queue
        await self.add_to_queue(game_id, params, priority)

        logger.info(f"Scheduled game {game_id} with interval {interval}s and priority {priority}")

    async def add_to_queue(self, game_id: str, params: dict[str, Any], priority: int = 0) -> None:
        """Add a game to the work queue.

        Args:
            game_id: ID of the game to parse
            params: Parameters for parsing
            priority: Priority (0-9, higher = more important)
        """
        work_item = {
            "game_id": game_id,
            "params": params,
            "priority": priority,
            "added_at": time.time(),
        }

        # Use priority queue (sorted set) with score = -priority
        # This ensures higher priority items come first
        await self.redis.zadd(self.work_queue_key, {json.dumps(work_item): -priority})

        logger.debug(f"Added game {game_id} to work queue with priority {priority}")

    async def get_next_work_item(self) -> Optional[dict[str, Any]]:
        """Get the next work item from the queue.

        Returns:
            Work item as a dictionary, or None if no work is available
        """
        # Get highest priority item (lowest score)
        result = await self.redis.zpopmin(self.work_queue_key)
        if not result:
            return None

        item_json, _ = result[0]
        try:
            return json.loads(item_json)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse work item: {item_json}")
            return None

    async def update_schedules(self) -> int:
        """Update schedules and add due games to the work queue.

        Returns:
            Number of games added to the queue
        """
        # Get all schedules
        schedules = await self.redis.hgetall(self.game_schedule_key)
        if not schedules:
            return 0

        current_time = time.time()
        added_count = 0

        for game_id, schedule_json in schedules.items():
            try:
                schedule = json.loads(schedule_json)

                # Check if it's time to schedule this game
                if schedule["next_scheduled"] <= current_time:
                    # Add to work queue
                    await self.add_to_queue(
                        game_id=schedule["game_id"],
                        params=schedule["params"],
                        priority=schedule["priority"],
                    )

                    # Update schedule
                    schedule["last_scheduled"] = current_time
                    schedule["next_scheduled"] = current_time + schedule["interval"]

                    await self.redis.hset(self.game_schedule_key, game_id, json.dumps(schedule))

                    added_count += 1
                    logger.debug(f"Scheduled game {game_id} for parsing")

            except Exception as e:
                logger.error(f"Error updating schedule for game {game_id}: {e}")

        logger.info(f"Added {added_count} games to the work queue")
        return added_count

    async def run_scheduler(self, check_interval: int = 60) -> None:
        """Run the scheduler loop.

        Args:
            check_interval: Interval in seconds between schedule checks
        """
        logger.info("Starting scheduler loop")

        try:
            while True:
                await self.update_schedules()
                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")

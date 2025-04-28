"""Module for retry functionality.

This module provides utilities for retrying operations with exponential backoff.
"""

import asyncio
import functools
import logging
import random
from typing import Any, Callable, TypeVar

from price_monitoring.exceptions import DMarketRateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions_to_retry: tuple = (Exception,),
    **kwargs: Any,
) -> Any:
    """Retry a function with exponential backoff.

    Args:
        func: The function to retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retries before giving up
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor by which the delay increases each retry
        exceptions_to_retry: Exception types to catch and retry on
        **kwargs: Keyword arguments for the function

    Returns:
        The return value of the function

    Raises:
        The last exception raised by the function if all retries fail
    """
    retries = 0
    delay = base_delay

    while True:
        try:
            return await func(*args, **kwargs)
        except DMarketRateLimitError as e:
            # Handle rate limit specifically with its retry_after value
            if retries >= max_retries:
                logger.error(f"Rate limit exceeded after {retries} retries - giving up. Error: {e}")
                raise

            retry_after = getattr(e, "retry_after", None) or delay
            logger.warning(
                f"Rate limit hit, retrying in {retry_after:.1f}s ({retries + 1}/{max_retries})"
            )
            await asyncio.sleep(retry_after)
            retries += 1
            # Stick with the server-provided retry_after instead of exponential backoff
        except exceptions_to_retry as e:
            if retries >= max_retries:
                logger.error(f"Function failed after {retries} retries - giving up. Error: {e}")
                raise

            # Add jitter to avoid thundering herd problem
            jitter = random.uniform(0.0, 0.1 * delay)
            sleep_time = min(delay + jitter, max_delay)

            logger.warning(f"Retry {retries + 1}/{max_retries} in {sleep_time:.1f}s. Error: {e}")

            await asyncio.sleep(sleep_time)
            retries += 1
            delay = min(delay * backoff_factor, max_delay)


def retry_decorator(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions_to_retry: tuple = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retries before giving up
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor by which the delay increases each retry
        exceptions_to_retry: Exception types to catch and retry on

    Returns:
        A decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_with_backoff(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                exceptions_to_retry=exceptions_to_retry,
                **kwargs,
            )

        return wrapper

    return decorator

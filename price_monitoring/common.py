"""Common functions and utilities for the price monitoring system.

The module provides common functions for creating HTTP headers
and managing sessions with proxy servers.
"""

from collections.abc import Sequence
from time import time

from random_user_agent.params import OperatingSystem, SoftwareName
from random_user_agent.user_agent import UserAgent

from proxy_http.aiohttp_session_factory import AiohttpSessionFactory
from proxy_http.async_proxies_concurrent_limiter import AsyncSessionConcurrentLimiter
from proxy_http.proxy import Proxy

# User-Agent rotator for simulating requests from different browsers
user_agent_rotator = UserAgent(
    software_names=[SoftwareName.CHROME.value],
    operating_systems=[OperatingSystem.WINDOWS.value],
    limit=1000,
)


def _create_headers():
    """Create a set of HTTP headers for requests.

    Generates headers with a random User-Agent to simulate requests
    from different browsers to reduce the likelihood of blocking.

    Returns:
        dict: Dictionary with HTTP headers for requests.
    """
    return {
        "User-Agent": user_agent_rotator.get_random_user_agent(),
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        # 'X-Requested-With': 'XMLHttpRequest',
        "Connection": "keep-alive",
        # 'Referer': referer,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


def create_limiter(proxies: Sequence[Proxy]):
    """Create a limiter for simultaneous connections through proxies.

    Creates an object to control and limit the number of simultaneous
    HTTP sessions through proxy servers, preventing their overload.

    Args:
        proxies: Sequence of Proxy objects for creating sessions.

    Returns:
        AsyncSessionConcurrentLimiter: Session management object.
    """
    return AsyncSessionConcurrentLimiter(
        [
            AiohttpSessionFactory.create_session_with_proxy(proxy, headers=_create_headers())
            for proxy in proxies
        ],
        time(),
    )

"""Factory for creating aiohttp sessions.

This module provides a factory for creating aiohttp sessions with proxy support.
"""

import logging
import random
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class AiohttpSessionFactory:
    """Factory for creating aiohttp sessions.

    This class provides methods for creating aiohttp sessions with
    optional proxy support.
    """

    def __init__(self, proxy_file_path: Optional[str] = None):
        """Initialize the factory.

        Args:
            proxy_file_path: Path to file with proxy list (optional)
        """
        self.proxies: List[str] = []
        self.proxy_file_path = proxy_file_path

        if proxy_file_path:
            self._load_proxies()

    def _load_proxies(self) -> None:
        """Load proxies from file."""
        if not self.proxy_file_path:
            return

        try:
            with open(self.proxy_file_path) as file:
                self.proxies = [line.strip() for line in file if line.strip()]
            logger.info(f"Loaded {len(self.proxies)} proxies from {self.proxy_file_path}")
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")

    def _get_random_proxy(self) -> Optional[str]:
        """Get a random proxy from the list.

        Returns:
            Random proxy URL or None if no proxies available
        """
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def create_session(
        self,
        use_proxy: bool = False,
        proxy_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
        timeout: Optional[aiohttp.ClientTimeout] = None,
    ) -> aiohttp.ClientSession:
        """Create an aiohttp session.

        Args:
            use_proxy: Whether to use proxy
            proxy_url: Specific proxy URL to use (optional)
            headers: HTTP headers to include (optional)
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout

        Returns:
            Configured aiohttp session
        """
        session_kwargs = {}

        if headers:
            session_kwargs["headers"] = headers

        if timeout:
            session_kwargs["timeout"] = timeout

        if use_proxy:
            if proxy_url:
                session_kwargs["proxy"] = proxy_url
            elif self.proxies:
                session_kwargs["proxy"] = self._get_random_proxy()

        session_kwargs["connector"] = aiohttp.TCPConnector(verify_ssl=verify_ssl)

        return aiohttp.ClientSession(**session_kwargs)

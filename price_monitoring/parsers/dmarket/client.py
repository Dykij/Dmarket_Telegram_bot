"""DMarket API client.

This module provides a client for accessing the DMarket API.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Optional

import aiohttp

from common.env_var import DMARKET_API_KEY, DMARKET_PUBLIC_KEY, DMARKET_SECRET_KEY
from price_monitoring.constants.dmarket_api import (
    DMARKET_BASE_URL,
    DMARKET_ITEM_DETAILS_ENDPOINT,
    DMARKET_MARKET_ITEMS_ENDPOINT,
    DMARKET_REQUEST_TIMEOUT,
)
from price_monitoring.exceptions import (
    DMarketAPIError,
    DMarketRateLimitError,
    InvalidResponseFormatError,
    NetworkError,
)
from price_monitoring.retries import retry_decorator
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory

logger = logging.getLogger(__name__)


class DMarketClient:
    """Client for the DMarket API.

    Handles authentication, request signing, and API communication.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        public_key: Optional[str] = None,
        base_url: str = DMARKET_BASE_URL,
        use_proxy: bool = True,
    ):
        """Initialize the DMarket API client.

        Args:
            api_key: DMarket API key (default: from environment)
            secret_key: DMarket secret key (default: from environment)
            public_key: DMarket public key (default: from environment)
            base_url: Base URL for DMarket API (default: from constants)
            use_proxy: Whether to use proxies for requests
        """
        self._api_key = api_key or DMARKET_API_KEY
        self._secret_key = secret_key or DMARKET_SECRET_KEY
        self._public_key = public_key or DMARKET_PUBLIC_KEY
        self._base_url = base_url
        self._use_proxy = use_proxy
        self._session_factory = AiohttpSessionFactory()

    async def get_session(self) -> aiohttp.ClientSession:
        """Get an aiohttp session for API requests.

        Returns:
            aiohttp session configured for DMarket API
        """
        session = self._session_factory.create_session(
            use_proxy=self._use_proxy,
            verify_ssl=True,
            timeout=aiohttp.ClientTimeout(total=DMARKET_REQUEST_TIMEOUT),
        )
        return session

    def _generate_signature(self, method: str, url: str, body: Optional[dict] = None) -> str:
        """Generate HMAC signature for DMarket API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            body: Request body (for POST requests)

        Returns:
            Base64-encoded signature
        """
        timestamp = str(int(time.time()))
        string_to_sign = f"{method.upper()}{url}{timestamp}"

        if body:
            string_to_sign += json.dumps(body, separators=(",", ":"))

        signature = hmac.new(
            self._secret_key.encode(), string_to_sign.encode(), hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()

    def _build_headers(
        self, method: str, endpoint: str, body: Optional[dict] = None
    ) -> dict[str, str]:
        """Build headers for DMarket API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            body: Request body (for POST requests)

        Returns:
            Dictionary of HTTP headers
        """
        timestamp = str(int(time.time()))
        signature = self._generate_signature(method, endpoint, body)

        headers = {
            "X-Api-Key": self._api_key,
            "X-Request-Sign": signature,
            "X-Sign-Date": timestamp,
            "X-User-Agent": "dmarket-bot/1.0",
        }

        if body:
            headers["Content-Type"] = "application/json"

        return headers

    @retry_decorator(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        exceptions_to_retry=(NetworkError, DMarketRateLimitError),
    )
    async def get_market_items(self, **params: Any) -> dict[str, Any]:
        """Get items from the DMarket market.

        Args:
            **params: Query parameters for filtering items

        Returns:
            API response containing market items

        Raises:
            NetworkError: If a network error occurs
            DMarketAPIError: If the API returns an error
            DMarketRateLimitError: If rate limits are exceeded
            InvalidResponseFormatError: If the response cannot be parsed
        """
        endpoint = DMARKET_MARKET_ITEMS_ENDPOINT
        url = f"{self._base_url}{endpoint}"
        headers = self._build_headers("GET", endpoint)

        session = await self.get_session()
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    error_text = await response.text()
                    raise DMarketRateLimitError(
                        status_code=response.status,
                        message=f"Rate limit exceeded: {error_text}",
                        retry_after=retry_after,
                        response_body=error_text,
                    )
                elif response.status != 200:
                    error_text = await response.text()
                    raise DMarketAPIError(
                        status_code=response.status,
                        message=f"DMarket API error: {error_text}",
                        response_body=error_text,
                    )

                try:
                    data = await response.json()
                    return data
                except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                    response_text = await response.text()
                    raise InvalidResponseFormatError(
                        f"Invalid JSON response: {e}", response=response_text
                    ) from e
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error when connecting to DMarket: {e}") from e
        finally:
            await session.close()

    @retry_decorator(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        exceptions_to_retry=(NetworkError, DMarketRateLimitError),
    )
    async def get_item_details(self, item_id: str) -> dict[str, Any]:
        """Get details for a specific item.

        Args:
            item_id: DMarket item ID

        Returns:
            API response containing item details

        Raises:
            NetworkError: If a network error occurs
            DMarketAPIError: If the API returns an error
            DMarketRateLimitError: If rate limits are exceeded
            InvalidResponseFormatError: If the response cannot be parsed
        """
        endpoint = f"{DMARKET_ITEM_DETAILS_ENDPOINT}/{item_id}"
        url = f"{self._base_url}{endpoint}"
        headers = self._build_headers("GET", endpoint)

        session = await self.get_session()
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    error_text = await response.text()
                    raise DMarketRateLimitError(
                        status_code=response.status,
                        message=f"Rate limit exceeded: {error_text}",
                        retry_after=retry_after,
                        response_body=error_text,
                    )
                elif response.status != 200:
                    error_text = await response.text()
                    raise DMarketAPIError(
                        status_code=response.status,
                        message=f"DMarket API error: {error_text}",
                        response_body=error_text,
                    )

                try:
                    data = await response.json()
                    return data
                except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                    response_text = await response.text()
                    raise InvalidResponseFormatError(
                        f"Invalid JSON response: {e}", response=response_text
                    ) from e
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error when connecting to DMarket: {e}") from e
        finally:
            await session.close()

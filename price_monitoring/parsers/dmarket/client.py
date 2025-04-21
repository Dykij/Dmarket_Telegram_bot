"""DMarket API Client implementation."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Union

import aiohttp

from common.dmarket_auth import build_signature
from common.errors import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    DMarketAPIError,
    DMarketAuthError,
    DMarketRateLimitError,
    DMarketResourceError,
    DMarketRequestError,
    DMarketServerError,
    DMARKET_PUBLIC_CIRCUIT_BREAKER,
    DMARKET_PRIVATE_CIRCUIT_BREAKER,
    DMARKET_TRADING_CIRCUIT_BREAKER,
    classify_dmarket_error
)
from price_monitoring.storage.proxy.abstract_proxy_storage import AbstractProxyStorage
from utils.rate_limiter import (
    DMARKET_PUBLIC_RATE_LIMITER,
    DMARKET_PRIVATE_RATE_LIMITER,
    DMARKET_TRADING_RATE_LIMITER,
    RateLimiter
)

logger = logging.getLogger(__name__)


class DMarketClient:
    """Asynchronous client for interacting with the DMarket API."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        public_key: str,
        session: aiohttp.ClientSession | None = None,
        proxy_storage: AbstractProxyStorage | None = None,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        max_retries: int = 3,
    ):
        """Initializes the DMarketClient.

        Args:
            api_key: DMarket API key.
            secret_key: DMarket secret key.
            public_key: DMarket public key.
            session: An optional aiohttp client session.
            proxy_storage: An optional storage for proxies.
            limiter: An optional rate limiter.
        """
        if not public_key or not secret_key:
            # Break line to fix length
            raise ValueError("DMarket API keys (public and secret) are required.")
        self._api_key = api_key
        self._secret_key = secret_key
        self._public_key = public_key
        self._base_url = "https://api.dmarket.com"
        self._session = session
        self._proxy_storage = proxy_storage
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._max_retries = max_retries

    async def close_session(self):
        """Closes the aiohttp client session if it was created internally."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Returns the current session or creates a new one."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        Makes an asynchronous request to the DMarket API with retry logic and circuit breaker.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: Query parameters
            data: Request body data
            retry_count: Current retry attempt (used internally for recursion)

        Returns:
            API response as a dictionary, or None if the request failed

        Raises:
            DMarketAPIError: If an API error occurs and max retries are exceeded
            CircuitBreakerOpenError: If the circuit breaker is open
        """
        # Get the appropriate circuit breaker for this endpoint
        circuit_breaker = self._get_circuit_breaker_for_path(path)

        # Check if circuit breaker allows the request
        if circuit_breaker and not circuit_breaker.allow_request():
            open_until = circuit_breaker._last_failure_time + circuit_breaker.reset_timeout
            raise CircuitBreakerOpenError(circuit_breaker.name, open_until)

        session = await self._get_session()
        url = f"{self._base_url}{path}"
        timestamp = str(int(time.time()))
        body_str: str | None = None

        # If data is provided, convert it to a JSON string
        if data is not None:
            body_str = json.dumps(data, separators=(",", ":"))

        signature = build_signature(
            self._public_key,
            self._secret_key,
            method,
            path,
            timestamp,
            body_str,
        )

        headers = {
            "X-Api-Key": self._public_key,
            "X-Request-Sign": f"dmar ed25519 {signature}",
            "X-Sign-Timestamp": timestamp,
            "Content-Type": "application/json",
        }

        proxy_url = None
        if self._proxy_storage:
            # Logic to get a proxy from storage - simplified
            # proxies = await self._proxy_storage.get_all()
            # if proxies:
            #     proxy = random.choice(proxies)
            #     proxy_url = str(proxy)
            pass  # Placeholder for actual proxy retrieval logic

        # Determine which rate limiter to use based on the endpoint
        rate_limiter = self._get_rate_limiter_for_path(path)

        try:
            # Apply rate limiting before making the request
            await rate_limiter.wait_if_needed()

            # Make the request
            async with session.request(
                method,
                url,
                headers=headers,
                params=params,
                data=body_str,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                logger.debug(f"Request: {method} {url} | Status: {response.status}")

                # Get response body for error handling
                response_text = await response.text()

                # Try to parse response as JSON
                response_data = None
                try:
                    if response_text:
                        response_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # Not JSON or invalid JSON
                    pass

                # Handle successful response
                if 200 <= response.status < 300:
                    # Mark success for rate limiter and circuit breaker
                    rate_limiter.mark_success()
                    if circuit_breaker:
                        circuit_breaker.record_success()

                    return response_data

                # Handle error responses
                error = classify_dmarket_error(
                    status_code=response.status,
                    response_data=response_data
                )

                # Handle rate limit errors specially
                if isinstance(error, DMarketRateLimitError):
                    retry_after = error.retry_after
                    await rate_limiter.handle_rate_limit_error(
                        status_code=response.status,
                        retry_after=retry_after
                    )

                # Record failure in circuit breaker
                if circuit_breaker:
                    circuit_breaker.record_failure()

                # Retry logic for retryable errors
                if retry_count < self._max_retries and self._should_retry(error):
                    retry_count += 1
                    wait_time = self._calculate_retry_wait_time(retry_count)

                    logger.warning(
                        f"Retrying request after error: {error}. "
                        f"Retry {retry_count}/{self._max_retries} in {wait_time:.2f}s"
                    )

                    await asyncio.sleep(wait_time)
                    return await self._request(method, path, params, data, retry_count)

                # If we've exhausted retries or it's not retryable, log and return None
                logger.error(
                    f"DMarket API error: {error}. "
                    f"URL: {url}, Method: {method}, Status: {response.status}"
                )
                return None

        except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
            # Network errors are retryable
            if circuit_breaker:
                circuit_breaker.record_failure()

            if retry_count < self._max_retries:
                retry_count += 1
                wait_time = self._calculate_retry_wait_time(retry_count)

                logger.warning(
                    f"Network error: {e}. "
                    f"Retry {retry_count}/{self._max_retries} in {wait_time:.2f}s"
                )

                await asyncio.sleep(wait_time)
                return await self._request(method, path, params, data, retry_count)

            logger.error(f"Network error after {self._max_retries} retries: {e}")
            return None

        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected error during DMarket API request: {e}")
            if circuit_breaker:
                circuit_breaker.record_failure()
            return None

    def _get_rate_limiter_for_path(self, path: str) -> RateLimiter:
        """
        Returns the appropriate rate limiter for the given API path.

        Different DMarket API endpoints have different rate limits:
        - Public endpoints (market items, etc.): 100 requests per minute
        - Private endpoints (user data, etc.): 60 requests per minute
        - Trading endpoints (create/edit offers): 30 requests per minute

        Args:
            path: The API path

        Returns:
            The appropriate RateLimiter instance
        """
        # Use custom rate limiter if provided
        if self._rate_limiter:
            return self._rate_limiter

        # Trading endpoints
        if any(trading_path in path for trading_path in [
            "/exchange/v1/offers",
            "/exchange/v1/user/offers",
            "/exchange/v1/user/inventory",
        ]):
            return DMARKET_TRADING_RATE_LIMITER

        # Private endpoints
        if any(private_path in path for private_path in [
            "/account/v1/balance",
            "/exchange/v1/user",
            "/account/v1/user",
        ]):
            return DMARKET_PRIVATE_RATE_LIMITER

        # Default to public rate limiter for all other endpoints
        return DMARKET_PUBLIC_RATE_LIMITER

    def _get_circuit_breaker_for_path(self, path: str) -> Optional[CircuitBreaker]:
        """
        Returns the appropriate circuit breaker for the given API path.

        Args:
            path: The API path

        Returns:
            The appropriate CircuitBreaker instance, or None if custom circuit breaker is disabled
        """
        # Use custom circuit breaker if provided
        if self._circuit_breaker:
            return self._circuit_breaker

        # Trading endpoints
        if any(trading_path in path for trading_path in [
            "/exchange/v1/offers",
            "/exchange/v1/user/offers",
            "/exchange/v1/user/inventory",
        ]):
            return DMARKET_TRADING_CIRCUIT_BREAKER

        # Private endpoints
        if any(private_path in path for private_path in [
            "/account/v1/balance",
            "/exchange/v1/user",
            "/account/v1/user",
        ]):
            return DMARKET_PRIVATE_CIRCUIT_BREAKER

        # Default to public circuit breaker for all other endpoints
        return DMARKET_PUBLIC_CIRCUIT_BREAKER

    def _should_retry(self, error: DMarketAPIError) -> bool:
        """
        Determines if a request should be retried based on the error.

        Args:
            error: The DMarketAPIError that occurred

        Returns:
            True if the request should be retried, False otherwise
        """
        # Don't retry client errors (except rate limiting which is handled separately)
        if isinstance(error, DMarketRequestError) or isinstance(error, DMarketAuthError):
            return False

        # Retry server errors and resource errors
        if isinstance(error, DMarketServerError) or isinstance(error, DMarketResourceError):
            return True

        # Retry rate limit errors
        if isinstance(error, DMarketRateLimitError):
            return True

        # Default to not retrying unknown errors
        return False

    def _calculate_retry_wait_time(self, retry_count: int) -> float:
        """
        Calculates the wait time for a retry using exponential backoff with jitter.

        Args:
            retry_count: The current retry attempt (1-based)

        Returns:
            The wait time in seconds
        """
        # Base wait time with exponential backoff: 2^(retry_count - 1)
        base_wait_time = 2 ** (retry_count - 1)

        # Add jitter (random value between 0 and 1)
        jitter = random.random()

        # Combine base wait time and jitter
        wait_time = base_wait_time + jitter

        # Cap at 30 seconds
        return min(wait_time, 30.0)

    async def get_market_items(
        self,
        game_id: str,
        currency: str = "USD",
        limit: int = 100,
        order_by: str = "price",
        order_dir: str = "asc",
        price_from: Optional[int] = None,
        price_to: Optional[int] = None,
        tree_filters: Optional[str] = None,
        offset: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetches market items based on specified filters."""
        path = "/exchange/v1/market/items"
        params: Dict[str, Any] = {
            "gameId": game_id,
            "currency": currency,
            "limit": str(limit),
            "orderBy": order_by,
            "orderDir": order_dir,
        }
        if price_from is not None:
            params["priceFrom"] = str(price_from)
        if price_to is not None:
            params["priceTo"] = str(price_to)
        if tree_filters:
            params["treeFilters"] = tree_filters
        if offset:
            params["offset"] = offset

        return await self._request("GET", path, params=params)

    async def get_offers_by_title(
        self,
        title: str,
        currency: str = "USD",
        limit: int = 100,
        offset: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetches offers based on item title."""
        path = "/exchange/v1/offers-by-title"
        params: Dict[str, Any] = {
            "title": title,
            "currency": currency,
            "limit": str(limit),
        }
        if offset:
            params["offset"] = offset
        return await self._request("GET", path, params=params)

    async def get_user_offers(
        self,
        status: str,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
        currency: str = "USD",  # Add currency parameter
        limit: int = 100,
        offset: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetches user's offers based on status and other filters."""
        path = "/exchange/v1/user/offers"
        params: Dict[str, Any] = {
            "status": status,
            "currency": currency,
            "limit": str(limit),
        }
        if game_id:
            params["gameId"] = game_id
        if title:
            params["title"] = title
        if offset:
            params["offset"] = offset
        return await self._request("GET", path, params=params)

    async def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Fetches the account balance.

        Ref:
            https://docs.dmarket.com/v1/swagger.html#/Account/getAccountBalance
        """
        path = "/account/v1/balance"
        return await self._request("GET", path)

    async def create_offer(
        self, item_id: str, price_cents: int, currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """Creates a sell offer for an item."""
        path = f"/exchange/v1/offers/{item_id}"
        method = "POST"
        body = {"price": {currency: str(price_cents)}}
        return await self._request(method, path, data=body)

    async def edit_offer(
        self, offer_id: str, price_cents: int, currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """Edits an existing sell offer."""
        path = f"/exchange/v1/offers/{offer_id}"
        method = "PATCH"
        body = {"price": {currency: str(price_cents)}}
        return await self._request(method, path, data=body)

"""HTTP Client Module with Error Handling and Retries.

This module provides a robust HTTP client with:
- Error handling for common network issues
- Automatic retries with exponential backoff
- Circuit breaker pattern to prevent cascading failures
- Proxy support
- Request and response logging
"""

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

import aiohttp
from aiohttp import ClientResponse, ClientSession, ClientTimeout, TCPConnector
from aiohttp_socks import ProxyConnector

from common.secure_logging import get_secure_logger

# Type variable for the decorator return type
T = TypeVar("T")

# Set up secure logger
logger = get_secure_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is healthy again


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5  # Number of failures before opening circuit
    recovery_timeout: float = 30.0  # Seconds to wait before trying half-open
    success_threshold: int = 2  # Successful requests needed to close circuit


class CircuitBreaker:
    """Circuit breaker implementation to prevent cascading failures.

    This class implements the circuit breaker pattern to prevent a failing
    service from causing cascading failures across the application.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """Initialize a circuit breaker.

        Args:
            name: Name of the circuit breaker (used for logging)
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self._lock = asyncio.Lock()

    async def __call__(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Any exception raised by the function
        """
        async with self._lock:
            # Check if circuit is open
            if self.state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has elapsed
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    logger.info(f"Circuit {self.name} trying half-open state")
                    self.state = CircuitBreakerState.HALF_OPEN
                else:
                    logger.warning(f"Circuit {self.name} is open, failing fast")
                    raise CircuitBreakerOpenError(f"Circuit {self.name} is open")

        try:
            # Execute function
            result = await func(*args, **kwargs)

            # Handle success
            async with self._lock:
                if self.state == CircuitBreakerState.HALF_OPEN:
                    self.success_count += 1
                    if self.success_count >= self.config.success_threshold:
                        logger.info(
                            f"Circuit {self.name} closed after {self.success_count} successes"
                        )
                        self.state = CircuitBreakerState.CLOSED
                        self.failure_count = 0
                        self.success_count = 0
                elif self.state == CircuitBreakerState.CLOSED:
                    # Reset failure count on success in closed state
                    self.failure_count = 0

            return result

        except Exception:
            # Handle failure
            async with self._lock:
                self.last_failure_time = time.time()

                if self.state == CircuitBreakerState.HALF_OPEN:
                    # Any failure in half-open state opens the circuit again
                    logger.warning(f"Circuit {self.name} reopened after failure in half-open state")
                    self.state = CircuitBreakerState.OPEN
                    self.success_count = 0
                elif self.state == CircuitBreakerState.CLOSED:
                    self.failure_count += 1
                    if self.failure_count >= self.config.failure_threshold:
                        logger.warning(
                            f"Circuit {self.name} opened after {self.failure_count} failures"
                        )
                        self.state = CircuitBreakerState.OPEN

            # Re-raise the original exception
            raise


class CircuitBreakerOpenError(Exception):
    """Exception raised when a circuit breaker is open."""

    pass


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        jitter: float = 0.1,
        retry_on_status_codes: Optional[List[int]] = None,
        retry_on_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            backoff_factor: Multiplier for delay after each retry
            jitter: Random factor to add to delay to prevent thundering herd
            retry_on_status_codes: HTTP status codes to retry on
            retry_on_exceptions: Exception types to retry on
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on_status_codes = retry_on_status_codes or [
            429,  # Too Many Requests
            500,
            502,
            503,
            504,  # Server errors
        ]
        self.retry_on_exceptions = retry_on_exceptions or [
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ]

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a retry attempt with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        delay = self.retry_delay * (self.backoff_factor**attempt)
        jitter_amount = delay * self.jitter
        return delay + random.uniform(-jitter_amount, jitter_amount)


async def with_retry(func: Callable[..., T], config: RetryConfig, *args: Any, **kwargs: Any) -> T:
    """Execute a function with retry logic.

    Args:
        func: Function to execute
        config: Retry configuration
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function

    Raises:
        Last exception encountered if all retries fail
    """
    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)

            # For aiohttp responses, check status code
            if isinstance(result, ClientResponse) and result.status in config.retry_on_status_codes:
                last_exception = aiohttp.ClientResponseError(
                    request_info=result.request_info,
                    history=result.history,
                    status=result.status,
                    message=f"HTTP {result.status}: {result.reason}",
                    headers=result.headers,
                )
                logger.warning(
                    f"Request failed with status {result.status}, "
                    f"attempt {attempt + 1}/{config.max_retries + 1}"
                )
            else:
                # Success
                return result

        except Exception as e:
            last_exception = e
            should_retry = any(isinstance(e, exc_type) for exc_type in config.retry_on_exceptions)

            if not should_retry:
                logger.error(f"Non-retryable error: {e!s}")
                raise

            logger.warning(
                f"Request failed with {type(e).__name__}: {e!s}, "
                f"attempt {attempt + 1}/{config.max_retries + 1}"
            )

        # Last attempt, re-raise the exception
        if attempt >= config.max_retries:
            logger.error(f"All retry attempts failed, last error: {last_exception}")
            assert last_exception is not None
            raise last_exception

        # Calculate and apply delay before retry
        delay = config.calculate_delay(attempt)
        logger.info(f"Retrying in {delay:.2f} seconds...")
        await asyncio.sleep(delay)

    # This should never be reached due to the re-raise above
    assert False, "Unreachable code"


class AsyncHttpClient:
    """Async HTTP client with robust error handling and retries.

    This client wraps aiohttp.ClientSession with additional features:
    - Error handling and logging
    - Automatic retries with exponential backoff
    - Circuit breaker pattern
    - Proxy support
    - Request and response logging
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        timeout: float = 30.0,
        proxy: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the HTTP client.

        Args:
            base_url: Base URL for all requests
            retry_config: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
            timeout: Request timeout in seconds
            proxy: Proxy URL (supports HTTP, SOCKS4, SOCKS5)
            default_headers: Default headers to include in all requests
        """
        self.base_url = base_url
        self.retry_config = retry_config or RetryConfig()
        self.timeout = ClientTimeout(total=timeout)
        self.proxy = proxy
        self.default_headers = default_headers or {}

        # Initialize session to None, will be created when needed
        self._session: Optional[ClientSession] = None

        # Create circuit breaker
        self.circuit_breaker = CircuitBreaker(
            name="http_client",
            config=circuit_breaker_config,
        )

    async def _get_session(self) -> ClientSession:
        """Get or create the client session.

        Returns:
            ClientSession instance
        """
        if self._session is None or self._session.closed:
            # Create connector based on proxy configuration
            if self.proxy:
                connector = ProxyConnector.from_url(self.proxy)
            else:
                connector = TCPConnector(ssl=False)

            self._session = ClientSession(
                timeout=self.timeout,
                connector=connector,
                headers=self.default_headers,
            )

        return self._session

    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> ClientResponse:
        """Send an HTTP request with circuit breaker protection.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments for the request

        Returns:
            ClientResponse object

        Raises:
            Various HTTP exceptions
        """
        # Resolve full URL
        full_url = f"{self.base_url}{url}" if self.base_url and not url.startswith("http") else url

        # Get session
        session = await self._get_session()

        # Log request
        logger.info(f"Sending {method} request to {full_url}")

        # Define request function to execute with retry
        async def do_request() -> ClientResponse:
            return await self.circuit_breaker(
                session.request,
                method=method,
                url=full_url,
                **kwargs,
            )

        # Execute request with retry logic
        return await with_retry(do_request, self.retry_config)

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Send a GET request.

        Args:
            url: Request URL
            params: Query parameters
            headers: Request headers
            **kwargs: Additional arguments for the request

        Returns:
            ClientResponse object
        """
        return await self._request(
            method="GET",
            url=url,
            params=params,
            headers=headers,
            **kwargs,
        )

    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Send a POST request.

        Args:
            url: Request URL
            data: Request data
            json: JSON data
            headers: Request headers
            **kwargs: Additional arguments for the request

        Returns:
            ClientResponse object
        """
        return await self._request(
            method="POST",
            url=url,
            data=data,
            json=json,
            headers=headers,
            **kwargs,
        )

    async def put(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Send a PUT request.

        Args:
            url: Request URL
            data: Request data
            json: JSON data
            headers: Request headers
            **kwargs: Additional arguments for the request

        Returns:
            ClientResponse object
        """
        return await self._request(
            method="PUT",
            url=url,
            data=data,
            json=json,
            headers=headers,
            **kwargs,
        )

    async def delete(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> ClientResponse:
        """Send a DELETE request.

        Args:
            url: Request URL
            params: Query parameters
            headers: Request headers
            **kwargs: Additional arguments for the request

        Returns:
            ClientResponse object
        """
        return await self._request(
            method="DELETE",
            url=url,
            params=params,
            headers=headers,
            **kwargs,
        )

    async def json_get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Send a GET request and return JSON response.

        Args:
            url: Request URL
            params: Query parameters
            headers: Request headers
            **kwargs: Additional arguments for the request

        Returns:
            Parsed JSON response
        """
        response = await self.get(url, params, headers, **kwargs)
        return await response.json()

    async def json_post(
        self,
        url: str,
        data: Optional[Any] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Send a POST request and return JSON response.

        Args:
            url: Request URL
            data: Request data
            json_data: JSON data
            headers: Request headers
            **kwargs: Additional arguments for the request

        Returns:
            Parsed JSON response
        """
        response = await self.post(url, data, json_data, headers, **kwargs)
        return await response.json()


def create_dmarket_client(
    api_url: Optional[str] = None,
    proxy: Optional[str] = None,
    max_retries: int = 3,
    timeout: float = 30.0,
) -> AsyncHttpClient:
    """Create a pre-configured HTTP client for DMarket API.

    Args:
        api_url: DMarket API URL
        proxy: Proxy URL
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds

    Returns:
        Configured AsyncHttpClient instance
    """
    # Import here to avoid circular imports
    from config.dmarket_api import DMarketAPIConfig, DMarketEndpoints

    # Use provided API URL or default from config
    base_url = api_url or DMarketEndpoints.API_URL

    # Create retry config with appropriate settings for DMarket
    retry_config = RetryConfig(
        max_retries=max_retries,
        retry_delay=1.0,
        backoff_factor=2.0,
        retry_on_status_codes=[429, 500, 502, 503, 504],
    )

    # Create circuit breaker config
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        success_threshold=2,
    )

    # Get default headers
    default_headers = DMarketAPIConfig.get_default_headers()

    return AsyncHttpClient(
        base_url=base_url,
        retry_config=retry_config,
        circuit_breaker_config=circuit_breaker_config,
        timeout=timeout,
        proxy=proxy,
        default_headers=default_headers,
    )

"""Error Handling Module for DMarket API

This module provides custom exception classes and utilities for handling
errors that may occur when interacting with the DMarket API. It includes:

1. Custom exception classes for different types of API errors
2. A circuit breaker implementation to prevent cascading failures
3. Utilities for classifying and handling errors based on API error codes

Usage:
    from common.errors import DMarketAPIError, CircuitBreaker

    # Using custom exceptions
    try:
        response = await client.get_market_items(...)
        if not response:
            raise DMarketAPIError("Failed to get market items")
    except DMarketRateLimitError as e:
        # Handle rate limit error
        logger.warning(f"Rate limit exceeded: {e}")
    except DMarketAPIError as e:
        # Handle other API errors
        logger.error(f"API error: {e}")

    # Using circuit breaker
    breaker = CircuitBreaker(name="dmarket_api", failure_threshold=5)
    try:
        with breaker:
            response = await client.get_market_items(...)
    except CircuitBreakerOpenError:
        # Circuit is open, handle gracefully
        logger.error("Circuit breaker is open, DMarket API is unavailable")
"""

import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

# Type for functions that can be decorated
F = TypeVar("F", bound=Callable[..., Any])


class DMarketErrorCode(Enum):
    """Enum representing DMarket API error codes."""

    # Authentication errors
    INVALID_API_KEY = "invalid_api_key"
    INVALID_SIGNATURE = "invalid_signature"
    EXPIRED_TIMESTAMP = "expired_timestamp"

    # Rate limiting errors
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Resource errors
    ITEM_NOT_FOUND = "item_not_found"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_PRICE = "invalid_price"

    # Request errors
    INVALID_REQUEST = "invalid_request"
    INVALID_PARAMETERS = "invalid_parameters"

    # Server errors
    INTERNAL_SERVER_ERROR = "internal_server_error"
    SERVICE_UNAVAILABLE = "service_unavailable"

    # Unknown error
    UNKNOWN_ERROR = "unknown_error"


class DMarketAPIError(Exception):
    """Base exception for all DMarket API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[Union[str, DMarketErrorCode]] = None,
        response_data: Optional[dict[str, Any]] = None,
    ):
        """Initialize a new DMarketAPIError.

        Args:
            message: Error message
            status_code: HTTP status code (e.g., 400, 401, 429)
            error_code: DMarket API error code or enum
            response_data: Raw response data from the API
        """
        self.status_code = status_code
        self.error_code = error_code
        self.response_data = response_data or {}
        super().__init__(message)


class DMarketAuthError(DMarketAPIError):
    """Exception raised for authentication errors."""

    pass


class DMarketRateLimitError(DMarketAPIError):
    """Exception raised when API rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = 429,
        retry_after: Optional[float] = None,
        **kwargs,
    ):
        """Initialize a new DMarketRateLimitError.

        Args:
            message: Error message
            status_code: HTTP status code (usually 429)
            retry_after: Suggested wait time in seconds before retrying
            **kwargs: Additional arguments to pass to DMarketAPIError
        """
        self.retry_after = retry_after
        super().__init__(message, status_code=status_code, **kwargs)


class DMarketResourceError(DMarketAPIError):
    """Exception raised for errors related to resources (items, funds, etc.)."""

    pass


class DMarketRequestError(DMarketAPIError):
    """Exception raised for invalid requests or parameters."""

    pass


class DMarketServerError(DMarketAPIError):
    """Exception raised for server-side errors."""

    pass


class CircuitBreakerState(Enum):
    """Enum representing the state of a circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests are allowed
    OPEN = "open"  # Circuit is open, requests are blocked
    HALF_OPEN = "half_open"  # Testing if the service is back to normal


class CircuitBreakerOpenError(Exception):
    """Exception raised when a request is made while the circuit is open."""

    def __init__(self, breaker_name: str, open_until: float):
        """Initialize a new CircuitBreakerOpenError.

        Args:
            breaker_name: Name of the circuit breaker
            open_until: Timestamp when the circuit will transition to half-open
        """
        self.breaker_name = breaker_name
        self.open_until = open_until
        time_remaining = max(0, open_until - time.time())
        super().__init__(
            f"Circuit breaker '{breaker_name}' is open. "
            f"Requests are blocked for {time_remaining:.2f} more seconds."
        )


class CircuitBreaker:
    """Implementation of the Circuit Breaker pattern.

    The circuit breaker prevents cascading failures by stopping requests
    to a service that is experiencing problems. It has three states:

    1. CLOSED: Normal operation, requests are allowed
    2. OPEN: Circuit is open, requests are blocked
    3. HALF_OPEN: Testing if the service is back to normal

    Attributes:
        name: Name of the circuit breaker
        failure_threshold: Number of failures before opening the circuit
        reset_timeout: Time in seconds to wait before transitioning from OPEN to HALF_OPEN
        half_open_max_calls: Maximum number of calls allowed in HALF_OPEN state
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        """Initialize a new CircuitBreaker.

        Args:
            name: Name of the circuit breaker
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds to wait before transitioning from OPEN to HALF_OPEN
            half_open_max_calls: Maximum number of calls allowed in HALF_OPEN state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitBreakerState:
        """Get the current state of the circuit breaker."""
        # Check if we need to transition from OPEN to HALF_OPEN
        if (
            self._state == CircuitBreakerState.OPEN
            and time.time() - self._last_failure_time >= self.reset_timeout
        ):
            self._state = CircuitBreakerState.HALF_OPEN
            self._half_open_calls = 0
            logger.info(f"Circuit breaker '{self.name}' transitioned from OPEN to HALF_OPEN")

        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                # Transition back to CLOSED state
                self._state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' transitioned from HALF_OPEN to CLOSED")
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success in CLOSED state
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._last_failure_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            # Any failure in HALF_OPEN state opens the circuit again
            self._state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' transitioned from HALF_OPEN to OPEN")
        elif self.state == CircuitBreakerState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                # Too many failures, open the circuit
                self._state = CircuitBreakerState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' transitioned from CLOSED to OPEN "
                    f"after {self._failure_count} consecutive failures"
                )

    def allow_request(self) -> bool:
        """Check if a request is allowed based on the current state.

        Returns:
            True if the request is allowed, False otherwise
        """
        current_state = self.state

        if current_state == CircuitBreakerState.CLOSED:
            return True
        elif current_state == CircuitBreakerState.HALF_OPEN:
            # Allow limited number of requests in HALF_OPEN state
            return self._half_open_calls < self.half_open_max_calls
        else:  # OPEN
            return False

    def __enter__(self):
        """Context manager entry point."""
        if not self.allow_request():
            open_until = self._last_failure_time + self.reset_timeout
            raise CircuitBreakerOpenError(self.name, open_until)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        if exc_type is None:
            # No exception, record success
            self.record_success()
        else:
            # Exception occurred, record failure
            self.record_failure()
        # Don't suppress exceptions
        return False


def circuit_breaker(breaker: CircuitBreaker) -> Callable[[F], F]:
    """Decorator to apply circuit breaker pattern to a function.

    Args:
        breaker: CircuitBreaker instance to use

    Returns:
        Decorated function with circuit breaker protection
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not breaker.allow_request():
                open_until = breaker._last_failure_time + breaker.reset_timeout
                raise CircuitBreakerOpenError(breaker.name, open_until)

            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception:
                breaker.record_failure()
                raise

        return wrapper  # type: ignore

    return decorator


def classify_dmarket_error(
    status_code: Optional[int] = None, response_data: Optional[dict[str, Any]] = None
) -> DMarketAPIError:
    """Classify an error based on status code and response data.

    Args:
        status_code: HTTP status code
        response_data: Response data from the API

    Returns:
        An appropriate DMarketAPIError subclass instance
    """
    response_data = response_data or {}
    error_message = response_data.get("message", "Unknown DMarket API error")
    error_code = response_data.get("code", "unknown_error")

    # Classify based on status code
    if status_code in {401, 403}:
        return DMarketAuthError(
            message=f"Authentication error: {error_message}",
            status_code=status_code,
            error_code=error_code,
            response_data=response_data,
        )
    elif status_code == 429:
        retry_after = None
        if "retry_after" in response_data:
            retry_after = float(response_data["retry_after"])

        return DMarketRateLimitError(
            message=f"Rate limit exceeded: {error_message}",
            status_code=status_code,
            retry_after=retry_after,
            error_code=error_code,
            response_data=response_data,
        )
    elif status_code in {404, 410}:
        return DMarketResourceError(
            message=f"Resource error: {error_message}",
            status_code=status_code,
            error_code=error_code,
            response_data=response_data,
        )
    elif status_code and 400 <= status_code < 500:
        return DMarketRequestError(
            message=f"Request error: {error_message}",
            status_code=status_code,
            error_code=error_code,
            response_data=response_data,
        )
    elif status_code and 500 <= status_code < 600:
        return DMarketServerError(
            message=f"Server error: {error_message}",
            status_code=status_code,
            error_code=error_code,
            response_data=response_data,
        )
    else:
        return DMarketAPIError(
            message=f"Unknown error: {error_message}",
            status_code=status_code,
            error_code=error_code,
            response_data=response_data,
        )


# Global circuit breakers for different DMarket API endpoints
DMARKET_PUBLIC_CIRCUIT_BREAKER = CircuitBreaker(
    name="dmarket_public_api", failure_threshold=10, reset_timeout=60.0
)

DMARKET_PRIVATE_CIRCUIT_BREAKER = CircuitBreaker(
    name="dmarket_private_api", failure_threshold=5, reset_timeout=120.0
)

DMARKET_TRADING_CIRCUIT_BREAKER = CircuitBreaker(
    name="dmarket_trading_api", failure_threshold=3, reset_timeout=300.0
)

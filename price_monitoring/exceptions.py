"""DMarket exceptions.

This module contains custom exceptions used in the DMarket API integration.
"""

from typing import Any, Optional, Union


class DMarketError(Exception):
    """Base class for DMarket related exceptions."""

    pass


class NetworkError(DMarketError):
    """Raised when a network error occurs during API communication."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class DMarketAPIError(DMarketError):
    """Raised when the DMarket API returns an error response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: Optional[Union[dict[str, Any], str]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class DMarketRateLimitError(DMarketAPIError):
    """Raised when the DMarket API rate limit is exceeded."""

    def __init__(
        self,
        status_code: int,
        message: str,
        retry_after: Optional[float] = None,
        response_body: Optional[Union[dict[str, Any], str]] = None,
    ):
        super().__init__(status_code, message, response_body)
        self.retry_after = retry_after


class InvalidResponseFormatError(DMarketError):
    """Raised when the response from DMarket API has an unexpected format."""

    def __init__(self, message: str, response: Any = None):
        super().__init__(message)
        self.response = response
        super().__init__(f"DMarket API Error ({status_code}): {message}")
        self.status_code = status_code
        self.message = message
        self.response_body = response_body


class InvalidResponseFormatError(DMarketError):
    """Raised when the API response cannot be parsed correctly."""

    pass


class DMarketRateLimitError(DMarketAPIError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        status_code: int,
        message: str,
        retry_after: Optional[float] = None,
        response_body: Optional[Union[Dict[str, Any], str]] = None,
    ):
        super().__init__(status_code, message, response_body)
        self.retry_after = retry_after or 60.0  # Default to 60 seconds

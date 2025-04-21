"""
DMarket Authentication Module

This module provides functions and classes for authenticating with the DMarket API.
It includes utilities for generating signatures required for API requests and
a DMarketAuth class that simplifies the authentication process.

The authentication process follows DMarket's API requirements, which involve
creating HMAC-SHA256 signatures using the API key, secret key, HTTP method,
API path, timestamp, and request body.
"""

import hashlib
import hmac
import json
import time
from typing import Dict, Optional


def build_signature(
    api_key: str,
    secret_key: str,
    method: str,
    api_path: str,
    timestamp: str,
    body: Optional[str] = None,
) -> str:
    """
    Build the signature required for DMarket API authentication.

    This function creates an HMAC-SHA256 signature using the provided parameters,
    following DMarket's API authentication requirements.

    Args:
        api_key: Your DMarket public API key
        secret_key: Your DMarket secret API key
        method: HTTP method (e.g., 'GET', 'POST')
        api_path: API endpoint path (e.g., '/exchange/v1/market/items')
        timestamp: Current Unix timestamp as a string
        body: Request body as a JSON string (only for POST/PUT requests)

    Returns:
        The calculated HMAC-SHA256 signature as a hexadecimal string
    """
    # Concatenate the parameters to create the string to sign
    string_to_sign = api_key + method + api_path + timestamp
    if body:
        string_to_sign += body

    # Create the HMAC-SHA256 signature
    signature = hmac.new(
        secret_key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return signature


def get_current_timestamp() -> str:
    """
    Get the current Unix timestamp as a string.

    This function returns the current time as a Unix timestamp (seconds since
    January 1, 1970, 00:00:00 UTC) converted to a string.

    Returns:
        The current Unix timestamp as a string
    """
    return str(int(time.time()))


class DMarketAuth:
    """
    Authentication handler for DMarket API requests.

    This class simplifies the process of authenticating requests to the DMarket API
    by generating the required authentication headers using the provided API keys.

    Attributes:
        public_key: The DMarket public API key
        secret_key: The DMarket secret API key
    """

    def __init__(self, public_key: str, secret_key: str):
        """
        Initialize a new DMarketAuth instance.

        Args:
            public_key: The DMarket public API key
            secret_key: The DMarket secret API key
        """
        self.public_key = public_key
        self.secret_key = secret_key

    def get_auth_headers(self, method: str, api_path: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict[str, str]:
        """
        Generate authentication headers for a DMarket API request.

        This method creates the X-Api-Key and X-Request-Sign headers required for
        authenticating requests to the DMarket API.

        Args:
            method: HTTP method (e.g., 'GET', 'POST')
            api_path: API endpoint path (e.g., '/exchange/v1/market/items')
            params: Query parameters for the request (for GET requests)
            body: Request body as a dictionary (for POST/PUT requests)

        Returns:
            A dictionary containing the authentication headers
        """
        # Get the current timestamp
        timestamp = get_current_timestamp()

        # Convert body to JSON string if provided
        body_str = None
        if body:
            body_str = json.dumps(body)

        # Build the signature
        signature = build_signature(
            api_key=self.public_key,
            secret_key=self.secret_key,
            method=method,
            api_path=api_path,
            timestamp=timestamp,
            body=body_str
        )

        # Create and return the headers
        headers = {
            "X-Api-Key": self.public_key,
            "X-Request-Sign": signature,
            "X-Sign-Date": timestamp,
            "Content-Type": "application/json"
        }

        return headers

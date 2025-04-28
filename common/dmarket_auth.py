"""DMarket authentication utilities.

This module provides utilities for authentication with the DMarket API.
"""

import base64
import hashlib
import hmac
import time
from typing import Optional


def get_current_timestamp() -> int:
    """Get current Unix timestamp.

    Returns:
        Current timestamp as an integer
    """
    return int(time.time())


def build_signature(
    method: str, url: str, timestamp: int, body: Optional[str] = None, secret_key: str = ""
) -> str:
    """Build a signature for DMarket API request.

    Args:
        method: HTTP method (GET, POST, etc)
        url: Request URL
        timestamp: Unix timestamp
        body: Request body (if any)
        secret_key: Secret key for signature

    Returns:
        Base64-encoded signature
    """
    string_to_sign = f"{method.upper()}{url}{timestamp}"

    if body:
        string_to_sign += body

    signature = hmac.new(
        secret_key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
    ).digest()

    return base64.b64encode(signature).decode("utf-8")

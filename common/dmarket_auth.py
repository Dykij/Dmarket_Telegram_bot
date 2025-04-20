import hashlib
import hmac
import time
from typing import Optional


def build_signature(
    api_key: str,
    secret_key: str,
    method: str,
    api_path: str,
    timestamp: str,
    body: Optional[str] = None,
) -> str:
    """
    Builds the signature required for DMarket API authentication.

    Args:
        api_key: Your DMarket public API key.
        secret_key: Your DMarket secret API key.
        method: HTTP method (e.g., 'GET', 'POST').
        api_path: API endpoint path (e.g., '/exchange/v1/market/items').
        timestamp: Current Unix timestamp as a string.
        body: Request body as a JSON string (only for POST/PUT requests).

    Returns:
        The calculated HMAC-SHA256 signature.
    """
    string_to_sign = api_key + method + api_path + timestamp
    if body:
        string_to_sign += body

    signature = hmac.new(
        secret_key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return signature


def get_current_timestamp() -> str:
    """Returns the current Unix timestamp as a string."""
    return str(int(time.time()))

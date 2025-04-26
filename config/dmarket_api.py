"""DMarket API Configuration Module.

This module provides configuration and constants for DMarket API integration.
It centralizes all URLs, API endpoints, and selectors to avoid hardcoding them
throughout the codebase.
"""

import os
from typing import Dict, Optional

from pydantic import BaseModel, Field, validator

# Default API URL if not specified in environment
DEFAULT_API_URL = "https://api.dmarket.com"


class DMarketEndpoints:
    """DMarket API endpoints configuration."""

    # Base URLs
    API_URL = os.getenv("DMARKET_API_URL", DEFAULT_API_URL)

    # API versions
    V1 = "v1"
    V2 = "v2"

    # Authentication endpoints
    AUTH = f"{API_URL}/auth"
    EXCHANGE_TOKEN = f"{AUTH}/token"

    # Market data endpoints
    MARKET_ITEMS = f"{API_URL}/{V1}/items"
    MARKET_OFFERS = f"{API_URL}/{V1}/market-offers"
    MARKET_PRICE_AGGREGATED = f"{API_URL}/{V1}/price-aggregated"

    # User data endpoints
    USER_ITEMS = f"{API_URL}/{V1}/user-items"
    USER_OFFERS = f"{API_URL}/{V1}/user-offers"
    USER_BALANCE = f"{API_URL}/{V1}/user/balance"

    # Game-specific endpoints
    GAMES_LIST = f"{API_URL}/{V1}/games"
    GAME_ITEMS = f"{API_URL}/{V1}/game-items"


class DMarketItemCategory:
    """DMarket item category constants."""

    # Game titles
    CS2 = "a8db"  # Counter-Strike 2
    CSGO = "a8db"  # Legacy name for CS2
    DOTA2 = "9a92"  # Dota 2
    RUST = "frb1"  # Rust
    TF2 = "tf2"  # Team Fortress 2

    # Item categories
    KNIFE = "knife"
    PISTOL = "pistol"
    RIFLE = "rifle"
    SNIPER_RIFLE = "sniper rifle"
    SMG = "smg"
    SHOTGUN = "shotgun"
    MACHINEGUN = "machinegun"
    CONTAINER = "container"
    KEY = "key"
    GLOVES = "gloves"
    AGENT = "agent"
    STICKER = "sticker"
    GRAFFITI = "graffiti"


class DMarketRequestParams(BaseModel):
    """Configuration for DMarket API request parameters.

    This model defines the available parameters for DMarket API requests
    with validation and defaults.
    """

    # Common parameters
    game_id: str = Field(..., description="Game ID (e.g., 'a8db' for CS2)")
    limit: int = Field(100, ge=1, le=100, description="Number of items to retrieve (max 100)")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    order_by: str = Field("price", description="Field to order results by")
    order_dir: str = Field("asc", description="Order direction ('asc' or 'desc')")

    # Filter parameters
    category: Optional[str] = Field(None, description="Item category")
    title: Optional[str] = Field(None, description="Item title search")
    price_from: Optional[float] = Field(None, ge=0, description="Minimum price")
    price_to: Optional[float] = Field(None, ge=0, description="Maximum price")
    currency: str = Field("USD", description="Currency for prices")

    # Advanced filters
    status: Optional[str] = Field(None, description="Item status")
    rarity: Optional[str] = Field(None, description="Item rarity")
    exterior: Optional[str] = Field(None, description="Item exterior/wear")

    class Config:
        """Pydantic model configuration."""

        extra = "ignore"  # Allow extra fields that might be added in the future

    @validator("order_dir")
    def validate_order_dir(cls, v: str) -> str:
        """Validate order direction is either 'asc' or 'desc'."""
        if v not in ("asc", "desc"):
            raise ValueError("order_dir must be either 'asc' or 'desc'")
        return v


class DMarketAPIConfig:
    """Configuration for DMarket API integration.

    This class provides methods to generate API request parameters and URLs
    for different types of requests to the DMarket API.
    """

    @staticmethod
    def get_market_offers_url(params: Optional[DMarketRequestParams] = None) -> str:
        """Generate the URL for market offers endpoint with query parameters.

        Args:
            params: Request parameters

        Returns:
            URL with query parameters
        """
        if params is None:
            return DMarketEndpoints.MARKET_OFFERS

        # Convert model to dict, removing None values
        query_params = {k: v for k, v in params.dict().items() if v is not None}

        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])

        return f"{DMarketEndpoints.MARKET_OFFERS}?{query_string}"

    @staticmethod
    def get_default_headers(include_auth: bool = False) -> Dict[str, str]:
        """Get default headers for DMarket API requests.

        Args:
            include_auth: Whether to include authorization headers

        Returns:
            Dictionary of headers
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "DMarket Price Monitor",
        }

        if include_auth:
            # In a real implementation, this would retrieve the token from a secure source
            api_key = os.getenv("DMARKET_API_KEY", "")
            api_secret = os.getenv("DMARKET_API_SECRET", "")

            if api_key and api_secret:
                # This is just a placeholder, actual implementation might differ
                headers["X-Api-Key"] = api_key
                headers["X-Api-Secret"] = api_secret

        return headers

    @staticmethod
    def get_cs2_market_params(
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 100,
    ) -> DMarketRequestParams:
        """Create request parameters for CS2 market offers.

        Args:
            category: Item category (e.g., 'knife', 'rifle')
            min_price: Minimum price
            max_price: Maximum price
            limit: Number of items to retrieve

        Returns:
            Configured request parameters
        """
        params = {
            "game_id": DMarketItemCategory.CS2,
            "limit": limit,
            "currency": "USD",
            "order_by": "price",
            "order_dir": "asc",
        }

        if category:
            params["category"] = category

        if min_price is not None:
            params["price_from"] = min_price

        if max_price is not None:
            params["price_to"] = max_price

        return DMarketRequestParams(**params)


# Commission percentage for DMarket
DMARKET_COMMISSION_PERCENT = float(os.getenv("DMARKET_COMMISSION_PERCENT", "7.0"))

# Predefined categories for quick access
CS2_CATEGORIES = [
    DMarketItemCategory.KNIFE,
    DMarketItemCategory.PISTOL,
    DMarketItemCategory.RIFLE,
    DMarketItemCategory.SNIPER_RIFLE,
    DMarketItemCategory.SMG,
    DMarketItemCategory.SHOTGUN,
    DMarketItemCategory.MACHINEGUN,
    DMarketItemCategory.CONTAINER,
    DMarketItemCategory.KEY,
    DMarketItemCategory.GLOVES,
    DMarketItemCategory.AGENT,
    DMarketItemCategory.STICKER,
]

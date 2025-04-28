"""DMarket API constants.

This module defines constants used for interacting with the DMarket API.
"""

# API endpoints and base URL
DMARKET_BASE_URL = "https://api.dmarket.com"
DMARKET_MARKET_ITEMS_ENDPOINT = "/exchange/v1/market/items"
DMARKET_ITEM_DETAILS_ENDPOINT = "/exchange/v1/market/items/details"
DMARKET_CREATE_OFFER_ENDPOINT = "/exchange/v1/offers"
DMARKET_USER_OFFERS_ENDPOINT = "/exchange/v1/user/offers"

# Rate limiting and retries
DMARKET_MAX_RETRIES = 3
DMARKET_RETRY_DELAY = 1.0  # base delay in seconds
DMARKET_REQUEST_TIMEOUT = 30.0  # seconds

# Feature flags
USE_PROXY = True  # Whether to use proxy for DMarket API requests

# Game IDs
DMARKET_GAME_ID_CS = "a8db"  # CS:GO/CS2
DMARKET_GAME_ID_DOTA2 = "9a92"  # Dota 2
DMARKET_GAME_ID_RUST = "dbd3"  # Rust
DMARKET_GAME_ID_TF2 = "tf2"  # Team Fortress 2

# Currency codes
DMARKET_CURRENCY_USD = "USD"
DMARKET_CURRENCY_EUR = "EUR"
DMARKET_CURRENCY_RUB = "RUB"

# Default limits
DMARKET_DEFAULT_ITEMS_LIMIT = 100  # Maximum items per request

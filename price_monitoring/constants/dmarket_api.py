"""Kohctahtbi для pa6otbi c API DMarket.
Bce URL u эhдnouhtbi 3arpyжaюtcя u3 kohфurypaцuu.
"""

from config.settings import get_settings

# Пoлyчehue hactpoek u3 kohфurypaцuu
settings = get_settings()

# 6a3oвbiй URL для API DMarket
DMARKET_BASE_URL = settings.dmarket_api_url

# Эhдnouhtbi API DMarket
DMARKET_MARKET_ITEMS_ENDPOINT = settings.dmarket_market_items_endpoint
DMARKET_ITEM_DETAILS_ENDPOINT = settings.dmarket_item_details_endpoint

# Hactpoйku для noвtophbix nonbitok u taйmaytoв
DMARKET_MAX_RETRIES = settings.dmarket_max_retries
DMARKET_RETRY_DELAY = settings.dmarket_retry_delay
DMARKET_REQUEST_TIMEOUT = settings.dmarket_request_timeout

# Пy6лuчhbiй u cekpethbiй kлючu API
DMARKET_API_PUBLIC_KEY = settings.dmarket_api_public_key
DMARKET_API_SECRET_KEY = settings.dmarket_api_secret_key

# Hactpoйka ucnoл'3oвahuя npokcu
USE_PROXY = settings.use_proxy

# API endpoints
DMARKET_ITEMS_ENDPOINT = "/exchange/v1/market/items"
DMARKET_SELL_HISTORY_ENDPOINT = "/exchange/v1/market/items/history"
DMARKET_USER_ITEMS_ENDPOINT = "/exchange/v1/user/items"

# HTTP status codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIMEOUT = 504

# Retry configuration
RETRY_STATUS_CODES = {
    HTTP_TOO_MANY_REQUESTS,  # Rate limiting
    HTTP_SERVER_ERROR,  # Server error
    HTTP_SERVICE_UNAVAILABLE,  # Service unavailable
    HTTP_GATEWAY_TIMEOUT,  # Gateway timeout
}

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 0.5  # Base delay in seconds
DEFAULT_REQUEST_TIMEOUT = 30.0  # Seconds

# API parameters
DEFAULT_LIMIT = 100
DEFAULT_CURRENCY = "USD"
DEFAULT_ORDER_BY = "price"
DEFAULT_ORDER_DIR = "asc"

# Price conversion
PRICE_DIVISOR = 100.0  # DMarket API returns price in cents, divide by 100 to get dollars

# User agent and headers
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Parameter names used in API requests
PARAM_GAME = "gameId"
PARAM_TITLE = "title"
PARAM_LIMIT = "limit"
PARAM_OFFSET = "offset"
PARAM_CURRENCY = "currency"
PARAM_ORDER_BY = "orderBy"
PARAM_ORDER_DIR = "orderDir"
PARAM_PRICE_FROM = "priceFrom"
PARAM_PRICE_TO = "priceTo"

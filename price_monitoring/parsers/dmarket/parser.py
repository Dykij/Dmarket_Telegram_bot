"""DMarket Parser Module.

This module provides a parser for the DMarket API results.
"""

import logging
from typing import Any, Optional

from price_monitoring.constants.dmarket_api import DMARKET_BASE_URL
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.parsers.dmarket.client import DMarketClient

logger = logging.getLogger(__name__)


class DMarketParser:
    """Parser for DMarket data.

    This class handles fetching and processing data from the DMarket API,
    including error handling, retries, and result formatting.
    """

    def __init__(self, client: Optional[DMarketClient] = None):
        """Initialize parser with an optional API client.

        Args:
            client: DMarket API client instance (optional)
        """
        self._client = client
        self._base_url = DMARKET_BASE_URL

    def _build_query_params(
        self,
        game_id: str,
        category: Optional[str] = None,
        price_min: Optional[str] = None,
        price_max: Optional[str] = None,
        currency: str = "USD",
        limit: int = 100,
    ) -> dict[str, str]:
        """Build query parameters for DMarket API requests.

        Args:
            game_id: Game ID for filtering items
            category: Category or title filter (optional)
            price_min: Minimum price filter (optional)
            price_max: Maximum price filter (optional)
            currency: Currency for prices (default: USD)
            limit: Maximum number of items to return (default: 100)

        Returns:
            Dictionary of query parameters
        """
        params = {
            "gameId": game_id,
            "currency": currency,
            "limit": str(limit),
        }

        if category:
            params["title"] = category

        if price_min:
            params["priceFrom"] = price_min

        if price_max:
            params["priceTo"] = price_max

        return params

    def _parse_response(self, response_data: dict[str, Any]) -> list[DMarketItem]:
        """Parse DMarket API response into a list of DMarketItem objects.

        Args:
            response_data: API response data as a dictionary

        Returns:
            List of DMarketItem objects
        """
        items = []
        objects = response_data.get("objects", [])

        for item_data in objects:
            try:
                item_id = item_data.get("itemId", "")
                title = item_data.get("title", "") or item_data.get("marketHashName", "")
                price_dict = item_data.get("price", {})

                # Цена обычно представлена в центах
                price_usd_cents = int(price_dict.get("USD", "0"))
                price_usd = price_usd_cents / 100.0

                item = DMarketItem(
                    item_id=item_id, title=title, price_usd=price_usd, raw_data=item_data
                )
                items.append(item)
            except (TypeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse item: {e}")

        return items

    async def get_items(
        self,
        game_id: str,
        category: Optional[str] = None,
        price_min: Optional[str] = None,
        price_max: Optional[str] = None,
        currency: str = "USD",
        limit: int = 100,
    ) -> tuple[list[DMarketItem], Optional[str]]:
        """Get items from DMarket API.

        Args:
            game_id: Game ID for filtering items
            category: Category or title filter (optional)
            price_min: Minimum price filter (optional)
            price_max: Maximum price filter (optional)
            currency: Currency for prices (default: USD)
            limit: Maximum number of items to return (default: 100)

        Returns:
            Tuple of (list of DMarketItem objects, cursor for pagination)

        Raises:
            DMarketAPIError: If the API returns an error response
        """
        if not self._client:
            raise ValueError("DMarket client is required")

        query_params = self._build_query_params(
            game_id=game_id,
            category=category,
            price_min=price_min,
            price_max=price_max,
            currency=currency,
            limit=limit,
        )

        api_response = await self._client.get_market_items(**query_params)

        if not api_response:
            return [], None

        items = self._parse_response(api_response)
        cursor = api_response.get("cursor", "")

        return items, cursor

    def _build_query_params(
        self,
        game_id: str,
        category: Optional[str] = None,
        price_min: Optional[str] = None,
        price_max: Optional[str] = None,
        currency: str = "USD",
        limit: int = 100,
    ) -> Dict[str, str]:
        """Build query parameters for DMarket API requests.

        Args:
            game_id: Game ID for filtering items
            category: Category or title filter (optional)
            price_min: Minimum price filter (optional)
            price_max: Maximum price filter (optional)
            currency: Currency for prices (default: USD)
            limit: Maximum number of items to return (default: 100)

        Returns:
            Dictionary of query parameters
        """
        params = {
            "gameId": game_id,
            "currency": currency,
            "limit": str(limit),
        }

        if category:
            params["title"] = category

        if price_min:
            params["priceFrom"] = price_min

        if price_max:
            params["priceTo"] = price_max

        return params

    def _parse_response(self, response_data: Dict[str, Any]) -> List[DMarketItem]:
        """Parse DMarket API response into a list of DMarketItem objects.

        Args:
            response_data: API response data as a dictionary

        Returns:
            List of DMarketItem objects
        """
        items = []
        objects = response_data.get("objects", [])

        for item_data in objects:
            try:
                item_id = item_data.get("itemId", "")
                title = item_data.get("title", "") or item_data.get("marketHashName", "")
                price_dict = item_data.get("price", {})

                # Цена обычно представлена в центах
                price_usd_cents = int(price_dict.get("USD", "0"))
                price_usd = price_usd_cents / 100.0

                item = DMarketItem(
                    item_id=item_id, title=title, price_usd=price_usd, raw_data=item_data
                )
                items.append(item)
            except (TypeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse item: {e}")

        return items

    async def get_items(
        self,
        game_id: str,
        category: Optional[str] = None,
        price_min: Optional[str] = None,
        price_max: Optional[str] = None,
        currency: str = "USD",
        limit: int = 100,
    ) -> Tuple[List[DMarketItem], Optional[str]]:
        """Get items from DMarket API.

        Args:
            game_id: Game ID for filtering items
            category: Category or title filter (optional)
            price_min: Minimum price filter (optional)
            price_max: Maximum price filter (optional)
            currency: Currency for prices (default: USD)
            limit: Maximum number of items to return (default: 100)

        Returns:
            Tuple of (list of DMarketItem objects, cursor for pagination)
        """
        query_params = self._build_query_params(
            game_id=game_id,
            category=category,
            price_min=price_min,
            price_max=price_max,
            currency=currency,
            limit=limit,
        )

        client = self._client
        api_response = await client.get_market_items(**query_params)

        if not api_response:
            return [], None

        items = self._parse_response(api_response)
        cursor = api_response.get("cursor", "")

        return items, cursor

"""
DMarket Items Parser Module

This module provides functionality for parsing item data from the DMarket API.
It fetches items for a specific game, processes the responses, and converts
the data into DMarketItem objects for further processing.

The parser handles pagination, error handling, and rate limiting to ensure
reliable data retrieval from the DMarket API.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

import aiohttp
from common.dmarket_auth import DMarketAuth
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.parsers.abstract_parser import AbstractParser
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory


class DMarketItemsParser(AbstractParser):
    """
    Parser for retrieving items and their prices from the DMarket API.

    This class implements the AbstractParser interface and provides functionality
    for fetching items from the DMarket API, processing the responses, and
    converting the data into DMarketItem objects.

    The parser handles pagination by using cursors provided in the API responses,
    implements error handling for API requests, and respects rate limits by
    adding delays between requests.
    """
    # Base URL for the DMarket API
    BASE_URL = "https://api.dmarket.com/exchange/v1"

    def __init__(
        self,
        session_factory: AiohttpSessionFactory,
        dmarket_auth: DMarketAuth,
        game_id: str,  # e.g., 'a8db' for CS:GO
        currency: str = "USD",
        items_per_page: int = 100,
        api_request_delay_seconds: float = 1.0,
    ):
        """
        Initialize the DMarket items parser.

        Args:
            session_factory: Factory for creating aiohttp sessions
            dmarket_auth: Instance for authenticating DMarket API requests
            game_id: Game ID on DMarket (e.g., 'a8db' for CS:GO)
            currency: Currency for price requests (default: USD)
            items_per_page: Number of items per API page (default: 100)
            api_request_delay_seconds: Delay between API requests in seconds (default: 1.0)
        """
        self._session_factory = session_factory
        self._dmarket_auth = dmarket_auth
        self._game_id = game_id
        self._currency = currency
        self._items_per_page = items_per_page
        self._api_request_delay = api_request_delay_seconds
        self._logger = logging.getLogger(__name__)

    async def _make_api_request(
        self, session: aiohttp.ClientSession, params: Dict
    ) -> Optional[Dict]:
        """
        Make a single request to the DMarket API /market/items endpoint.

        This method handles the authentication, request execution, and error handling
        for a single API request to the DMarket /market/items endpoint.

        Args:
            session: The aiohttp ClientSession to use for the request
            params: Query parameters for the API request

        Returns:
            The JSON response as a dictionary if successful, None otherwise

        Raises:
            No exceptions are raised; errors are logged and None is returned
        """
        endpoint = "/market/items"
        url = f"{self.BASE_URL}{endpoint}"
        method = "GET"

        # Add authentication headers using dmarket_auth
        headers = self._dmarket_auth.get_auth_headers(method=method, api_path=endpoint, params=params)

        try:
            # Execute the API request
            async with session.get(url, params=params, headers=headers, timeout=30) as response:
                # Check for HTTP errors
                response.raise_for_status()
                self._logger.debug(f"DMarket API request to {url} with params {params} successful.")
                # Parse and return the JSON response
                return await response.json()
        except aiohttp.ClientError as e:
            # Handle HTTP client errors
            self._logger.error(f"Error during DMarket API request to {url}: {e}")
            return None
        except asyncio.TimeoutError:
            # Handle request timeouts
            self._logger.error(f"Timeout during DMarket API request to {url}")
            return None

    async def parse(self) -> Tuple[List[DMarketItem], List[Exception]]:
        """
        Main parsing method that retrieves all items for the specified game.

        This method fetches items from the DMarket API page by page using cursor-based
        pagination. It processes each item, converts prices from cents to dollars,
        and creates DMarketItem objects for valid items.

        Returns:
            A tuple containing:
            - A list of successfully parsed DMarketItem objects
            - A list of exceptions encountered during parsing
        """
        all_items: List[DMarketItem] = []
        errors: List[Exception] = []
        cursor = None
        page_num = 1

        # Create a session for making API requests
        async with self._session_factory.create_session() as session:
            # Continue fetching pages until we break out of the loop
            while True:
                self._logger.info(f"Fetching page {page_num} for game {self._game_id}...")

                # Prepare query parameters for the API request
                params = {
                    "gameId": self._game_id,
                    "currency": self._currency,
                    "limit": str(self._items_per_page),
                    # Add other params like 'orderBy', 'orderDir', 'treeFilters' if needed
                }
                if cursor:
                    params["cursor"] = cursor

                try:
                    # Make the API request
                    data = await self._make_api_request(session, params)

                    # Check if the response is valid
                    if not data or "objects" not in data:
                        self._logger.warning(f"No 'objects' in response or request failed for page {page_num}.")
                        break  # Stop if no data or error

                    # Get the items from the response
                    items_on_page = data.get("objects", [])

                    # Process each item
                    for item_data in items_on_page:
                        try:
                            # Extract price safely and convert from cents string to float dollars
                            price_str = item_data.get("price", {}).get(self._currency)
                            price_usd_float = None

                            if price_str:
                                try:
                                    # Convert price from cents to dollars
                                    price_usd_float = float(price_str) / 100.0
                                except (ValueError, TypeError):
                                    self._logger.warning(
                                        f"Could not convert price '{price_str}' to float for item {item_data.get('itemId')}"
                                    )
                                    # Skip items with invalid prices
                                    continue
                            else:
                                # Skip items without prices in the specified currency
                                continue

                            # Create DMarketItem instance using data from API response
                            item = DMarketItem(
                                item_id=item_data.get("itemId"),
                                class_id=item_data.get("classId"),
                                game_id=self._game_id,  # Already known from parser context
                                title=item_data.get("title"),
                                price_usd=price_usd_float,  # Use the converted float value
                                tradable=item_data.get("tradable", True),  # Default to True if missing
                                image_url=item_data.get("image"),  # Use .get() for optional fields
                                float_value=item_data.get("float"),
                                paint_seed=item_data.get("paintSeed"),
                                phase=item_data.get("phase"),
                            )

                            # Basic validation (ensure required fields are present)
                            if not all([item.item_id, item.class_id, item.title]):
                                self._logger.warning(f"Skipping item due to missing required fields: {item_data}")
                                continue

                            # Add the valid item to the list
                            all_items.append(item)
                        except Exception as e:
                            self._logger.error(f"Error processing item data: {item_data}. Error: {e}")
                            errors.append(e)

                    # Check for next page cursor
                    cursor = data.get("cursor")
                    if not cursor or not items_on_page:
                        self._logger.info(f"No more pages found for game {self._game_id}.")
                        break  # Exit loop if no cursor or no items on the last page

                    # Move to the next page
                    page_num += 1
                    self._logger.debug(f"Moving to next page with cursor: {cursor}")

                    # Respect API rate limits
                    await asyncio.sleep(self._api_request_delay)

                except Exception as e:
                    self._logger.error(f"An unexpected error occurred during parsing page {page_num}: {e}")
                    errors.append(e)
                    break  # Stop parsing this game on critical error

        self._logger.info(f"Finished parsing for game {self._game_id}. Total items: {len(all_items)}, Errors: {len(errors)}")
        return all_items, errors

    async def run(self) -> Tuple[List[DMarketItem], List[Exception]]:
        """
        Run the parser and return the results.

        This method is required by the AbstractParser interface and serves as
        a wrapper around the parse() method. It calls parse() and returns the results.

        Returns:
            A tuple containing:
            - A list of successfully parsed DMarketItem objects
            - A list of exceptions encountered during parsing
        """
        # Call the main parsing method
        items, errors = await self.parse()

        # Log the results
        self._logger.info(f"Run finished. Items: {len(items)}, Errors: {len(errors)}")

        # Return the results
        return items, errors

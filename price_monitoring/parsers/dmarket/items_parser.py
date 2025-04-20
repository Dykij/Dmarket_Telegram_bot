import asyncio
from typing import List, Optional, Tuple

import aiohttp
from common.dmarket_auth import DMarketAuth
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.parsers.abstract_parser import AbstractParser
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory


class DMarketItemsParser(AbstractParser):
    """
    Парсер для получения списка предметов и их цен с DMarket API.
    """
    BASE_URL = "https://api.dmarket.com/exchange/v1" # Or the correct base URL

    def __init__(
        self,
        session_factory: AiohttpSessionFactory,
        dmarket_auth: DMarketAuth,
        game_id: str, # e.g., 'a8db' for CS:GO
        currency: str = "USD",
        items_per_page: int = 100,
        api_request_delay_seconds: float = 1.0,
    ):
        """
        Инициализация парсера.

        Args:
            session_factory: Фабрика для создания aiohttp сессий.
            dmarket_auth: Экземпляр для аутентификации запросов DMarket.
            game_id: ID игры на DMarket.
            currency: Валюта для запроса цен.
            items_per_page: Количество предметов на странице API.
            api_request_delay_seconds: Задержка между запросами к API.
        """
        self._session_factory = session_factory
        self._dmarket_auth = dmarket_auth
        self._game_id = game_id
        self._currency = currency
        self._items_per_page = items_per_page
        self._api_request_delay = api_request_delay_seconds
        # Add logger if needed: self._logger = logging.getLogger(__name__)

    async def _make_api_request(
        self, session: aiohttp.ClientSession, params: dict
    ) -> Optional[dict]:
        """
        Выполняет один запрос к API /market/items.
        """
        endpoint = "/market/items"
        url = f"{self.BASE_URL}{endpoint}"
        method = "GET"

        # Add authentication headers using dmarket_auth
        headers = self._dmarket_auth.get_auth_headers(method=method, api_path=endpoint, params=params)
        # Add other necessary headers like 'Content-Type': 'application/json' if needed

        try:
            async with session.get(url, params=params, headers=headers, timeout=30) as response:
                response.raise_for_status() # Check for HTTP errors
                # self._logger.debug(f"DMarket API request to {url} with params {params} successful.")
                return await response.json() # Use orjson if preferred
        except aiohttp.ClientError as e:
            # self._logger.error(f"Error during DMarket API request to {url}: {e}")
            print(f"Error during DMarket API request to {url}: {e}") # Placeholder for logging
            return None
        except asyncio.TimeoutError:
            # self._logger.error(f"Timeout during DMarket API request to {url}")
            print(f"Timeout during DMarket API request to {url}") # Placeholder for logging
            return None

    async def parse(self) -> Tuple[List[DMarketItem], List[Exception]]:
        """
        Основной метод парсинга. Получает все предметы для указанной игры.
        """
        all_items: List[DMarketItem] = []
        errors: List[Exception] = []
        cursor = None
        page_num = 1

        async with self._session_factory.create_session() as session:
            while True:
                # self._logger.info(f"Fetching page {page_num} for game {self._game_id}...")
                print(f"Fetching page {page_num} for game {self._game_id}...") # Placeholder
                params = {
                    "gameId": self._game_id,
                    "currency": self._currency,
                    "limit": str(self._items_per_page),
                    # Add other params like 'orderBy', 'orderDir', 'treeFilters' if needed
                }
                if cursor:
                    params["cursor"] = cursor

                try:
                    data = await self._make_api_request(session, params)

                    if not data or "objects" not in data:
                        print(f"No 'objects' in response or request failed for page {page_num}.")
                        break # Stop if no data or error

                    items_on_page = data.get("objects", [])

                    for item_data in items_on_page:
                        try:
                            # Extract price safely and convert from cents string to float dollars
                            price_str = item_data.get("price", {}).get(self._currency)
                            price_usd_float = None
                            if price_str:
                                try:
                                    price_usd_float = float(price_str) / 100.0
                                except (ValueError, TypeError):
                                    # self._logger.warning(f"Could not convert price '{price_str}' to float for item {item_data.get('itemId')}")
                                    print(f"Could not convert price '{price_str}' to float for item {item_data.get('itemId')}")
                                    # Decide how to handle items with invalid price - skip or set price to None/0?
                                    # Skipping for now:
                                    continue
                            else:
                                # Handle items without price in the specified currency - skip or default?
                                # Skipping for now:
                                continue

                            # Create DMarketItem instance using data from API response
                            item = DMarketItem(
                                item_id=item_data.get("itemId"),
                                class_id=item_data.get("classId"),
                                game_id=self._game_id, # Already known from parser context
                                title=item_data.get("title"),
                                price_usd=price_usd_float, # Use the converted float value
                                tradable=item_data.get("tradable", True), # Default to True if missing
                                image_url=item_data.get("image"), # Use .get() for optional fields
                                float_value=item_data.get("float"),
                                paint_seed=item_data.get("paintSeed"),
                                phase=item_data.get("phase"),
                            )
                            # Basic validation (ensure required fields are present)
                            if not all([item.item_id, item.class_id, item.title]):
                                # self._logger.warning(f"Skipping item due to missing required fields: {item_data}")
                                print(f"Skipping item due to missing required fields: {item_data}")
                                continue

                            all_items.append(item)
                        except Exception as e:
                            print(f"Error processing item data: {item_data}. Error: {e}")
                            errors.append(e)

                    # Check for next page cursor
                    cursor = data.get("cursor")
                    if not cursor or not items_on_page:
                        # self._logger.info(f"No more pages found for game {self._game_id}.")
                        print(f"No more pages found for game {self._game_id}.")
                        break # Exit loop if no cursor or no items on the last page

                    page_num += 1
                    # self._logger.debug(f"Moving to next page with cursor: {cursor}")
                    await asyncio.sleep(self._api_request_delay) # Respect API rate limits

                except Exception as e:
                    print(f"An unexpected error occurred during parsing page {page_num}: {e}")
                    errors.append(e)
                    break # Stop parsing this game on critical error

        print(f"Finished parsing for game {self._game_id}. Total items: {len(all_items)}, Errors: {len(errors)}")
        return all_items, errors

    async def run(self):
        # This method might be needed if AbstractParser defines it,
        # otherwise, the main logic is in parse().
        # It could potentially call parse() and handle results (e.g., store them).
        items, errors = await self.parse()
        # Process items and errors (e.g., send to storage/queue)
        print(f"Run finished. Items: {len(items)}, Errors: {len(errors)}")

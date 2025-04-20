"""DMarket API Client implementation."""

import asyncio
import json
# from async_limits import AsyncLimiter  # Comment out unused import
import logging  # Use standard logging
import time
from typing import Any, Dict, Optional

import aiohttp

from common.dmarket_auth import build_signature
# Correct import path based on search results
from price_monitoring.storage.proxy.abstract_proxy_storage import \
    AbstractProxyStorage

logger = logging.getLogger(__name__)  # Initialize standard logger


class DMarketClient:
    """Asynchronous client for interacting with the DMarket API."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        public_key: str,
        session: aiohttp.ClientSession | None = None,
        proxy_storage: AbstractProxyStorage | None = None,
        # limiter: AsyncLimiter | None = None,  # Keep commented out
        limiter: Any | None = None,  # Use Any as a placeholder
    ):
        """Initializes the DMarketClient.

        Args:
            api_key: DMarket API key.
            secret_key: DMarket secret key.
            public_key: DMarket public key.
            session: An optional aiohttp client session.
            proxy_storage: An optional storage for proxies.
            limiter: An optional rate limiter.
        """
        if not public_key or not secret_key:
            # Break line to fix length
            raise ValueError("DMarket API keys (public and secret) are required.")
        self._api_key = api_key
        self._secret_key = secret_key
        self._public_key = public_key
        self._base_url = "https://api.dmarket.com"
        self._session = session
        self._proxy_storage = proxy_storage
        self._limiter = limiter

    async def close_session(self):
        """Closes the aiohttp client session if it was created internally."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Returns the current session or creates a new one."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,  # Use Dict and Optional
        data: Optional[Dict[str, Any]] = None,  # Use Dict and Optional
    ) -> Optional[Dict[str, Any]]:  # Use Dict and Optional
        """Makes an asynchronous request to the DMarket API."""
        session = await self._get_session()
        url = f"{self._base_url}{path}"
        timestamp = str(int(time.time()))
        body_str: str | None = None
        # If data is provided, convert it to a JSON string
        if data is not None:
            body_str = json.dumps(data, separators=(",", ":"))

        signature = build_signature(
            self._public_key,
            self._secret_key,
            method,
            path,
            timestamp,  # Pass timestamp as string
            body_str,
        )

        headers = {
            "X-Api-Key": self._public_key,
            # Break line to fix length
            "X-Request-Sign": (f"dmar ed25519 {signature}"),
            "X-Sign-Timestamp": timestamp,
            "Content-Type": "application/json",
        }

        proxy_url = None
        if self._proxy_storage:
            # Logic to get a proxy from storage - simplified
            # proxies = await self._proxy_storage.get_all()
            # if proxies:
            #     proxy = random.choice(proxies)
            #     proxy_url = str(proxy)
            pass  # Placeholder for actual proxy retrieval logic

        try:
            # Use limiter if available
            # if self._limiter:
            #     await self._limiter.acquire()

            # Break line to fix length
            async with session.request(
                method,
                url,
                headers=headers,
                params=params,
                data=body_str,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=30),  # Use ClientTimeout
            ) as response:
                # ... (rest of the try block remains the same)
                logger.debug(f"Request: {method} {url} | Status: {response.status}")
                # ... (rest of the try block remains the same)

        except aiohttp.ClientConnectionError as e:
            # Break line to fix length
            logger.error(f"DMarket API connection error: {method} {path} - {e}")
            return None
        except asyncio.TimeoutError:
            logger.warning(f"DMarket API request timed out: {method} {path}")
            return None
        except Exception as e:
            # Break line to fix length
            logger.exception(f"An unexpected error occurred during DMarket API request: {e}")
            return None
        # finally:
        # Release limiter if it was used
        # if self._limiter:
        #     self._limiter.release()

    async def get_market_items(
        self,
        game_id: str,
        currency: str = "USD",
        limit: int = 100,
        order_by: str = "price",
        order_dir: str = "asc",
        price_from: Optional[int] = None,
        price_to: Optional[int] = None,
        tree_filters: Optional[str] = None,
        offset: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetches market items based on specified filters."""
        path = "/exchange/v1/market/items"
        params: Dict[str, Any] = {
            "gameId": game_id,
            "currency": currency,
            "limit": str(limit),
            "orderBy": order_by,
            "orderDir": order_dir,
        }
        if price_from is not None:
            params["priceFrom"] = str(price_from)
        if price_to is not None:
            params["priceTo"] = str(price_to)
        if tree_filters:
            params["treeFilters"] = tree_filters
        if offset:
            params["offset"] = offset

        return await self._request("GET", path, params=params)

    async def get_offers_by_title(
        self,
        title: str,
        currency: str = "USD",
        limit: int = 100,
        offset: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetches offers based on item title."""
        path = "/exchange/v1/offers-by-title"
        params: Dict[str, Any] = {
            "title": title,
            "currency": currency,
            "limit": str(limit),
        }
        if offset:
            params["offset"] = offset
        return await self._request("GET", path, params=params)

    async def get_user_offers(
        self,
        status: str,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
        currency: str = "USD",  # Add currency parameter
        limit: int = 100,
        offset: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetches user's offers based on status and other filters."""
        path = "/exchange/v1/user/offers"
        params: Dict[str, Any] = {
            "status": status,
            "currency": currency,
            "limit": str(limit),
        }
        if game_id:
            params["gameId"] = game_id
        if title:
            params["title"] = title
        if offset:
            params["offset"] = offset
        return await self._request("GET", path, params=params)

    async def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Fetches the account balance.

        Ref:
            https://docs.dmarket.com/v1/swagger.html#/Account/getAccountBalance
        """
        path = "/account/v1/balance"
        return await self._request("GET", path)

    async def create_offer(
        self, item_id: str, price_cents: int, currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """Creates a sell offer for an item."""
        path = f"/exchange/v1/offers/{item_id}"
        method = "POST"
        body = {"price": {currency: str(price_cents)}}
        return await self._request(method, path, data=body)

    async def edit_offer(
        self, offer_id: str, price_cents: int, currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """Edits an existing sell offer."""
        path = f"/exchange/v1/offers/{offer_id}"
        method = "PATCH"
        body = {"price": {currency: str(price_cents)}}
        return await self._request(method, path, data=body)

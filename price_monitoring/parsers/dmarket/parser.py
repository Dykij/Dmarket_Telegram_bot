import asyncio
import json
import logging
from typing import Any, Optional

import aiohttp
import aiozipkin as az
from aiozipkin import SpanAbc as Span
from aiozipkin import Tracer

from common.dmarket_auth import build_signature, get_current_timestamp
from common.env_var import DMARKET_PUBLIC_KEY, DMARKET_SECRET_KEY
from price_monitoring.exceptions import (DMarketAPIError, DMarketError, InvalidResponseFormatError,
                                         NetworkError)
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.retries import retry_with_backoff

logger = logging.getLogger(__name__)

BASE_URL = "https://api.dmarket.com"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)
MAX_LOG_BODY_LENGTH = 500
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_OK = 200  # Added constant for status code


async def parse_dmarket_items(
    data: dict[str, Any],
) -> tuple[list[DMarketItem], str]:
    """Parse the DMarket API response.

    Args:
        data: The JSON data from the API response.

    Returns:
        A tuple containing a list of parsed DMarketItem objects and cursor string.
    """
    objects: list[dict[str, Any]] = data.get("objects", [])
    items: list[DMarketItem] = []
    for item_data in objects:
        try:
            market_hash_name = item_data.get("marketHashName")
            item_id = item_data.get("itemId")
            price_dict = item_data.get("price")

            # Check for essential fields
            if not market_hash_name or not item_id or not isinstance(price_dict, dict):
                logger.warning(
                    "Skipping item: missing name/id or invalid price dict: %s",
                    item_data,
                )
                continue

            price_usd_str: Optional[Any] = price_dict.get("USD")
            if price_usd_str is None:
                logger.warning("Skipping item: missing USD price: %s", item_data)
                continue

            if not isinstance(price_usd_str, str):
                logger.warning("Skipping item: non-string USD price: %s", item_data)
                continue

            try:
                price_usd = int(price_usd_str)
            except ValueError:
                logger.warning("Skipping item: invalid USD price format: %s", item_data)
                continue

            item = DMarketItem(
                market_hash_name=market_hash_name,  # type: ignore[call-arg]
                price_usd=price_usd,
                item_id=item_id,
            )
            items.append(item)

        except (TypeError, KeyError, AttributeError) as e:
            logger.warning("Failed to parse item data: %s. Error: %s", item_data, e, exc_info=True)
    cursor: str = data.get("cursor", "")
    return items, cursor


async def _handle_response(
    response: aiohttp.ClientResponse, span: Optional[Span]
) -> tuple[list[DMarketItem], str]:
    """Handle the HTTP response, parse data, and manage tracing."""
    logger.debug("DMarket Response Status: %s", response.status)
    response_text = await response.text()
    log_body = (
        f"{response_text[:MAX_LOG_BODY_LENGTH]}..."
        if len(response_text) > MAX_LOG_BODY_LENGTH
        else response_text
    )
    logger.debug("DMarket Response Body (text): %s", log_body)

    if response.status >= HTTP_STATUS_BAD_REQUEST:
        error_message: str = response_text
        response_body_json: Optional[dict[str, Any]] = None
        try:
            response_body_json = json.loads(response_text)
            if isinstance(response_body_json, dict):
                msg = response_body_json.get("message")
                if isinstance(msg, str):
                    error_message = msg
        except json.JSONDecodeError:
            pass

        error = DMarketAPIError(
            status_code=response.status,
            message=error_message,
            response_body=response_body_json or response_text,
        )

        if span:
            span.tag("error", "true")
            span.tag("error.message", error_message)
            span.tag("http.status_code", str(response.status))

        raise error

    try:
        data: dict[str, Any] = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error("Failed to decode DMarket JSON response: %s", e)
        if span:
            span.tag("error", "true")
            span.tag("error.message", f"Invalid JSON: {e}")
        raise InvalidResponseFormatError(f"Invalid JSON: {e}") from e

    if span:
        span.tag("http.status_code", str(response.status))
        items_list = data.get("objects", [])
        items_count = len(items_list) if isinstance(items_list, list) else 0
        span.tag("items_count", str(items_count))

    items, new_cursor = await parse_dmarket_items(data)
    return items, new_cursor


class DMarketParser:
    def __init__(self, session_factory: Any, trace_config: Optional[Any] = None):
        self._session_factory = session_factory
        self._trace_config = trace_config

    async def fetch_dmarket_items(self, params: dict[str, Any]) -> tuple[list[DMarketItem], str]:
        """Fetch and parse items from the DMarket API."""
        method = "GET"
        path = "/exchange/v1/market/items"
        url = f"{BASE_URL}{path}"
        timestamp = get_current_timestamp()

        request_params = params.copy()
        str_params = {k: str(v) for k, v in request_params.items()}

        signature = build_signature(
            api_key=DMARKET_PUBLIC_KEY,
            secret_key=DMARKET_SECRET_KEY,
            method=method,
            api_path=path,
            timestamp=timestamp,
            body=None,
        )

        headers = {
            "X-Api-Key": DMARKET_PUBLIC_KEY,
            "X-Request-Sign": f"dmar ed25519 {signature}",
            "X-Sign-Date": timestamp,
            "Accept": "application/json",
        }

        tracer: Optional[Tracer] = az.get_tracer()  # Does not require app
        span: Optional[Span] = None
        if tracer:
            span = tracer.new_child()  # Context is inherited by default
            if span:
                span.start()
                span.kind("CLIENT")
                span.name(f"{method} {path}")
                span.tag("http.method", method)
                span.tag("http.url", url)

        try:
            result = await self._execute_request(method, url, headers, str_params, span)
            # Status code tagging happens in _handle_response
            return result
        except Exception as e:
            if span:
                span.tag("error", "true")
                span.tag("error.message", str(e))
                span.tag("error.type", e.__class__.__name__)
            raise
        finally:
            if span:
                span.finish()

    @retry_with_backoff(
        attempts=3,
        initial_delay=1,
        backoff_factor=2,
        retry_exceptions=(NetworkError, asyncio.TimeoutError),
    )
    async def _execute_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        str_params: dict[str, str],
        span: Optional[Span],
    ) -> tuple[list[DMarketItem], str]:
        """Execute the HTTP request with error handling, tracing, and retries."""
        try:
            session_kwargs = {}
            if self._trace_config:
                session_kwargs["trace_configs"] = [self._trace_config]

            async with aiohttp.ClientSession(**session_kwargs) as session:
                logger.debug(
                    "Requesting DMarket: %s %s with params %s",
                    method,
                    url,
                    str_params,
                )
                async with session.get(
                    url, headers=headers, params=str_params, timeout=DEFAULT_TIMEOUT
                ) as response:
                    result: tuple[list[DMarketItem], str] = await _handle_response(response, span)
                    return result

        except asyncio.TimeoutError as e:
            logger.error("Timeout error during DMarket request to %s: %s", url, e, exc_info=True)
            # Error tagging moved to fetch_dmarket_items
            raise NetworkError(f"Timeout error: {e}") from e
        except aiohttp.ClientError as e:
            logger.error("Network error during DMarket request to %s: %s", url, e, exc_info=True)
            # Error tagging moved to fetch_dmarket_items
            raise NetworkError(f"Network error: {e}") from e
        except DMarketAPIError:
            raise  # Already handled in _handle_response
        except InvalidResponseFormatError:
            raise  # Already handled in _handle_response
        except Exception as e:
            logger.exception("Unexpected error during DMarket request to %s: %s", url, e)
            # Error tagging moved to fetch_dmarket_items
            raise DMarketError(f"An unexpected error occurred: {e}") from e

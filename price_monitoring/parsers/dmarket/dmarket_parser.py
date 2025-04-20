import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from common.dmarket_auth import build_signature, get_current_timestamp
from common.env_var import DMARKET_PUBLIC_KEY, DMARKET_SECRET_KEY
from price_monitoring.exceptions import (DMarketAPIError, DMarketError,
                                         InvalidResponseFormatError,
                                         NetworkError)
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory

from ...models.dmarket import DMarketItem

logger = logging.getLogger(__name__)

BASE_URL = "https://api.dmarket.com"


def parse_dmarket_items(data: Dict[str, Any]) -> Tuple[List[DMarketItem], str]:
    """Функция парсинга ответа DMarket API."""
    objects: List[Dict[str, Any]] = data.get("objects", [])
    items: List[DMarketItem] = []

    for item_data in objects:
        try:
            market_hash_name = item_data.get("marketHashName")
            item_id = item_data.get("itemId")
            price_dict = item_data.get("price")

            # Проверяем наличие обязательных полей перед парсингом цены
            if not market_hash_name or not item_id or not isinstance(price_dict, dict):
                logger.warning(
                    f"Skipping item due to missing name, id, or invalid price dict: {item_data}"
                )
                # Пропускаем объект, если не хватает базовых данных или цена не словарь
                continue

            price_usd_str = price_dict.get("USD")
            if price_usd_str is None:
                logger.warning(f"Skipping item due to missing USD price: {item_data}")
                continue  # Пропускаем, если нет цены в USD

            # DMarket API возвращает цену как строку с числом в центах
            # (например "1234" для $12.34)
            price_usd = int(price_usd_str) / 100.0

            # Проверяем, можно ли торговать предметом
            tradable = True
            if "restrictions" in item_data:
                if item_data["restrictions"].get("untradable") is True:
                    tradable = False

            # Создаем объект только если все успешно
            item = DMarketItem(
                market_hash_name=market_hash_name,
                price_usd=price_usd,
                item_id=item_id,
                tradable=tradable,
            )
            items.append(item)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            # Ловим больше типов ошибок и логируем
            logger.warning(f"Failed to parse item data: {item_data}. Error: {e}", exc_info=True)
            # Пропускаем объекты с некорректными данными

    cursor: str = data.get("cursor", "")
    return items, cursor


class DMarketParser:
    """Парсер для DMarket API v1, включая логику HTTP-запросов."""

    def __init__(
        self,
        session_factory: AiohttpSessionFactory,
        public_key: str = DMARKET_PUBLIC_KEY,
        secret_key: str = DMARKET_SECRET_KEY,
    ):
        if not public_key or not secret_key:
            raise ValueError("DMarket API keys (public and secret) are required.")
        self._session_factory = session_factory
        self._public_key = public_key
        self._secret_key = secret_key

    async def parse(self, page_content: str) -> Tuple[List[DMarketItem], str]:
        """
        Парсит HTML-страницу DMarket и извлекает информацию о предметах.

        Args:
            page_content: HTML-страница с DMarket

        Returns:
            Кортеж с списком объектов DMarketItem и строкой курсора
        """
        logger.info(f"Parsing DMarket page content of length: {len(page_content)}")

        items = []
        cursor = ""

        try:
            # Если содержимое страницы является JSON - обрабатываем напрямую
            try:
                data = json.loads(page_content)
                if isinstance(data, dict):
                    return parse_dmarket_items(data)
            except json.JSONDecodeError:
                pass  # Не JSON, продолжаем парсинг HTML

            # Парсинг HTML-страницы
            soup = BeautifulSoup(page_content, "html.parser")

            # Ищем скрипты с данными о предметах
            scripts = soup.find_all("script")
            for script in scripts:
                # DMarket часто хранит данные о предметах в объекте __INITIAL_STATE__
                if script.string and "window.__INITIAL_STATE__" in script.string:
                    try:
                        # Извлекаем JSON из скрипта
                        json_text = (
                            script.string.split("window.__INITIAL_STATE__ = ")[1].split("};")[0]
                            + "}"
                        )
                        data = json.loads(json_text)

                        # Получаем данные о предметах из структуры
                        if "marketItems" in data:
                            market_items = data["marketItems"].get("items", [])
                            for item_data in market_items:
                                try:
                                    # Извлекаем необходимые поля
                                    market_hash_name = item_data.get("title") or item_data.get(
                                        "name"
                                    )
                                    item_id = item_data.get("itemId")
                                    price_usd = (
                                        float(item_data.get("price", {}).get("USD", 0)) / 100.0
                                    )

                                    if market_hash_name and item_id and price_usd > 0:
                                        items.append(
                                            DMarketItem(
                                                market_hash_name=market_hash_name,
                                                price_usd=price_usd,
                                                item_id=item_id,
                                                tradable=not item_data.get("untradable", False),
                                            )
                                        )
                                except Exception as e:
                                    logger.warning(f"Failed to parse item from HTML: {e}")

                            # Ищем курсор для пагинации
                            if "cursor" in data.get("marketItems", {}):
                                cursor = data["marketItems"]["cursor"]
                        break
                    except Exception as e:
                        logger.warning(f"Failed to extract data from script: {e}")

            # Если скрипт не найден, пытаемся искать в HTML
            if not items:
                # Поиск элементов списка предметов
                item_elements = soup.select(".c-market__item, .item-card")
                for item_element in item_elements:
                    try:
                        # Получаем данные из атрибутов или текстового содержимого
                        name_element = item_element.select_one(".item-name, .item-title")
                        price_element = item_element.select_one(".item-price, .price")

                        if name_element and price_element:
                            market_hash_name = name_element.text.strip()
                            price_text = (
                                price_element.text.strip().replace("$", "").replace(",", "")
                            )
                            item_id = item_element.get("data-item-id") or item_element.get("id", "")

                            if market_hash_name and price_text and item_id:
                                price_usd = float(price_text)
                                items.append(
                                    DMarketItem(
                                        market_hash_name=market_hash_name,
                                        price_usd=price_usd,
                                        item_id=item_id,
                                    )
                                )
                    except Exception as e:
                        logger.warning(f"Failed to parse item element: {e}")

        except Exception as e:
            logger.error(f"Error parsing DMarket page: {e}", exc_info=True)

        logger.info(f"Extracted {len(items)} items from DMarket page")
        return items, cursor

    async def get_items(
        self, params: Dict[str, Any], cursor: Optional[str] = None
    ) -> Tuple[List[DMarketItem], str]:
        """Получает и парсит предметы с DMarket API."""
        method = "GET"
        path = "/exchange/v1/market/items"
        url = f"{BASE_URL}{path}"
        timestamp = get_current_timestamp()

        # Добавляем курсор к параметрам, если он есть
        request_params = params.copy()
        if cursor:
            request_params["cursor"] = cursor

        # Преобразуем все значения параметров в строки, как ожидает API
        str_params = {k: str(v) for k, v in request_params.items()}

        # Генерируем подпись
        # Важно: DMarket использует только путь в подписи, без query params
        signature = build_signature(
            api_key=self._public_key,
            secret_key=self._secret_key,
            method=method,
            api_path=path,  # Только путь!
            timestamp=timestamp,
            body=None,  # GET-запрос не имеет тела
        )

        headers = {
            "X-Api-Key": self._public_key,
            "X-Request-Sign": f"dmar ed25519 {signature}",
            "X-Sign-Date": timestamp,
            "Accept": "application/json",  # Указываем, что ожидаем JSON
        }

        try:
            async with self._session_factory.create_session() as session:
                logger.debug(f"Requesting DMarket: {method} {url} with params {str_params}")
                async with session.get(url, headers=headers, params=str_params) as response:
                    logger.debug(f"DMarket Response Status: {response.status}")
                    # Читаем текст для возможных ошибок
                    response_text = await response.text()

                    if response.status >= 400:
                        # Пытаемся извлечь сообщение об ошибке из JSON, если возможно
                        error_message = response_text
                        response_body_json = None
                        try:
                            response_body_json = json.loads(response_text)
                            if (
                                isinstance(response_body_json, dict)
                                and "message" in response_body_json
                            ):
                                error_message = response_body_json["message"]
                        except json.JSONDecodeError:
                            pass  # Оставляем исходный текст ошибки
                        raise DMarketAPIError(
                            status_code=response.status,
                            message=error_message,
                            response_body=response_body_json or response_text,
                        )

                    # Если статус OK, пытаемся парсить JSON
                    try:
                        data = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode DMarket JSON response: {e}")
                        raise InvalidResponseFormatError(f"Invalid JSON received: {e}") from e

                    # Парсим объекты с помощью существующей функции
                    items, new_cursor = parse_dmarket_items(data)
                    return items, new_cursor

        except aiohttp.ClientError as e:
            logger.error(f"Network error during DMarket request: {e}", exc_info=True)
            raise NetworkError(f"Network error: {e}") from e
        except DMarketAPIError:  # Перехватываем, чтобы не попасть в общий Exception
            raise
        # Перехватываем, чтобы не попасть в общий Exception
        except InvalidResponseFormatError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during DMarket request: {e}")
            # Можно перебросить как более общее исключение или специфичное
            raise DMarketError(f"An unexpected error occurred: {e}") from e

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from common.dmarket_auth import build_signature, get_current_timestamp
from common.env_var import (DMARKET_PUBLIC_KEY,  # Импортируем ключи
                            DMARKET_SECRET_KEY)
from price_monitoring.exceptions import (DMarketAPIError, DMarketError,
                                         InvalidResponseFormatError,
                                         NetworkError)
# Используем абсолютные импорты
from price_monitoring.models.dmarket import DMarketItem
from proxy_http.aiohttp_session_factory import \
    AiohttpSessionFactory  # Импортируем фабрику

logger = logging.getLogger(__name__)

BASE_URL = "https://api.dmarket.com"


# Заглушка для функции парсинга, ожидаемой тестом
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
                continue  # Пропускаем объект, если не хватает базовых данных или цена не словарь

            price_usd_str = price_dict.get("USD")
            if price_usd_str is None:
                logger.warning(f"Skipping item due to missing USD price: {item_data}")
                continue  # Пропускаем, если нет цены в USD

            price_usd = int(price_usd_str)  # Преобразуем в int

            # Создаем объект только если все успешно
            item = DMarketItem(
                market_hash_name=market_hash_name,
                price_usd=price_usd,
                item_id=item_id,
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
        session_factory: AiohttpSessionFactory,  # Принимаем фабрику сессий
        public_key: str = DMARKET_PUBLIC_KEY,
        secret_key: str = DMARKET_SECRET_KEY,
    ):
        if not public_key or not secret_key:
            raise ValueError("DMarket API keys (public and secret) are required.")
        self._session_factory = session_factory
        self._public_key = public_key
        self._secret_key = secret_key

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
                    response_text = await response.text()  # Читаем текст для возможных ошибок
                    logger.debug(
                        f"DMarket Response Body (text): {response_text[:500]}..."
                    )  # Логируем начало ответа

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
        except InvalidResponseFormatError:  # Перехватываем, чтобы не попасть в общий Exception
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during DMarket request: {e}")
            # Можно перебросить как более общее исключение или специфичное
            raise DMarketError(f"An unexpected error occurred: {e}") from e

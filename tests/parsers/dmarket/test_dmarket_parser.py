import json
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aiohttp import ClientError

from price_monitoring.exceptions import (DMarketAPIError,
                                         InvalidResponseFormatError,
                                         NetworkError)
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.parsers.dmarket.parser import DMarketParser
# Импортируем фабрику из правильного места
from proxy_http.aiohttp_session_factory import AiohttpSessionFactory

# Пример ответа API, который должен вернуть мок
SAMPLE_API_RESPONSE = {
    "objects": [
        {
            "itemId": "1",
            "marketHashName": "AK-47 | Redline (Field-Tested)",
            "price": {"USD": "1500"},
        }
    ],
    "cursor": "some_cursor",
    "total": 1,
}

# Примеры ответов
SAMPLE_API_RESPONSE_PAGE_2 = {
    "objects": [{"itemId": "2", "marketHashName": "Item 2", "price": {"USD": "2000"}}],
    "cursor": "",  # Конец пагинации
    "total": 1,
}
SAMPLE_API_ERROR_RESPONSE = {"message": "Unauthorized"}


# Фикстура для мока фабрики сессий
@pytest.fixture
def mock_session_factory():
    # Мокаем фабрику сессий
    with patch(
        "proxy_http.aiohttp_session_factory.AiohttpSessionFactory",
        spec=AiohttpSessionFactory,
    ) as MockFactory:
        # Создаем мок самой сессии, который будет возвращаться фабрикой
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        # Настраиваем фабрику, чтобы create_session возвращал наш мок сессии
        MockFactory.return_value.create_session.return_value.__aenter__.return_value = mock_session
        yield MockFactory.return_value  # Возвращаем экземпляр мока фабрики


# Тесты
@pytest.mark.asyncio
async def test_dmarket_parser_get_items_success(mock_session_factory):
    """Тестирует успешное получение и парсинг предметов."""
    # Передаем фиктивные API ключи
    parser = DMarketParser(
        session_factory=mock_session_factory,
        public_key="dummy_public_key",
        secret_key="dummy_secret_key",
    )
    params = {"limit": 100, "currency": "USD"}
    api_url = "https://api.dmarket.com/exchange/v1/market/items"

    # Настраиваем мок ответа
    mock_response_ok = AsyncMock()
    mock_response_ok.status = 200
    # Используем json.dumps для имитации реального ответа
    mock_response_ok.text.return_value = json.dumps(SAMPLE_API_RESPONSE)
    # raise_for_status не должен вызываться при успехе, но на всякий случай
    mock_response_ok.raise_for_status.return_value = None

    # Получаем мок сессии из фабрики
    mock_session = mock_session_factory.create_session.return_value.__aenter__.return_value
    # Настраиваем session.get для возврата успешного ответа
    mock_session.get.return_value.__aenter__.return_value = mock_response_ok

    # Вызываем метод парсера
    items, cursor = await parser.get_items(params=params)

    # Проверки
    assert len(items) == 1
    assert isinstance(items[0], DMarketItem)
    assert items[0].market_hash_name == "AK-47 | Redline (Field-Tested)"
    assert items[0].item_id == "1"
    assert items[0].price_usd == 1500  # Цена парсится как int (центы)
    assert cursor == "some_cursor"

    # Проверяем, что сессия была создана
    mock_session_factory.create_session.assert_called_once()

    # Проверяем вызов session.get
    mock_session.get.assert_called_once()
    call_args, call_kwargs = mock_session.get.call_args
    assert call_args[0] == api_url  # Проверяем URL
    assert call_kwargs["params"] == {
        "limit": "100",
        "currency": "USD",
    }  # Параметры должны быть строками
    # Проверяем наличие заголовков аутентификации (без проверки точной подписи)
    assert "X-Api-Key" in call_kwargs["headers"]
    assert "X-Sign-Date" in call_kwargs["headers"]
    assert "X-Request-Sign" in call_kwargs["headers"]
    assert call_kwargs["headers"]["X-Request-Sign"].startswith("dmar ed25519 ")

    # Проверяем, что был вызван text() для получения тела ответа
    mock_response_ok.text.assert_called_once()


@pytest.mark.asyncio
async def test_dmarket_parser_pagination(mock_session_factory):
    """Тестирует логику пагинации с использованием cursor."""
    # Передаем фиктивные API ключи
    parser = DMarketParser(
        session_factory=mock_session_factory,
        public_key="dummy_public_key",
        secret_key="dummy_secret_key",
    )
    api_url = "https://api.dmarket.com/exchange/v1/market/items"
    params_page1 = {"limit": 1, "currency": "USD"}
    # Параметры для второго запроса (с курсором) формируются внутри get_items
    expected_params_page2_str = {
        "limit": "1",
        "currency": "USD",
        "cursor": "some_cursor",
    }

    # Настраиваем мок для двух вызовов get
    mock_response_page1 = AsyncMock()
    mock_response_page1.status = 200
    mock_response_page1.text.return_value = json.dumps(SAMPLE_API_RESPONSE)  # cursor="some_cursor"

    mock_response_page2 = AsyncMock()
    mock_response_page2.status = 200
    mock_response_page2.text.return_value = json.dumps(SAMPLE_API_RESPONSE_PAGE_2)  # cursor=""

    # Получаем мок сессии
    mock_session = mock_session_factory.create_session.return_value.__aenter__.return_value

    # Настраиваем session.get для возврата разных ответов при разных вызовах
    mock_session.get.side_effect = [
        AsyncMock(__aenter__=AsyncMock(return_value=mock_response_page1)),
        AsyncMock(__aenter__=AsyncMock(return_value=mock_response_page2)),
    ]

    # Вызов 1 (получаем первую страницу)
    items1, cursor1 = await parser.get_items(params=params_page1)

    assert len(items1) == 1
    assert items1[0].item_id == "1"
    assert cursor1 == "some_cursor"

    # Вызов 2 (передаем курсор)
    items2, cursor2 = await parser.get_items(
        params=params_page1, cursor=cursor1
    )  # Передаем курсор явно

    assert len(items2) == 1
    assert items2[0].item_id == "2"
    assert cursor2 == ""  # Конец пагинации

    # Проверяем, что сессия создавалась один раз (переиспользуется)
    # Замечание: текущая реализация mock_session_factory создает новый мок сессии при каждом create_session,
    # но сам create_session вызывается дважды, так как контекстный менеджер используется в get_items.
    # Если бы сессия переиспользовалась, create_session вызывался бы один раз.
    # Проверим, что create_session вызывался дважды
    assert mock_session_factory.create_session.call_count == 2

    # Проверяем вызовы session.get
    assert mock_session.get.call_count == 2
    calls = mock_session.get.call_args_list
    # Вызов 1
    assert calls[0].args[0] == api_url
    assert calls[0].kwargs["params"] == {"limit": "1", "currency": "USD"}
    assert "X-Request-Sign" in calls[0].kwargs["headers"]
    # Вызов 2
    assert calls[1].args[0] == api_url
    assert calls[1].kwargs["params"] == expected_params_page2_str  # Проверяем, что курсор добавлен
    assert "X-Request-Sign" in calls[1].kwargs["headers"]


@pytest.mark.parametrize(
    "status_code, response_body_dict, expected_exception",
    [
        (500, {"message": "Internal Server Error"}, DMarketAPIError),
        (401, SAMPLE_API_ERROR_RESPONSE, DMarketAPIError),  # Используем пример ошибки
        (403, {"message": "Forbidden"}, DMarketAPIError),
        (429, {"message": "Too Many Requests"}, DMarketAPIError),
        (400, "Bad Request Text", DMarketAPIError),  # Случай, когда тело не JSON
    ],
)
@pytest.mark.asyncio
async def test_dmarket_parser_api_http_errors(
    mock_session_factory, status_code, response_body_dict, expected_exception
):  # Убираем auth_headers
    """Тестирует обработку HTTP ошибок от API DMarket."""
    # Передаем фиктивные API ключи
    parser = DMarketParser(
        session_factory=mock_session_factory,
        public_key="dummy_public_key",
        secret_key="dummy_secret_key",
    )
    params = {"limit": 10, "currency": "USD"}
    api_url = "https://api.dmarket.com/exchange/v1/market/items"

    # Настраиваем мок ответа с ошибкой
    mock_response_error = AsyncMock()
    mock_response_error.status = status_code
    # Ответ API может быть JSON или просто текстом
    if isinstance(response_body_dict, dict):
        response_text = json.dumps(response_body_dict)
    else:
        response_text = response_body_dict
    mock_response_error.text.return_value = response_text
    # raise_for_status не должен вызываться, так как статус проверяется вручную
    mock_response_error.raise_for_status.side_effect = ClientError(f"HTTP Error {status_code}")

    # Настраиваем мок сессии для возврата ошибки
    mock_session = mock_session_factory.create_session.return_value.__aenter__.return_value
    mock_session.get.return_value.__aenter__.return_value = mock_response_error

    with pytest.raises(expected_exception) as exc_info:
        await parser.get_items(params=params)

    # Дополнительные проверки для DMarketAPIError
    if expected_exception == DMarketAPIError:
        assert exc_info.value.status_code == status_code
        # Проверяем, что сообщение извлечено правильно
        expected_message = (
            response_body_dict.get("message")
            if isinstance(response_body_dict, dict)
            else response_text
        )
        assert expected_message in str(
            exc_info.value
        )  # Проверяем наличие сообщения в тексте исключения

    # Проверяем вызовы
    mock_session_factory.create_session.assert_called_once()
    mock_session.get.assert_called_once()
    call_args, call_kwargs = mock_session.get.call_args
    assert call_args[0] == api_url
    assert call_kwargs["params"] == {"limit": "10", "currency": "USD"}
    assert "X-Request-Sign" in call_kwargs["headers"]
    mock_response_error.text.assert_called_once()  # Проверяем, что текст ответа был прочитан


@pytest.mark.asyncio
async def test_dmarket_parser_network_error(
    mock_session_factory,
):  # Убираем auth_headers
    """Тестирует обработку сетевой ошибки (например, ConnectionError)."""
    # Передаем фиктивные API ключи
    parser = DMarketParser(
        session_factory=mock_session_factory,
        public_key="dummy_public_key",
        secret_key="dummy_secret_key",
    )
    params = {"limit": 10}

    # Настраиваем мок сессии для выброса сетевой ошибки при вызове get
    mock_session = mock_session_factory.create_session.return_value.__aenter__.return_value
    # Используем aiohttp.ClientError или его подклассы
    mock_session.get.side_effect = ClientError("Connection failed")

    with pytest.raises(NetworkError):  # Ожидаем наше кастомное исключение
        await parser.get_items(params=params)

    # Проверяем вызовы
    mock_session_factory.create_session.assert_called_once()
    mock_session.get.assert_called_once()


@pytest.mark.asyncio
async def test_dmarket_parser_invalid_json(
    mock_session_factory,
):  # Убираем auth_headers
    """Тестирует обработку невалидного JSON ответа."""
    # Передаем фиктивные API ключи
    parser = DMarketParser(
        session_factory=mock_session_factory,
        public_key="dummy_public_key",
        secret_key="dummy_secret_key",
    )

    # Имитируем ошибку при вызове json.loads() внутри парсера, сам .json() не вызывается
    invalid_json_text = "This is not valid JSON"
    mock_response_invalid = AsyncMock()
    mock_response_invalid.status = 200
    mock_response_invalid.text = AsyncMock(return_value=invalid_json_text)

    mock_session = mock_session_factory.create_session.return_value.__aenter__.return_value
    mock_session.get.return_value.__aenter__.return_value = mock_response_invalid

    params = {"limit": 10, "currency": "USD"}

    with pytest.raises(InvalidResponseFormatError):
        await parser.get_items(params=params)

    mock_session_factory.create_session.assert_called_once()
    mock_session.get.assert_called_once()
    mock_response_invalid.text.assert_called_once()  # Проверяем, что текст был прочитан

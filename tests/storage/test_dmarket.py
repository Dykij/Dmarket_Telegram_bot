import json
from unittest.mock import AsyncMock, MagicMock

import pytest
# --- Предполагаемый импорт ошибок Redis ---
import redis.exceptions

from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.storage.dmarket import DMarketStorage

# --- Конец импорта ---

# --- Константа для TTL (пример) ---
EXPECTED_TTL_SECONDS = 3600
# --- Конец константы ---


@pytest.fixture
def mock_redis_client():
    """Фикстура для мокирования клиента Redis."""
    # Используем spec=True для более строгой проверки методов
    client = MagicMock(spec=["set", "get", "delete"])
    # Настраиваем асинхронные моки для методов
    client.set = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)  # По умолчанию ничего не найдено
    client.delete = AsyncMock(return_value=1)  # По умолчанию удален 1 ключ
    return client


@pytest.mark.asyncio
async def test_dmarket_storage_save_item(mock_redis_client):
    """Тестирует сохранение элемента в хранилище с TTL."""
    storage = DMarketStorage(redis_client=mock_redis_client)
    item = DMarketItem(item_id="123", market_hash_name="Test Item", price_usd=1000)

    # Предполагаем, что save_item устанавливает TTL
    await storage.save_item(item)

    expected_key = "dmarket:items:123"
    # ВАЖНО: Убедитесь, что это соответствует реальной сериализации!
    expected_value = json.dumps(item.to_dict())
    # Проверяем вызов set с ключом, значением и TTL (параметр ex)
    mock_redis_client.set.assert_awaited_once_with(
        expected_key,
        expected_value,
        ex=EXPECTED_TTL_SECONDS,  # Проверяем TTL
    )


@pytest.mark.asyncio
async def test_dmarket_storage_get_item_found(mock_redis_client):
    """Тестирует получение существующего элемента."""
    storage = DMarketStorage(redis_client=mock_redis_client)
    item_id = "456"
    expected_key = f"dmarket:items:{item_id}"
    stored_item = DMarketItem(item_id=item_id, market_hash_name="Found Item", price_usd=2000)
    # ВАЖНО: Убедитесь, что это соответствует реальной сериализации!
    stored_value_bytes = json.dumps(stored_item.to_dict()).encode("utf-8")
    mock_redis_client.get.return_value = stored_value_bytes

    retrieved_item = await storage.get_item(item_id)

    mock_redis_client.get.assert_awaited_once_with(expected_key)
    assert retrieved_item is not None
    assert isinstance(retrieved_item, DMarketItem)
    assert retrieved_item.item_id == item_id
    assert retrieved_item.market_hash_name == "Found Item"
    assert retrieved_item.price_usd == 2000


@pytest.mark.asyncio
async def test_dmarket_storage_get_item_not_found(mock_redis_client):
    """Тестирует получение несуществующего элемента."""
    storage = DMarketStorage(redis_client=mock_redis_client)
    item_id = "789"
    expected_key = f"dmarket:items:{item_id}"
    # Мок уже настроен на возврат None по умолчанию
    # mock_redis_client.get.return_value = None

    retrieved_item = await storage.get_item(item_id)

    mock_redis_client.get.assert_awaited_once_with(expected_key)
    assert retrieved_item is None


@pytest.mark.asyncio
async def test_dmarket_storage_delete_item(mock_redis_client):
    """Тестирует удаление элемента."""
    storage = DMarketStorage(redis_client=mock_redis_client)
    item_id = "101"
    expected_key = f"dmarket:items:{item_id}"

    await storage.delete_item(item_id)

    mock_redis_client.delete.assert_awaited_once_with(expected_key)


@pytest.mark.asyncio
async def test_dmarket_storage_save_redis_error(mock_redis_client):
    """Тестирует обработку ошибки Redis при сохранении."""
    # Имитируем ошибку Redis при вызове set
    mock_redis_client.set.side_effect = redis.exceptions.ConnectionError("Cannot connect to Redis")
    storage = DMarketStorage(redis_client=mock_redis_client)
    item = DMarketItem(item_id="err1", market_hash_name="Error Item", price_usd=100)

    # Ожидаем, что хранилище перехватит ошибку Redis и выбросит свою или стандартную
    # Здесь предполагаем, что оно выбрасывает исходную ошибку Redis
    with pytest.raises(redis.exceptions.ConnectionError):
        await storage.save_item(item)


@pytest.mark.asyncio
async def test_dmarket_storage_get_redis_error(mock_redis_client):
    """Тестирует обработку ошибки Redis при получении."""
    # Имитируем ошибку Redis при вызове get
    mock_redis_client.get.side_effect = redis.exceptions.TimeoutError("Redis timeout")
    storage = DMarketStorage(redis_client=mock_redis_client)
    item_id = "err2"

    # Ожидаем, что хранилище вернет None (или выбросит исключение, если логика иная)
    retrieved_item = await storage.get_item(item_id)
    assert retrieved_item is None
    # TODO: Если хранилище должно логировать ошибку, можно использовать `mocker.patch('logging.error')`
    # и `assert_called_once_with(...)` для проверки лога.


@pytest.mark.asyncio
async def test_dmarket_storage_delete_redis_error(mock_redis_client):
    """Тестирует обработку ошибки Redis при удалении."""
    # Имитируем ошибку Redis при вызове delete
    mock_redis_client.delete.side_effect = redis.exceptions.RedisError("Generic Redis Error")
    storage = DMarketStorage(redis_client=mock_redis_client)
    item_id = "err3"

    # Ожидаем, что хранилище перехватит и, возможно, выбросит ошибку
    with pytest.raises(redis.exceptions.RedisError):
        await storage.delete_item(item_id)


@pytest.mark.asyncio
async def test_dmarket_storage_get_item_invalid_json_data(mock_redis_client):
    """Тестирует получение элемента с некорректным JSON в Redis."""
    storage = DMarketStorage(redis_client=mock_redis_client)
    item_id = "bad_json"
    expected_key = f"dmarket:items:{item_id}"
    # Возвращаем байты, которые не являются валидным JSON
    mock_redis_client.get.return_value = b"this is not json {"

    # Ожидаем, что хранилище вернет None при ошибке десериализации
    retrieved_item = await storage.get_item(item_id)

    mock_redis_client.get.assert_awaited_once_with(expected_key)
    assert retrieved_item is None
    # TODO: Проверить логирование ошибки JSONDecodeError, если оно есть.


@pytest.mark.asyncio
async def test_dmarket_storage_get_item_missing_key_in_data(mock_redis_client):
    """Тестирует получение элемента с отсутствующим ключом в JSON."""
    storage = DMarketStorage(redis_client=mock_redis_client)
    item_id = "missing_key"
    expected_key = f"dmarket:items:{item_id}"
    # Возвращаем валидный JSON, но без обязательного поля (например, price_usd)
    invalid_data = {"item_id": item_id, "market_hash_name": "Incomplete Item"}
    mock_redis_client.get.return_value = json.dumps(invalid_data).encode("utf-8")

    # Ожидаем, что хранилище вернет None при ошибке KeyError/TypeError во время from_dict
    retrieved_item = await storage.get_item(item_id)

    mock_redis_client.get.assert_awaited_once_with(expected_key)
    assert retrieved_item is None
    # TODO: Проверить логирование ошибки KeyError/TypeError, если оно есть.

from typing import Any, Dict, Optional

import pytest

from price_monitoring.models.dmarket import \
    DMarketItem  # Убедимся, что импорт есть
from price_monitoring.parsers.dmarket.parser import parse_dmarket_items

# Пример тестовых данных (сырой ответ API DMarket)
SAMPLE_DMARKET_RESPONSE_VALID: Dict[str, Any] = {
    "objects": [
        {
            "itemId": "1",
            "marketHashName": "AK-47 | Redline (Field-Tested)",
            "price": {"USD": "1500"},
            # ... другие поля
        }
    ],
    "cursor": "some_cursor",
    "total": 1,
}

SAMPLE_DMARKET_RESPONSE_EMPTY: Dict[str, Any] = {
    "objects": [],
    "cursor": "",
    "total": 0,
}

SAMPLE_DMARKET_RESPONSE_INVALID_PRICE: Dict[str, Any] = {
    "objects": [
        {
            "itemId": "2",
            "marketHashName": "M4A4 | Howl (Factory New)",
            "price": {"USD": "invalid_price"},  # Некорректная цена
        }
    ],
    "cursor": "another_cursor",
    "total": 1,
}

# Пример ответа DMarket с отсутствующим marketHashName
SAMPLE_DMARKET_RESPONSE_MISSING_NAME = {
    "objects": [{"itemId": "3", "price": {"USD": "500000"}}],  # Нет marketHashName
    "cursor": "final_cursor",
    "total": 1,
}

# --- Добавленные недостающие тестовые данные ---
SAMPLE_DMARKET_RESPONSE_NO_OBJECTS: Dict[str, Any] = {
    # "objects": [], # Ключ objects отсутствует
    "cursor": "no_objects_cursor",
    "total": 0,
}

SAMPLE_DMARKET_RESPONSE_NO_CURSOR: Dict[str, Any] = {
    "objects": [
        {
            "itemId": "4",
            "marketHashName": "AWP | Asiimov",
            "price": {"USD": "3000"},
        }
    ],
    # "cursor": "", # Ключ cursor отсутствует
    "total": 1,
}

SAMPLE_DMARKET_RESPONSE_INVALID_OBJECT: Dict[str, Any] = {
    "objects": [
        {
            "itemId": "5",
            "marketHashName": "Knife | Butterfly Knife",
            "price": "not_a_dict",  # Некорректный формат цены
        }
    ],
    "cursor": "invalid_cursor",
    "total": 1,
}
# --- Конец добавленных недостающих данных ---

# --- Добавленные тестовые данные ---
SAMPLE_DMARKET_RESPONSE_MISSING_ITEM_ID: Dict[str, Any] = {
    "objects": [
        {
            # "itemId": "6", # Отсутствует ID
            "marketHashName": "Glock-18 | Water Elemental",
            "price": {"USD": "500"},
        }
    ],
    "cursor": "missing_id_cursor",
    "total": 1,
}

SAMPLE_DMARKET_RESPONSE_MISSING_PRICE_DICT: Dict[str, Any] = {
    "objects": [
        {
            "itemId": "7",
            "marketHashName": "USP-S | Kill Confirmed",
            # "price": {"USD": "2500"}, # Отсутствует словарь price
        }
    ],
    "cursor": "missing_price_dict_cursor",
    "total": 1,
}

SAMPLE_DMARKET_RESPONSE_MISSING_PRICE_USD: Dict[str, Any] = {
    "objects": [
        {
            "itemId": "8",
            "marketHashName": "M4A1-S | Hyper Beast",
            "price": {"EUR": "4000"},  # Отсутствует ключ USD
        }
    ],
    "cursor": "missing_price_usd_cursor",
    "total": 1,
}
# --- Конец добавленных данных ---


@pytest.mark.parametrize(
    (
        "raw_data",
        "expected_count",
        "expected_item_name",
        "expected_cursor",
        "expected_price",
        "expected_id",
    ),
    [
        (
            SAMPLE_DMARKET_RESPONSE_VALID,
            1,
            "AK-47 | Redline (Field-Tested)",
            "some_cursor",
            1500,
            "1",
        ),
        (SAMPLE_DMARKET_RESPONSE_EMPTY, 0, None, "", None, None),
        # Ожидаем 0 валидных item'ов, т.к. цена не парсится
        # (пропускаем объект)
        (
            SAMPLE_DMARKET_RESPONSE_INVALID_PRICE,
            0,
            None,
            "another_cursor",
            None,
            None,
        ),
        # Ожидаем 0 валидных item'ов, т.к. itemId отсутствует
        # (пропускаем объект)
        (
            SAMPLE_DMARKET_RESPONSE_MISSING_ITEM_ID,
            0,
            None,
            "missing_id_cursor",
            None,
            None,
        ),
        # Ожидаем 0 валидных item'ов, т.к. price отсутствует
        # (пропускаем объект)
        (
            SAMPLE_DMARKET_RESPONSE_MISSING_PRICE_DICT,
            0,
            None,
            "missing_price_dict_cursor",
            None,
            None,
        ),
        # Ожидаем 0 валидных item'ов, т.к. price.USD отсутствует
        # (пропускаем объект)
        (
            SAMPLE_DMARKET_RESPONSE_MISSING_PRICE_USD,
            0,
            None,
            "missing_price_usd_cursor",
            None,
            None,
        ),
        # Ожидаем 0, так как парсер пропускает элементы без имени
        (
            SAMPLE_DMARKET_RESPONSE_MISSING_NAME,
            0,  # ИЗМЕНЕНО: Ожидаем 0, так как парсер пропускает элементы без имени
            None,  # Имя не ожидается
            "final_cursor",
            None,  # Цена не ожидается
            None,  # ID не ожидается
        ),
    ],
)
def test_parse_dmarket_items(
    raw_data: Dict[str, Any],
    expected_count: int,
    expected_item_name: Optional[str],
    expected_cursor: str,
    expected_price: Optional[int],
    expected_id: Optional[str],
):
    """Тестирует основную функцию парсинга ответа DMarket."""
    # Инициализируем переменные перед блоком try
    parsed_items: list[DMarketItem] = []
    cursor: str = ""
    # Предполагаем, что функция не выбрасывает исключений при ошибках
    # парсинга отдельных объектов, а просто пропускает их и,
    # возможно, логирует.
    try:
        parsed_items, cursor = parse_dmarket_items(raw_data)
    except Exception as e:
        pytest.fail(f"Parsing function raised an unexpected exception: {e}")

    assert len(parsed_items) == expected_count
    assert cursor == expected_cursor

    # Проверяем детали первого элемента только если ожидается хотя бы один элемент
    if expected_count > 0:
        assert len(parsed_items) > 0  # Дополнительная проверка для безопасности
        item = parsed_items[0]
        assert isinstance(item, DMarketItem)
        assert item.market_hash_name == expected_item_name
        assert item.price_usd == expected_price
        assert item.item_id == expected_id
    # Если ожидается 0 элементов, остальные проверки пропускаются


def test_parse_dmarket_items_invalid_input_type():
    """Тестирует парсинг при невалидном типе входных данных."""
    # Ожидаем ошибку атрибута или типа при попытке доступа
    # к ключам у не-словаря
    with pytest.raises((AttributeError, TypeError)):
        parse_dmarket_items(["not", "a", "dict"])  # type: ignore


# TODO: Добавить тесты для вспомогательных функций из parser.py, если они есть.

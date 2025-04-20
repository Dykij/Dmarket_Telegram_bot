# filepath: d:\Dmarket_Telegram_bot\price_monitoring\models\dmarket.py
"""
Модели данных для работы с маркетплейсом DMarket.

Модуль содержит классы для представления предметов, пакетов предметов
и истории продаж с маркетплейса DMarket, включая методы сериализации
и десериализации для работы с API и хранилищем данных.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# Неиспользуемый импорт удален
import orjson  # Для быстрой сериализации/десериализации


@dataclass
class DMarketItem:
    """
    Представляет информацию о предмете на маркетплейсе DMarket.

    Класс содержит основные данные о предмете, такие как название,
    цена и идентификатор, а также методы для сериализации и десериализации
    для работы с API и хранилищем.

    Attributes:
        item_id: Уникальный идентификатор предмета на DMarket
        class_id: Идентификатор класса предмета
        game_id: Идентификатор игры предмета
        title: Название предмета (соответствует 'title' в API)
        price_usd: Цена предмета в USD (в долларах, требует конвертации из центов API)
        tradable: Флаг доступности предмета для торговли
        image_url: URL изображения предмета (опционально)
        float_value: Значение float (износа) в виде строки (опционально)
        paint_seed: Значение paint seed (опционально)
        phase: Фаза предмета (опционально)
    """

    item_id: str
    class_id: str
    game_id: str
    title: str # Renamed from market_hash_name
    price_usd: float
    tradable: bool = True
    image_url: Optional[str] = None
    float_value: Optional[str] = None
    paint_seed: Optional[int] = None
    phase: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект в словарь.

        Returns:
            Dict[str, Any]: Словарь с данными предмета
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DMarketItem":
        """
        Создает объект из словаря.

        Args:
            data: Словарь с данными предмета

        Returns:
            DMarketItem: Новый экземпляр класса DMarketItem
        """
        # !!! Важно: При реальном использовании может потребоваться
        # более сложная логика для обработки отсутствующих ключей
        # или преобразования типов (например, price_usd из центов).
        # Пока что предполагаем, что словарь 'data' уже содержит
        # ключи с правильными именами и типами, соответствующими полям класса.
        return cls(**data)

    def dump_bytes(self) -> bytes:
        """
        Сериализует объект в bytes.

        Returns:
            bytes: Сериализованные данные в формате JSON
        """
        return orjson.dumps(self.to_dict())

    @classmethod
    def load_bytes(cls, data: bytes) -> "DMarketItem":
        """
        Создает объект из bytes.

        Args:
            data: Сериализованные данные в формате JSON

        Returns:
            DMarketItem: Новый экземпляр класса DMarketItem
        """
        return cls.from_dict(orjson.loads(data))


@dataclass
class DMarketItemPack:
    """
    Пакет предметов с DMarket.

    Представляет коллекцию предметов DMarket, получаемую или
    отправляемую в API или хранилище данных.

    Attributes:
        items: Список предметов DMarket
    """

    items: List[DMarketItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект в словарь.

        Returns:
            Dict[str, Any]: Словарь с данными пакета предметов
        """
        return {"items": [item.to_dict() for item in self.items]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DMarketItemPack":
        """
        Создает объект из словаря.

        Args:
            data: Словарь с данными пакета предметов

        Returns:
            DMarketItemPack: Новый экземпляр класса DMarketItemPack
        """
        return cls(items=[DMarketItem.from_dict(item) for item in data.get("items", [])])

    def dump_bytes(self) -> bytes:
        """
        Сериализует объект в bytes.

        Returns:
            bytes: Сериализованные данные в формате JSON
        """
        return orjson.dumps(self.to_dict())

    @classmethod
    def load_bytes(cls, data: bytes) -> "DMarketItemPack":
        """
        Создает объект из bytes.

        Args:
            data: Сериализованные данные в формате JSON

        Returns:
            DMarketItemPack: Новый экземпляр класса DMarketItemPack
        """
        return cls.from_dict(orjson.loads(data))


@dataclass
class MarketNamePack:
    """
    Пакет с именами предметов для рынка.

    Представляет коллекцию названий предметов для запросов к API
    или другим операциям с маркетплейсом.

    Attributes:
        items: Список названий предметов
    """

    items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект в словарь.

        Returns:
            Dict[str, Any]: Словарь с данными пакета названий
        """
        return {"items": self.items}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketNamePack":
        """
        Создает объект из словаря.

        Args:
            data: Словарь с данными пакета названий

        Returns:
            MarketNamePack: Новый экземпляр класса MarketNamePack
        """
        return cls(items=data.get("items", []))

    def dump_bytes(self) -> bytes:
        """
        Сериализует объект в bytes.

        Returns:
            bytes: Сериализованные данные в формате JSON
        """
        return orjson.dumps(self.to_dict())

    @classmethod
    def load_bytes(cls, data: bytes) -> "MarketNamePack":
        """
        Создает объект из bytes.

        Args:
            data: Сериализованные данные в формате JSON

        Returns:
            MarketNamePack: Новый экземпляр класса MarketNamePack
        """
        return cls.from_dict(orjson.loads(data))


@dataclass
class DMarketSellHistory:
    """
    История продаж предмета на DMarket.

    Содержит информацию о истории продаж предмета, включая
    количество продаж за неделю и цены по процентилям.

    Attributes:
        market_name: Название предмета
        sold_per_week: Количество проданных предметов за неделю
        price_history: Словарь цен по процентилям (ключ: процентиль, значение: цена)
        is_stable: Флаг стабильности цен предмета
    """

    market_name: str
    sold_per_week: int
    price_history: Dict[int, float] = field(default_factory=dict)
    is_stable: bool = True

    def get(self, percentile: int) -> Optional[float]:
        """
        Получает цену по заданному процентилю.

        Args:
            percentile: Процентиль цены (0-100)

        Returns:
            Optional[float]: Цена для указанного процентиля или None,
                            если процентиль не найден
        """
        return self.price_history.get(percentile)

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект в словарь.

        Returns:
            Dict[str, Any]: Словарь с данными истории продаж
        """
        return asdict(self)

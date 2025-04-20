"""
Модуль содержит классы для работы с очередями предметов DMarket в RabbitMQ.

Определяет структуры данных для хранения информации о предметах DMarket
и их сериализации/десериализации для передачи через очередь сообщений.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from common.rpc.queue_factory import AbstractQueue


@dataclass
class DMarketItem:
    """
    Представляет информацию о предмете DMarket.

    Хранит основные атрибуты предмета: идентификатор игры,
    идентификатор предмета, название, цену и дополнительные данные.

    Attributes:
        game_id: Идентификатор игры, к которой относится предмет
        item_id: Уникальный идентификатор предмета
        title: Название предмета
        price: Цена предмета
        currency: Валюта цены (по умолчанию USD)
        extra: Дополнительные данные о предмете в виде словаря
    """

    game_id: str
    item_id: str
    title: str
    price: float
    currency: str = "USD"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DMarketItemsPayload:
    """
    Пакет данных с предметами DMarket для передачи через очередь сообщений.

    Содержит список предметов DMarket, которые будут обработаны воркером.

    Attributes:
        items: Список предметов DMarket
    """

    items: List[DMarketItem]

    def json(self):
        """
        Преобразует объект в JSON-строку.

        Returns:
            JSON-строка, содержащая данные о предметах
        """
        return json.dumps(
            {
                "items": [
                    {
                        "game_id": item.game_id,
                        "item_id": item.item_id,
                        "title": item.title,
                        "price": item.price,
                        "currency": item.currency,
                        "extra": item.extra,
                    }
                    for item in self.items
                ]
            }
        )


class AbstractDMarketItemQueue(AbstractQueue[DMarketItemsPayload]):
    """
    Абстрактный класс для очереди сообщений с предметами DMarket.

    Определяет интерфейс для публикации и получения пакетов данных
    с предметами.

    Attributes:
        queue_name: Имя очереди сообщений в RabbitMQ
        payload_type: Тип полезной нагрузки сообщений
    """

    queue_name = "DMarketItemQueue"
    payload_type = DMarketItemsPayload

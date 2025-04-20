from collections.abc import Sequence
from typing import Optional

from common.tracer import annotate, trace

from ...storage.dmarket import (AbstractDmarketItemStorage,
                                AbstractDmarketOrdersStorage)
from ..dmarket_fee import DmarketFee
from ..offers import BaseItemOffer, DmarketOrdersOffer
from .abstract_offer_provider import AbstractOfferProvider


class RedisOfferProvider(AbstractOfferProvider):
    """
    Провайдер предложений, использующий Redis в качестве хранилища данных.

    Получает информацию о предметах и ордерах DMarket из Redis и создаёт
    на основе этих данных предложения для показа пользователям в Telegram.

    Важно: Этот класс необходим для сервиса уведомлений, так как предоставляет
    доступ к данным о предметах и ордерах, хранящимся в Redis.

    Attributes:
        dmarket_orders: Хранилище данных об ордерах DMarket
        dmarket_items: Хранилище данных о предметах DMarket
    """

    def __init__(
        self,
        dmarket_orders: AbstractDmarketOrdersStorage,
        dmarket_items: AbstractDmarketItemStorage,
    ):
        """
        Инициализирует провайдер с указанными хранилищами данных.

        Args:
            dmarket_orders: Хранилище данных об ордерах DMarket
            dmarket_items: Хранилище данных о предметах DMarket
        """
        self.dmarket_orders = dmarket_orders
        self.dmarket_items = dmarket_items

    @trace
    async def get_items(
        self, percentage_limit: Optional[float] = None, min_price: Optional[float] = None
    ) -> Sequence[BaseItemOffer]:
        """
        Получает список предложений на основе данных из Redis.

        Извлекает информацию о предметах и ордерах DMarket, фильтрует их по
        указанным критериям и создаёт предложения для пользователей.

        Args:
            percentage_limit: Минимальный процент разницы в цене для фильтрации
            min_price: Минимальная цена предмета для фильтрации

        Returns:
            Последовательность предложений, удовлетворяющих критериям
        """
        dmarket_items_data = await self.dmarket_items.get_all()
        annotate(f"Loaded {len(dmarket_items_data)} items from dmarket")
        dmarket_orders_data = await self.dmarket_orders.get_all()
        annotate(f"Loaded {len(dmarket_orders_data)} items from dmarket orders")

        items = []
        for market_name, (buy_order, _) in dmarket_orders_data.items():
            if not buy_order:
                continue
            if market_name not in dmarket_items_data:
                continue
            dmarket_price = dmarket_items_data[market_name]
            if min_price and dmarket_price < min_price:
                continue
            offer = DmarketOrdersOffer(
                market_name=market_name,
                orig_price=dmarket_price,
                buy_order=DmarketFee.subtract_fee(buy_order),
            )
            if percentage_limit is not None and offer.compute_percentage() < percentage_limit:
                continue
            items.append(offer)

        return items

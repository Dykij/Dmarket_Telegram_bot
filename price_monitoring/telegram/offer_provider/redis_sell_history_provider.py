import logging
from collections.abc import Sequence

from common.tracer import annotate, trace

from ...decorators import timer
from ...storage.dmarket import (AbstractDmarketItemStorage,
                                AbstractDmarketSellHistoryStorage)
from ..dmarket_fee import DmarketFee
from ..offers import BaseItemOffer, DmarketOffer
from .abstract_offer_provider import AbstractOfferProvider

_MIN_SOLD_PER_WEEK = 5

logger = logging.getLogger(__name__)


def _get_percentile(price: float) -> float:
    """
    Определяет процентиль для цены предмета.

    Использует разные процентили для предметов разной стоимости:
    - 50-й процентиль для предметов до 100$
    - 20-й процентиль для предметов от 100$

    Args:
        price: Цена предмета

    Returns:
        Соответствующий процентиль
    """
    return 50 if price < 100 else 20


class RedisSellHistoryProvider(AbstractOfferProvider):
    """
    Провайдер предложений, основанный на истории продаж.

    Анализирует историю продаж предметов на DMarket и создает предложения
    на основе исторических данных о ценах и объемах продаж.

    Attributes:
        dmarket_history: Хранилище данных об истории продаж
        dmarket_items: Хранилище данных о предметах DMarket
    """

    def __init__(
        self,
        dmarket_history: AbstractDmarketSellHistoryStorage,
        dmarket_items: AbstractDmarketItemStorage,
    ):
        """
        Инициализирует провайдер с указанными хранилищами данных.

        Args:
            dmarket_history: Хранилище данных об истории продаж
            dmarket_items: Хранилище данных о предметах DMarket
        """
        self.dmarket_history = dmarket_history
        self.dmarket_items = dmarket_items

    @timer(logger)
    @trace
    async def get_items(
        self, percentage_limit: float = None, min_price: float = None
    ) -> Sequence[BaseItemOffer]:
        """
        Получает список предложений на основе истории продаж.

        Извлекает информацию о предметах и истории их продаж,
        фильтрует по указанным критериям и создаёт предложения.

        Args:
            percentage_limit: Минимальный процент разницы в цене для фильтрации
            min_price: Минимальная цена предмета для фильтрации

        Returns:
            Последовательность предложений, удовлетворяющих критериям
        """
        is_trade_ban = self.dmarket_items.is_trade_ban
        dmarket_items_data = await self.dmarket_items.get_all()
        annotate(f"Loaded {len(dmarket_items_data)} items from dmarket")
        dmarket_history_data = await self.dmarket_history.get_all()
        annotate(f"Loaded {len(dmarket_history_data)} items from dmarket history")

        items = []
        for history in dmarket_history_data.values():
            market_name = history.market_name
            if market_name not in dmarket_items_data:
                continue
            if not history.is_stable:
                continue
            if history.sold_per_week < _MIN_SOLD_PER_WEEK:
                continue
            dmarket_price = dmarket_items_data[market_name]
            if min_price and dmarket_price < min_price:
                continue
            percentile = _get_percentile(dmarket_price)
            price_50th = history.get(percentile)
            if not price_50th:
                continue
            offer = DmarketOffer(
                market_name=market_name,
                orig_price=dmarket_price,
                suggested_price=DmarketFee.subtract_fee(price_50th),
                mean_price=price_50th,
                sold_per_week=history.sold_per_week,
                lock_status="TRADEBAN" if is_trade_ban else None,
            )
            if percentage_limit and offer.compute_percentage() < percentage_limit:
                continue
            items.append(offer)

        return items

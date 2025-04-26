import asyncio
import typing
from typing import Optional

from common.tracer import trace
from price_monitoring.telegram.offer_provider.abstract_offer_provider import AbstractOfferProvider
from price_monitoring.telegram.offers.base_item_offer import BaseItemOffer


class ChainProvider(AbstractOfferProvider):
    def __init__(self, offer_providers: typing.Iterable[AbstractOfferProvider]):
        self.offer_providers = offer_providers

    @trace
    async def get_offers(
        self,
        percentage_limit: Optional[float] = None,
        min_price: Optional[float] = None,
    ) -> list[BaseItemOffer]:
        result: list[BaseItemOffer] = []
        tasks = [
            provider.get_offers(percentage_limit=percentage_limit, min_price=min_price)
            for provider in self.offer_providers
        ]
        for array in await asyncio.gather(*tasks):
            result.extend(array)
        return result

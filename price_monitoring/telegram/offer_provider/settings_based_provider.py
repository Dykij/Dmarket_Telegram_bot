from collections.abc import Sequence
from typing import Optional

from common.tracer import trace
from price_monitoring.telegram.bot import AbstractSettings
from price_monitoring.telegram.offers import BaseItemOffer

from .abstract_offer_provider import AbstractOfferProvider


class SettingsBasedProvider(AbstractOfferProvider):
    def __init__(self, settings_provider: AbstractSettings, offer_provider: AbstractOfferProvider):
        self.settings_provider = settings_provider
        self.offer_provider = offer_provider

    @trace
    async def get_items(
        self, percentage_limit: Optional[float] = None, min_price: Optional[float] = None
    ) -> Sequence[BaseItemOffer]:
        settings = await self.settings_provider.get()
        if not settings:
            raise ValueError("Failed to load settings!")
        return await self.offer_provider.get_items(
            percentage_limit=percentage_limit or settings.max_threshold,
            min_price=min_price or settings.min_price,
        )

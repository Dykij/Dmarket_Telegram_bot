from abc import ABC, abstractmethod
from typing import Optional

from price_monitoring.telegram.offers.base_item_offer import BaseItemOffer


class AbstractOfferProvider(ABC):
    @abstractmethod
    async def get_offers(
        self,
        percentage_limit: Optional[float] = None,
        min_price: Optional[float] = None,
    ) -> list[BaseItemOffer]: ...

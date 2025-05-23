from abc import ABC, abstractmethod
from collections.abc import Sequence

from price_monitoring.telegram.offers import BaseItemOffer


class AbstractFilter(ABC):
    @abstractmethod
    async def filter_new_offers(
        self, offers: Sequence[BaseItemOffer]
    ) -> Sequence[BaseItemOffer]: ...

    @abstractmethod
    async def append_offers(self, offers: Sequence[BaseItemOffer]) -> None: ...

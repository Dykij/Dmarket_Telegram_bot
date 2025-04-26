from abc import ABC, abstractmethod
from typing import Optional

from price_monitoring.models.dmarket import DMarketItemPack


class AbstractDmarketItemReader(ABC):
    @abstractmethod
    async def get(self, timeout: int = 5) -> Optional[DMarketItemPack]:
        """Чutaet дahhbie o npeдmetax u3 oчepeдu c yka3ahhbim taйmaytom."""


class AbstractDmarketItemWriter(ABC):
    @abstractmethod
    async def put(self, item: DMarketItemPack) -> None:
        """3anucbiвaet uhфopmaцuю o npeдmetax в oчepeд'."""

from abc import ABC, abstractmethod
from typing import Optional

from price_monitoring.models.dmarket import DMarketItemPack


class AbstractDmarketItemReader(ABC):
    @abstractmethod
    async def get(self, timeout: int = 5) -> Optional[DMarketItemPack]:
        """Читает данные о предметах из очереди с указанным таймаутом."""


class AbstractDmarketItemWriter(ABC):
    @abstractmethod
    async def put(self, item: DMarketItemPack) -> None:
        """Записывает информацию о предметах в очередь."""

from abc import ABC, abstractmethod

from price_monitoring.models.dmarket import DMarketItemPack  # Исправлен регистр


class AbstractDmarketItemProcessor(ABC):
    """Базовый класс для обработчиков предметов с DMarket."""

    @abstractmethod
    async def process(self, pack: DMarketItemPack) -> None:
        """
        Обработать пакет предметов с DMarket.

        Args:
            pack: Пакет предметов с DMarket.
        """

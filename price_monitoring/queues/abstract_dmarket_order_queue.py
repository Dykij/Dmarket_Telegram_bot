from abc import ABC, abstractmethod
from typing import Optional

from price_monitoring.models.dmarket import DMarketItem  # Исправлено с DMarketOrderPack


class AbstractDMarketOrderQueue(ABC):
    """
    Абстрактный класс для очереди ордеров DMarket.

    Определяет интерфейс для добавления и получения ордеров DMarket.
    """

    @abstractmethod
    async def get(self, timeout: int = 5) -> Optional[DMarketItem]:  # Тип изменен на DMarketItem
        """
        Получает ордер из очереди.

        Args:
            timeout: Время ожидания в секундах

        Returns:
            Optional[DMarketItem]: Ордер DMarket или None, если очередь пуста
        """
        raise NotImplementedError

    @abstractmethod
    async def put(self, skin: DMarketItem) -> None:  # Тип изменен на DMarketItem
        """
        Добавляет ордер в очередь.

        Args:
            skin: Ордер DMarket для добавления
        """
        raise NotImplementedError

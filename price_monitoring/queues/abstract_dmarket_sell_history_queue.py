from abc import ABC, abstractmethod
from typing import Optional

from price_monitoring.models.dmarket import DMarketSellHistory  # Исправлено


class AbstractDMarketSellHistoryQueue(ABC):
    """
    Абстрактный класс для очереди истории продаж DMarket.

    Определяет интерфейс для добавления и получения данных
    о истории продаж предметов DMarket.
    """

    @abstractmethod
    async def get(self, timeout: int = 5) -> Optional[DMarketSellHistory]:  # Исправлено
        """
        Получает данные истории продаж из очереди.

        Args:
            timeout: Время ожидания в секундах

        Returns:
            Optional[DMarketSellHistory]: Данные истории продаж или None,
                                         если очередь пуста
        """
        raise NotImplementedError

    @abstractmethod
    async def put(self, history: DMarketSellHistory) -> None:  # Исправлено
        """
        Добавляет данные истории продаж в очередь.

        Args:
            history: Данные истории продаж для добавления
        """
        raise NotImplementedError

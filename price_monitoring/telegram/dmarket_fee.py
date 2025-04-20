# filepath: d:\steam_dmarket-master\price_monitoring\telegram\dmarket_fee.py
import math
from functools import lru_cache


class DmarketFee:
    """
    Класс для расчета комиссий на маркетплейсе DMarket.

    Предоставляет статические методы для расчета цен с учетом комиссий
    маркетплейса DMarket (около 7%), что позволяет точно оценивать
    потенциальную прибыль при торговых операциях.
    """

    @staticmethod
    @lru_cache(maxsize=10**5)
    def subtract_fee(price: float) -> float:
        """
        Вычитает комиссию из цены (для получения чистой прибыли продавца).

        Используется для расчета суммы, которую получит продавец
        после вычета комиссии маркетплейса.

        Args:
            price: Цена предмета (до вычета комиссии)

        Returns:
            float: Цена после вычета комиссии (округленная до 2 знаков)
        """
        if price <= 0.01:
            return 0
        # На DMarket комиссия примерно 7%
        return round(price * 0.93, 2)

    @staticmethod
    @lru_cache(maxsize=10**5)
    def add_fee(price: float) -> float:
        """
        Добавляет комиссию к цене (для расчета цены покупателя).

        Используется для расчета финальной цены, которую заплатит
        покупатель с учетом комиссии маркетплейса.

        Args:
            price: Чистая цена предмета (без комиссии)

        Returns:
            float: Цена с учетом комиссии (округленная до 2 знаков)
        """
        # На DMarket комиссия примерно 7%
        fee = math.floor(price * 7.53) / 100  # Округляем вниз
        return round(price + max(fee, 0.01), 2)

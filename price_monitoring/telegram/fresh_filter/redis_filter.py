"""
Модуль содержит реализацию фильтра на основе Redis для Telegram-уведомлений.

Предоставляет механизм для фильтрации повторяющихся предложений, чтобы
пользователи получали только новые уведомления о выгодных предложениях.

Примечание: Этот модуль подготовлен для будущего использования при расширении
функциональности системы мониторинга цен.
"""

import asyncio
from collections.abc import Awaitable, Sequence
from datetime import timedelta
from typing import Any, List

from aioredis import Redis

from ..offers import BaseItemOffer
from .abstract_filter import AbstractFilter

_ENTRY_TTL = timedelta(minutes=30)


def _key(market_name: str, percent_diff: float) -> str:
    """
    Создаёт уникальный ключ для хранения информации о предложении в Redis.

    Args:
        market_name: Название предмета на рынке
        percent_diff: Процентная разница в цене

    Returns:
        Уникальный ключ для Redis
    """
    return f"cache:withdraw:{market_name}:{percent_diff}"


class RedisFilter(AbstractFilter):
    """
    Фильтр предложений на основе Redis.

    Использует Redis для отслеживания отправленных предложений,
    чтобы избежать повторной отправки одних и тех же уведомлений
    пользователям в течение определённого периода времени.

    Attributes:
        redis: Клиент Redis для хранения информации о предложениях
    """

    def __init__(self, redis: Redis):
        """
        Инициализирует фильтр с клиентом Redis.

        Args:
            redis: Клиент Redis для кэширования предложений
        """
        self.redis = redis

    async def filter_new_offers(self, offers: Sequence[BaseItemOffer]) -> Sequence[BaseItemOffer]:
        """
        Фильтрует список предложений, оставляя только новые.

        Проверяет каждое предложение в Redis и оставляет только те,
        которые ещё не были отправлены пользователям.

        Args:
            offers: Список предложений для фильтрации

        Returns:
            Отфильтрованный список новых предложений
        """
        keys = [_key(offer.market_name, offer.compute_percentage()) for offer in offers]
        values = await self.redis.mget(keys)
        result = []
        for offer, value in zip(offers, values):
            if not value:
                result.append(offer)
        return result

    async def append_offers(self, offers: Sequence[BaseItemOffer]) -> None:
        """
        Добавляет предложения в кэш Redis.

        Помечает предложения как отправленные, чтобы они не были
        отправлены повторно в течение _ENTRY_TTL времени.

        Args:
            offers: Список предложений для добавления в кэш
        """
        tasks: List[Awaitable[Any]] = []
        for offer in offers:
            key = _key(offer.market_name, offer.compute_percentage())
            tasks.append(self.redis.set(key, 1, ex=_ENTRY_TTL))
        await asyncio.gather(*tasks)

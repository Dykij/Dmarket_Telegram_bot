"""
Модуль содержит типовые алиасы для работы с рыночными данными.

Этот модуль определяет типовые алиасы для параметров, связанных с
маркетплейсами. Эти алиасы используются для улучшения типизации и
повышения читаемости кода в других частях системы.
"""

from typing import TypeAlias

MarketName: TypeAlias = str
"""Название маркетплейса."""

NameId: TypeAlias = int  # dmarket identifier
"""Уникальный идентификатор предмета на маркетплейсе DMarket."""

ItemNameId: TypeAlias = int  # dmarket market identifier
"""Уникальный идентификатор типа предмета на маркетплейсе DMarket."""

OrderPrice: TypeAlias = float | None
"""Цена заказа. None если заказ отсутствует."""

BuySellOrders: TypeAlias = tuple[OrderPrice, OrderPrice]
"""Кортеж цен заказов на покупку и продажу."""

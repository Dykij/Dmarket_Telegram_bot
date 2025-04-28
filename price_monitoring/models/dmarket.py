"""DMarket data models.

This module contains models for working with DMarket marketplace data,
including item representation, serialization, and deserialization.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional


@dataclass
class DMarketItem:
    """Represents an item on the DMarket marketplace.

    This class contains basic information about an item, such as name,
    price, and identifier.

    Attributes:
        item_id: Unique item identifier on DMarket
        title: Item name (corresponds to 'title' or 'marketHashName' in API)
        price_usd: Item price in USD (dollars, requires conversion from API cents)
        raw_data: Raw item data from the API (optional)
    """

    item_id: str
    title: str
    price_usd: Decimal
    raw_data: Optional[dict[str, Any]] = None

    @property
    def price(self) -> Decimal:
        """Get the item price as a Decimal for accurate financial calculations.

        Returns:
            Decimal representation of the price in USD
        """
        return self.price_usd

    @property
    def price_in_cents(self) -> int:
        """Get the item price in cents (as used by DMarket API).

        Returns:
            Integer price in cents
        """
        return int(self.price_usd * 100)

    def __str__(self) -> str:
        """String representation of the item.

        Returns:
            Item title and price
        """
        return f"{self.title} (${self.price_usd:.2f})"
        """
        return Decimal(str(self.price_usd))

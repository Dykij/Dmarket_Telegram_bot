# filepath: d:\steam_dmarket-master\price_monitoring\telegram\offers\dmarket_offer.py
from price_monitoring.market_types import MarketName
from price_monitoring.telegram.models import ItemOfferNotification
from price_monitoring.telegram.offers.base_item_offer import BaseItemOffer


class DmarketOffer(BaseItemOffer):
    """Предложение для предмета с DMarket с информацией о средней цене и количестве продаж."""

    def __init__(
        self,
        market_name: MarketName,
        orig_price: float,
        suggested_price: float,
        mean_price: float,
        sold_per_week: int,
    ):
        super().__init__(market_name, orig_price, suggested_price)
        self.mean_price = round(mean_price, 2)
        self.sold_per_week = sold_per_week
        self.tradable = True  # По умолчанию предметы торгуемые

    def create_notification(self) -> ItemOfferNotification:
        short_title = f"AVG ${self.mean_price} | {self.sold_per_week} SOLD IN WEEK"

        if not self.tradable:
            short_title = f"{short_title} | NOT TRADABLE"

        return ItemOfferNotification(
            market_name=self.market_name,
            orig_price=self.orig_price,
            sell_price=self.sell_price,
            short_title=short_title,
        )

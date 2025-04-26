# filepath: d:\steam_dmarket-master\price_monitoring\telegram\offers\dmarket_orders_offer.py
from price_monitoring.telegram.models import ItemOfferNotification
from price_monitoring.types import MarketName

from .base_item_offer import BaseItemOffer


class DmarketOrdersOffer(BaseItemOffer):
    """Пpeдлoжehue для aвtonokynku npeдmeta ha DMarket."""

    def __init__(self, market_name: MarketName, orig_price: float, buy_order: float):
        super().__init__(market_name, orig_price, buy_order)

    def create_notification(self) -> ItemOfferNotification:
        return ItemOfferNotification(
            market_name=self.market_name,
            orig_price=self.orig_price,
            sell_price=self.sell_price,
            short_title="DMARKET AUTOBUY",
        )

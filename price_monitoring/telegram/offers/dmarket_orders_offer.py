# filepath: d:\steam_dmarket-master\price_monitoring\telegram\offers\dmarket_orders_offer.py
from ...types import MarketName
from ..models import ItemOfferNotification
from .base_item_offer import BaseItemOffer


class DmarketOrdersOffer(BaseItemOffer):
    """Предложение для автопокупки предмета на DMarket."""

    def __init__(self, market_name: MarketName, orig_price: float, buy_order: float):
        super().__init__(market_name, orig_price, buy_order)

    def create_notification(self) -> ItemOfferNotification:
        return ItemOfferNotification(
            market_name=self.market_name,
            orig_price=self.orig_price,
            sell_price=self.sell_price,
            short_title="DMARKET AUTOBUY",
        )

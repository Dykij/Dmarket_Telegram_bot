# Тест для DmarketOrdersOffer
import pytest

from price_monitoring.telegram.offers import DmarketOrdersOffer


@pytest.fixture()
def offer():
    return DmarketOrdersOffer(market_name="AK-47 | Redline", orig_price=10.5, buy_order=12.0)


def test_create_notification(offer):
    notification = offer.create_notification()

    assert notification.short_title == "DMARKET AUTOBUY"
    assert notification.market_name == "AK-47 | Redline"
    assert notification.orig_price == 10.5
    assert notification.sell_price == 12.0

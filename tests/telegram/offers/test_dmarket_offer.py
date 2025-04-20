# Тест для DmarketOffer
import pytest

from price_monitoring.telegram.offers import DmarketOffer


@pytest.fixture()
def offer():
    return DmarketOffer(
        market_name="AK-47 | Redline",
        orig_price=10.5,
        suggested_price=12.0,
        mean_price=12.1,
        sold_per_week=75,
    )


@pytest.mark.parametrize("tradable", [True, False])
def test_create_notification(offer, tradable):
    offer.tradable = tradable
    notification = offer.create_notification()

    if not tradable:
        assert notification.short_title == "AVG $12.1 | 75 SOLD IN WEEK | NOT TRADABLE"
    else:
        assert notification.short_title == "AVG $12.1 | 75 SOLD IN WEEK"
    assert notification.market_name == "AK-47 | Redline"
    assert notification.orig_price == 10.5
    assert notification.sell_price == 12.0

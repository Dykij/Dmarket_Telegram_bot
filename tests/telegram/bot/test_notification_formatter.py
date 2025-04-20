import html  # Добавим импорт html

# Исправляем импорт: импортируем существующие функции
from price_monitoring.telegram.bot.notification_formatter import (
    several_to_html, to_html)
from price_monitoring.telegram.dmarket_fee import DmarketFee
from price_monitoring.telegram.models import ItemOfferNotification


def test_to_html():  # Переименован тест
    notification = ItemOfferNotification(
        market_name="Test Item > Name",
        orig_price=10.0,
        sell_price=8.0,
        short_title="Test Title",
    )
    price_with_fee = DmarketFee.add_fee(notification.sell_price)
    # Ожидаем HTML-форматированный вывод
    expected = (
        f"{html.escape(notification.market_name)}\n"
        f"<b>{notification.compute_percentage_diff()}%</b>  "
        f"{html.escape(f'${notification.orig_price}')} \\-\\> "  # Оставляем -> как есть
        f"{html.escape(f'${notification.sell_price}')} "
        f"{html.escape(f'(${price_with_fee})')}  "
        f"<i>{html.escape(notification.short_title)}</i>"  # Экранируем title внутри <i>
    )
    # Используем to_html
    assert to_html(notification) == expected


def test_several_to_html():  # Переименован тест
    notifications = [
        ItemOfferNotification(market_name="Item 1", orig_price=10, sell_price=9, short_title="T1"),
        ItemOfferNotification(market_name="Item 2", orig_price=20, sell_price=15, short_title="T2"),
    ]
    # Используем to_html для генерации ожидаемых строк
    expected = f"{to_html(notifications[0])}\n\n{to_html(notifications[1])}"
    # Используем several_to_html
    assert several_to_html(notifications) == expected

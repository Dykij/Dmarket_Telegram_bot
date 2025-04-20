"""
Форматирование уведомлений для Telegram-бота.

Модуль предоставляет функции для форматирования уведомлений о предложениях
в HTML-разметке, подходящей для отправки через Telegram API.
"""

import html
from collections.abc import Iterable

from aiogram.utils.markdown import hbold, hitalic

from ..dmarket_fee import DmarketFee
from ..models import ItemOfferNotification


def to_html(notification: ItemOfferNotification) -> str:
    """
    Форматирует уведомление в HTML-строку для отправки в Telegram.

    Создает форматированное сообщение с информацией о предложении,
    включая название предмета, процентное соотношение цен, исходную цену,
    цену продажи и цену с учетом комиссии.

    Args:
        notification: Объект уведомления с информацией о предложении

    Returns:
        str: Форматированная HTML-строка для отправки в Telegram
    """
    price_with_fee = DmarketFee.add_fee(notification.sell_price)
    # Пример: <b>10.0%</b> $1.14 -> $0.98 ($0.98) <i>AUTOBUY</i>
    # Используем HTML-экранирование и форматтеры
    block = "{}  {} \\-\\> {} {}  {}".format(
        hbold(f"{notification.compute_percentage_diff()}%"),
        html.escape(f"${notification.orig_price}"),
        html.escape(f"${notification.sell_price}"),
        html.escape(f"(${price_with_fee})"),
        hitalic(notification.short_title),
    )
    # Добавляем имя предмета в начало, экранируя его
    return f"{html.escape(notification.market_name)}\n{block}"


def several_to_html(
    notifications: Iterable[ItemOfferNotification],
) -> str:
    """
    Объединяет несколько уведомлений в одно сообщение.

    Форматирует каждое уведомление с помощью to_html и объединяет их
    в одно сообщение для отправки, разделяя двойным переносом строки.

    Args:
        notifications: Итерируемый объект с уведомлениями

    Returns:
        str: Объединенная HTML-строка для отправки в Telegram
    """
    return "\n\n".join(to_html(notification) for notification in notifications)

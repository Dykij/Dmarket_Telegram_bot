"""
Модели данных для работы с Telegram-ботом.

Модуль содержит классы для настроек уведомлений и представления
уведомлений о предложениях, отправляемых через Telegram-бота.
"""

from dataclasses import dataclass

from marshmallow_dataclass import add_schema

from common.core.dataclass_json import JsonMixin

from ..market_types import MarketName


@add_schema
@dataclass
class NotificationSettings(JsonMixin):
    """
    Настройки уведомлений для Telegram-бота.

    Содержит пороговые значения для фильтрации предложений
    перед отправкой уведомлений пользователям.

    Attributes:
        max_threshold: Максимальный порог разницы цен в процентах
        min_price: Минимальная цена предмета для отправки уведомлений
    """

    max_threshold: float = 0
    min_price: float = 10


@add_schema
@dataclass
class ItemOfferNotification(JsonMixin):
    """
    Уведомление о предложении предмета для отправки в Telegram.

    Представляет информацию о предложении, которая будет отправлена
    пользователям через Telegram-бота, включая информацию о ценах
    и форматированный текст сообщения.

    Attributes:
        market_name: Название предмета на маркетплейсе
        orig_price: Исходная/рыночная цена предмета
        sell_price: Цена продажи предмета
        short_title: Краткое описание предложения
        text: Полный текст уведомления
        preview_links: Флаг для включения предпросмотра ссылок
    """

    market_name: MarketName
    orig_price: float
    sell_price: float
    short_title: str
    text: str = ""
    preview_links: bool = False

    def compute_percentage_diff(self) -> float:
        """
        Вычисляет процентную разницу между исходной ценой и ценой продажи.

        Возвращает отрицательное значение, если цена продажи ниже исходной
        (выгодное предложение), и положительное, если выше.

        Returns:
            float: Процентная разница между ценами, округлённая до 2 знаков
        """
        return round((self.sell_price - self.orig_price) / self.orig_price * 100, 2)

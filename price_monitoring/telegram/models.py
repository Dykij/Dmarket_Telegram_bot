"""
Модели данных для работы с Telegram-ботом.

Модуль содержит классы для настроек уведомлений и представления
уведомлений о предложениях, отправляемых через Telegram-бота.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Union

from marshmallow_dataclass import add_schema

from common.core.dataclass_json import JsonMixin

from ..market_types import MarketName


class NotificationType(Enum):
    """
    Типы уведомлений, поддерживаемые Telegram-ботом.

    Определяет различные типы уведомлений, которые могут быть отправлены
    пользователям через Telegram-бота.

    Attributes:
        TEXT: Простое текстовое уведомление
        IMAGE: Уведомление с изображением
        PHOTO_GROUP: Группа изображений (до 10 фото)
        DOCUMENT: Документ (файл)
        VIDEO: Видео
        ANIMATION: Анимация (GIF)
    """
    TEXT = auto()
    IMAGE = auto()
    PHOTO_GROUP = auto()
    DOCUMENT = auto()
    VIDEO = auto()
    ANIMATION = auto()


@add_schema
@dataclass
class InlineButton(JsonMixin):
    """
    Кнопка для встроенной клавиатуры Telegram.

    Представляет одну кнопку в интерактивной клавиатуре,
    которая может быть прикреплена к сообщению.

    Attributes:
        text: Текст, отображаемый на кнопке
        callback_data: Данные, отправляемые боту при нажатии на кнопку
        url: URL, открываемый при нажатии на кнопку (опционально)
    """
    text: str
    callback_data: str
    url: Optional[str] = None


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
    пользователям через Telegram-бота, включая информацию о ценах,
    форматированный текст сообщения и медиа-контент.

    Attributes:
        market_name: Название предмета на маркетплейсе
        orig_price: Исходная/рыночная цена предмета
        sell_price: Цена продажи предмета
        short_title: Краткое описание предложения
        text: Полный текст уведомления
        preview_links: Флаг для включения предпросмотра ссылок
        notification_type: Тип уведомления (текст, изображение и т.д.)
        media_url: URL медиа-контента (изображение, видео и т.д.)
        media_urls: Список URL для группы изображений
        caption: Подпись к медиа-контенту
        buttons: Список кнопок для интерактивной клавиатуры
        button_rows: Список рядов кнопок для более сложных клавиатур
    """

    market_name: MarketName
    orig_price: float
    sell_price: float
    short_title: str
    text: str = ""
    preview_links: bool = False
    notification_type: NotificationType = NotificationType.TEXT
    media_url: Optional[str] = None
    media_urls: List[str] = field(default_factory=list)
    caption: Optional[str] = None
    buttons: List[InlineButton] = field(default_factory=list)
    button_rows: List[List[InlineButton]] = field(default_factory=list)

    def compute_percentage_diff(self) -> float:
        """
        Вычисляет процентную разницу между исходной ценой и ценой продажи.

        Возвращает отрицательное значение, если цена продажи ниже исходной
        (выгодное предложение), и положительное, если выше.

        Returns:
            float: Процентная разница между ценами, округлённая до 2 знаков
        """
        return round((self.sell_price - self.orig_price) / self.orig_price * 100, 2)

"""
Команда для отображения доступных предложений.
"""

import logging

from aiogram import types

from ...bot.notification_formatter import several_to_html
from ...offer_provider import AbstractOfferProvider
from ..abstract_command import AbstractCommand

_COMMAND = "offers"
_MAX_MESSAGE_LENGTH = 4000  # Приблизительный максимальный размер сообщения Telegram

logger = logging.getLogger(__name__)


class Offers(AbstractCommand):
    """
    Команда для получения списка доступных предложений.
    """

    def __init__(self, offer_provider: AbstractOfferProvider):
        """
        Инициализация команды.

        Args:
            offer_provider: Провайдер предложений, из которого будут получены данные.
        """
        super().__init__(_COMMAND)
        self.offer_provider = offer_provider

    async def handler(self, message: types.Message) -> None:
        """
        Обработчик команды /offers.
        Получает список предложений и отправляет их пользователю.
        Если предложений слишком много, разбивает на несколько сообщений.

        Args:
            message: Сообщение от пользователя.
        """
        try:
            offers = await self.offer_provider.get_items()

            if not offers:
                await message.reply("Нет доступных предложений")
                return

            # Сортируем предложения (например, по имени)
            offers = sorted(offers, key=lambda x: x.market_name)

            # Форматируем предложения в HTML
            formatted_offers = []
            for offer in offers:
                notification = offer.create_notification()
                formatted_offers.append(notification)

            # Разбиваем на части, если текст слишком длинный
            texts = []
            current_text = []
            current_length = 0

            for notification in formatted_offers:
                html = several_to_html([notification])
                if current_length + len(html) > _MAX_MESSAGE_LENGTH and current_text:
                    # Если текущий блок будет слишком большим, сохраняем предыдущий
                    texts.append(several_to_html(current_text))
                    current_text = [notification]
                    current_length = len(html)
                else:
                    current_text.append(notification)
                    current_length += len(html)

            # Добавляем последний блок
            if current_text:
                texts.append(several_to_html(current_text))

            # Отправляем сообщения
            for text in texts:
                await message.reply(text, parse_mode="HTML")

        except Exception as e:
            logger.exception(f"Ошибка при получении предложений: {e}")
            await message.reply(f"Ошибка при получении предложений: {e!s}")

import asyncio
from collections.abc import Iterable
from typing import Optional

from aiogram import Bot, Dispatcher

from ..models import ItemOfferNotification
from .abstract_bot import AbstractBot
from .abstract_command import AbstractCommand
from .abstract_whitelist import AbstractWhitelist


class AiogramBot(AbstractBot):
    """
    Реализация бота Telegram на основе библиотеки aiogram.

    Обеспечивает взаимодействие с API Telegram для отправки уведомлений
    и обработки команд от пользователей.

    Attributes:
        _whitelist: Объект для работы с белым списком пользователей
        commands: Список поддерживаемых команд
        _bot: Экземпляр класса Bot из aiogram
        _dispatcher: Экземпляр класса Dispatcher из aiogram
        _polling_task: Задача, представляющая процесс опроса серверов Telegram
    """

    def __init__(
        self,
        token: str,
        whitelist: AbstractWhitelist,
        commands: Iterable[AbstractCommand],
    ):
        """
        Инициализирует бота с указанным токеном и настройками.

        Args:
            token: Токен API Telegram
            whitelist: Объект для работы с белым списком пользователей
            commands: Список поддерживаемых команд
        """
        self._whitelist = whitelist
        self.commands = commands
        self._bot = Bot(token=token, parse_mode="HTML")
        self._dispatcher = Dispatcher()
        self._polling_task: Optional[asyncio.Task] = None

    async def start(self):
        """
        Запускает бота и начинает обработку входящих сообщений.

        Регистрирует все команды и запускает процесс опроса серверов
        Telegram.
        """
        members = await self._whitelist.get_members()
        for command in self.commands:
            command.register_command(self._dispatcher, members)
        self._polling_task = asyncio.create_task(
            # В aiogram 3.0 первый аргумент метода start_polling
            # должен быть экземпляром бота (позиционный аргумент, а не keyword)
            self._dispatcher.start_polling(self._bot)
        )

    async def notify(self, notification: ItemOfferNotification):
        """
        Отправляет уведомление всем пользователям из белого списка.

        Args:
            notification: Объект уведомления для отправки
        """
        members = await self._whitelist.get_members()
        tasks = []
        for chat_id in members:
            task = asyncio.create_task(
                self._bot.send_message(
                    chat_id=chat_id,
                    text=notification.text,
                    parse_mode="HTML",
                    disable_web_page_preview=not notification.preview_links,
                )
            )
            tasks.append(task)
        await asyncio.gather(*tasks)

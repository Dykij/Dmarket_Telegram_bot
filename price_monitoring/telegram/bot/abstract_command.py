"""
Абстрактный интерфейс команд для Telegram-бота.

Модуль предоставляет базовую абстракцию для команд бота, упрощая
создание новых команд и их регистрацию в диспетчере событий.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from aiogram import Dispatcher, types


class AbstractCommand(ABC):
    """
    Абстрактный базовый класс для команд Telegram-бота.

    Предоставляет базовую функциональность для регистрации команд
    в диспетчере событий и обработки сообщений. Конкретные команды
    должны наследоваться от этого класса и реализовывать метод handler.

    Attributes:
        name: Имя команды (без символа '/')
    """

    def __init__(self, name: str):
        """
        Инициализирует команду с заданным именем.

        Args:
            name: Имя команды (без символа '/')
        """
        self.name = name

    def register_command(self, dispatcher: Dispatcher, members: Iterable[int]):
        """
        Регистрирует команду в диспетчере событий.

        Связывает команду с методом-обработчиком и ограничивает
        доступ к команде только для пользователей из белого списка.

        Args:
            dispatcher: Диспетчер событий aiogram
            members: Список ID пользователей, имеющих доступ к команде
        """
        dispatcher.message_handler(commands=[self.name], user_id=members)(self.handler)

    @abstractmethod
    async def handler(self, message: types.Message) -> None:
        """
        Обрабатывает сообщение с командой.

        Этот метод должен быть реализован в производных классах
        для определения конкретного поведения команды.

        Args:
            message: Объект сообщения от пользователя
        """
        ...

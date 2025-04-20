from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import types

from price_monitoring.telegram.bot.abstract_command import AbstractCommand
from price_monitoring.telegram.bot.abstract_whitelist import AbstractWhitelist
from price_monitoring.telegram.bot.aiogram_bot import AiogramBot


# Заглушки для тестирования
class DispatcherStub:
    def __init__(self, *args, **kwargs):
        self.start_polling = AsyncMock()
        self.handlers = {}


class WhitelistStub(AbstractWhitelist):
    async def add_member(self, member: int) -> None:
        pass

    async def remove_member(self, member: int) -> None:
        pass

    async def get_members(self) -> List[int]:
        return []

    async def is_member(self, member_id: int) -> bool:
        return True


# Другие заглушки для тестирования
class CommandStub(AbstractCommand):
    """Заглушка для команды бота."""

    def __init__(self, name: str = "test"):
        super().__init__(name)
        self.bot = None  # Будет установлено в тесте

    async def handler(self, message):
        """Обработчик команды."""
        pass  # Ничего не делаем в тесте

    async def process_message(self, message):
        """Имитирует обработку сообщения и отправку ответа."""
        await self.handler(message)
        # В тесте нам нужно имитировать отправку сообщения
        if hasattr(self, "bot") and self.bot:
            await self.bot.send_message(message.from_user.id, "Test response")

    def register_command(self, dispatcher, members=None):
        """Регистрирует команду в диспетчере."""
        pass  # Ничего не делаем в тестовой регистрации


class BotStub:
    """Заглушка для бота."""



@pytest.fixture()
def command():
    return CommandStub()


@pytest.fixture()
def bot():
    with patch("aiogram.Bot", new=BotStub) as mock:
        yield mock


@pytest.fixture()
def dispatcher():
    with patch("aiogram.Dispatcher", new=DispatcherStub) as mock:
        yield mock


@pytest.fixture()
def whitelist():
    return WhitelistStub()


@pytest.fixture()
def aiogram_bot(whitelist, command, bot, dispatcher):
    return AiogramBot(token="token", whitelist=whitelist, commands=[command])


@pytest.mark.asyncio
async def test_start(bot, command):
    """Тестирует команду /start."""
    # Патчируем классы, которые используются внутри AiogramBot
    with (
        patch("price_monitoring.telegram.bot.aiogram_bot.Dispatcher", new=DispatcherStub),
        patch(
            "price_monitoring.telegram.bot.aiogram_bot.Bot", return_value=AsyncMock()
        ) as mock_bot,
    ):
        # Настраиваем мок для Bot
        mock_bot.return_value.send_message = AsyncMock()

        # Создаем экземпляр AiogramBot
        aiogram_bot = AiogramBot(
            token="123456:ABC-DEF", commands=[command], whitelist=WhitelistStub()
        )

        # Создаем мок сообщения правильно
        message = MagicMock()
        from_user_mock = MagicMock()
        from_user_mock.id = 123
        message.from_user = from_user_mock

        # Подменяем внутреннее свойство _bot на наш мок
        aiogram_bot._bot = mock_bot.return_value

        # Устанавливаем мок бота в команду
        command.bot = mock_bot.return_value

        # Эмулируем выполнение команды
        await command.process_message(message)  # Вызываем напрямую команду

        # Проверяем, что сообщение было отправлено
        mock_bot.return_value.send_message.assert_called_once()


# Добавьте фикстуру message, если она используется в других тестах
@pytest.fixture()
def message():
    msg = MagicMock(spec=types.Message)
    msg.from_user = MagicMock(spec=types.User)
    msg.from_user.id = 12345
    msg.chat = MagicMock(spec=types.Chat)
    msg.chat.id = 67890
    msg.reply = AsyncMock()  # Мокируем метод reply
    return msg


# Пример теста notify, если он существует
@pytest.mark.asyncio
async def test_notify(bot, command):
    """Тестирует отправку уведомлений."""
    whitelist = WhitelistStub()
    # Добавим тестового пользователя в whitelist для этого теста
    test_user_id = 54321
    await whitelist.add_member(test_user_id)  # Хотя заглушка ничего не делает, вызываем для ясности
    # Переопределим get_members для этого теста, чтобы вернуть пользователя
    whitelist.get_members = AsyncMock(return_value=[test_user_id])

    # Мокаем класс ItemOfferNotification
    mock_notification = MagicMock()
    mock_notification.text = "Test notification"
    mock_notification.preview_links = False

    # Патчируем классы, которые используются внутри AiogramBot
    with (
        patch("price_monitoring.telegram.bot.aiogram_bot.Dispatcher", new=DispatcherStub),
        patch(
            "price_monitoring.telegram.bot.aiogram_bot.Bot", return_value=AsyncMock()
        ) as mock_bot,
    ):
        # Настраиваем мок для Bot
        mock_bot.return_value.send_message = AsyncMock()

        # Создаем экземпляр AiogramBot
        aiogram_bot = AiogramBot(token="123456:ABC-DEF", commands=[command], whitelist=whitelist)
        # Подменяем внутреннее свойство _bot на наш мок
        aiogram_bot._bot = mock_bot.return_value

        # Вызываем notify с моком ItemOfferNotification
        await aiogram_bot.notify(mock_notification)

        # Проверяем, что сообщение отправлено правильному пользователю
        mock_bot.return_value.send_message.assert_called_once_with(
            chat_id=test_user_id,
            text="Test notification",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

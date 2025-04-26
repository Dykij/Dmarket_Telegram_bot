from aiogram import types

from price_monitoring.telegram.bot.abstract_command import AbstractCommand
from price_monitoring.telegram.bot.abstract_settings import AbstractSettings

_COMMAND = "settings"


class Settings(AbstractCommand):
    def __init__(self, settings_provider: AbstractSettings):
        super().__init__(_COMMAND)
        self.settings_provider = settings_provider

    async def handler(self, message: types.Message) -> None:
        try:
            settings = await self.settings_provider.get()

            result = f"Current settings: {settings!s}"

            await message.reply(result)
        except Exception as exc:
            await message.reply(str(exc))

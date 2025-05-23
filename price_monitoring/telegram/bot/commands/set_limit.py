from aiogram import types

from price_monitoring.telegram.bot.abstract_command import AbstractCommand
from price_monitoring.telegram.bot.abstract_settings import AbstractSettings

_COMMAND = "set_limit"


class SetLimit(AbstractCommand):
    def __init__(self, settings_provider: AbstractSettings):
        super().__init__(_COMMAND)
        self.settings_provider = settings_provider

    async def handler(self, message: types.Message) -> None:
        try:
            args = message.get_args()
            try:
                percentage = float(args.split()[0])
            except Exception as exc:
                raise ValueError(f"could not convert string to float: '{args}'") from exc

            settings = await self.settings_provider.get()
            if not settings:
                raise ValueError("Failed to load settings!")
            settings.max_threshold = percentage
            await self.settings_provider.set(settings)

            result = f"Limit for {percentage}% successfully set!"

            await message.reply(result)
        except Exception as exc:
            await message.reply(str(exc))

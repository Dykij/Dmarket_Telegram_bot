import asyncio
import logging

from common.tracer import annotate, trace
from price_monitoring.decorators import async_infinite_loop
from price_monitoring.telegram.bot import AbstractBot
from price_monitoring.telegram.fresh_filter import AbstractFilter
from price_monitoring.telegram.offer_provider import AbstractOfferProvider

from .abstract_runner import AbstractRunner

logger = logging.getLogger(__name__)


class Runner(AbstractRunner):
    def __init__(
        self,
        bot: AbstractBot,
        price_provider: AbstractOfferProvider,
        filter_: AbstractFilter,
    ):
        self.bot = bot
        self.price_provider = price_provider
        self.filter_ = filter_

    @async_infinite_loop(logger)
    @trace
    async def run(self) -> None:
        offers = await self.price_provider.get_items()
        annotate(f"Got {len(offers)} offers from {len(offers)}")
        new_offers = await self.filter_.filter_new_offers(offers)
        annotate(f"Filtered out {len(offers) - len(new_offers)}")
        logger.info(f"Got {len(new_offers)} new offers from {len(offers)}")
        annotate(f"Got {len(new_offers)} new offers from {len(offers)}")
        await self.filter_.append_offers(offers)

        for offer in new_offers:
            notification = offer.create_notification()
            await self.bot.notify(notification)
            await asyncio.sleep(1 / 15)

        await asyncio.sleep(3)

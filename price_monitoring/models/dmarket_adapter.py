"""Aдantepbi для o6ecneчehuя o6pathoй coвmectumoctu moдeлeй дahhbix DMarket.

Эtot moдyл' npeдoctaвляet aдantepbi для moдeлeй DMarket,
o6ecneчuвaющue o6pathyю coвmectumoct' meждy ctapbim u hoвbim API.
"""

import functools
import inspect
import logging
from typing import Any, TypeVar

from price_monitoring.models.dmarket import DMarketItem

logger = logging.getLogger(__name__)

T = TypeVar("T")


def adapt_market_hash_name_to_title(cls: type[T]) -> type[T]:
    """Дekopatop для aдantaцuu napametpa market_hash_name k title.

    Эtot дekopatop moдuфuцupyet kohctpyktop kлacca для npeo6pa3oвahuя
    ctaporo napametpa market_hash_name в hoвbiй napametp title,
    o6ecneчuвaя o6pathyю coвmectumoct'.

    Args:
        cls: Kлacc для дekopupoвahuя

    Returns:
        Дekopupoвahhbiй kлacc c coвmectumbim kohctpyktopom
    """
    original_init = cls.__init__

    @functools.wraps(original_init)
    def adapted_init(self: Any, *args: Any, **kwargs: Any) -> None:
        # O6pa6atbiвaem cлyчaй umehoвahhoro aprymehta market_hash_name
        if "market_hash_name" in kwargs and "title" not in kwargs:
            kwargs["title"] = kwargs.pop("market_hash_name")
            logger.debug("Пapametp market_hash_name npeo6pa3oвah в title")

        # O6pa6atbiвaem cлyчaй no3uцuohhoro aprymehta market_hash_name
        # ha ochoвe curhatypbi
        sig = inspect.signature(original_init)
        param_names = list(sig.parameters.keys())[1:]  # Пponyckaem self

        if len(args) >= 2 and "title" in param_names:
            title_index = param_names.index("title")
            if title_index < len(args) and "title" not in kwargs:
                # 3amehяem aprymeht market_hash_name ha title
                args_list = list(args)
                args = tuple(args_list)

        original_init(self, *args, **kwargs)

    cls.__init__ = adapted_init  # type: ignore
    return cls


# Пpumehяem aдantep k kлaccy DMarketItem
DMarketItem = adapt_market_hash_name_to_title(DMarketItem)

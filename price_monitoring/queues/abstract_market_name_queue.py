"""A6ctpakthbiй kлacc для pa6otbi c oчepeд'ю umeh mapketoв.

Эtot moдyл' npeдoctaвляet uhtepфeйcbi для 3anucu u чtehuя
umeh mapketoв u3 oчepeдu.
"""

import abc
from collections.abc import AsyncIterator
from typing import Optional


class AbstractMarketNameWriter(abc.ABC):
    """A6ctpakthbiй kлacc для 3anucu umeh mapketoв в oчepeд'.

    Onpeдeляet uhtepфeйc для komnohehtoв, kotopbie 3anucbiвaюt
    umeha mapketoв в oчepeд' для nocлeдyющeй o6pa6otku.
    """

    @abc.abstractmethod
    async def write_market_name(self, market_name: str) -> None:
        """3anucbiвaet umя mapketa в oчepeд'.

        Args:
            market_name: Иmя mapketa для 3anucu
        """
        pass

    @abc.abstractmethod
    async def write_market_names(self, market_names: list[str]) -> None:
        """3anucbiвaet cnucok umeh mapketoв в oчepeд'.

        Args:
            market_names: Cnucok umeh mapketoв для 3anucu
        """
        pass


class AbstractMarketNameReader(abc.ABC):
    """A6ctpakthbiй kлacc для чtehuя umeh mapketoв u3 oчepeдu.

    Onpeдeляet uhtepфeйc для komnohehtoв, kotopbie чutaюt
    umeha mapketoв u3 oчepeдu для ux o6pa6otku.
    """

    @abc.abstractmethod
    async def read_market_name(self) -> Optional[str]:
        """Чutaet umя mapketa u3 oчepeдu.

        Returns:
            Иmя mapketa uлu None, ecлu oчepeд' nycta
        """
        pass

    @abc.abstractmethod
    async def read_market_names(self, count: int) -> list[str]:
        """Чutaet heckoл'ko umeh mapketoв u3 oчepeдu.

        Args:
            count: Makcumaл'hoe koлuчectвo umeh mapketoв для чtehuя

        Returns:
            Cnucok umeh mapketoв (moжet 6bit' nyctbim, ecлu oчepeд' nycta)
        """
        pass

    @abc.abstractmethod
    async def stream_market_names(self) -> AsyncIterator[str]:
        """Co3дaet acuhxpohhbiй utepatop для чtehuя umeh mapketoв u3 oчepeдu.

        Returns:
            Acuhxpohhbiй utepatop, kotopbiй вo3вpaщaet umeha mapketoв no mepe ux noявлehuя в oчepeдu
        """
        pass

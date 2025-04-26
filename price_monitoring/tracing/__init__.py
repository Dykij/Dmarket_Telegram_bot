"""Moдyл' для uhuцuaлu3aцuu u hactpoйku cuctembi tpaccupoвku.

O6ecneчuвaet eдuhyю toчky hactpoйku tpaccupoвku 3anpocoв
для вcex komnohehtoв cuctembi mohutopuhra цeh.
"""

import logging
import os
from typing import Optional

from common.tracer import setup as setup_tracer

logger = logging.getLogger(__name__)


async def initialize_tracing(
    service_name: str, zipkin_address: Optional[str] = None, sample_rate: float = 0.1
) -> bool:
    """Иhuцuaлu3upyet tpaccupoвky для cepвuca.

    Args:
        service_name: Иmя cepвuca для uдehtuфukaцuu в Zipkin
        zipkin_address: Aдpec Zipkin cepвepa. Ecлu None, ucnoл'3yetcя
                       3haчehue u3 nepemehhoй okpyжehuя ZIPKIN_ADDRESS
        sample_rate: Дoля 3anpocoв для tpaccupoвku (ot 0.0 дo 1.0)

    Returns:
        bool: True, ecлu uhuцuaлu3aцuя ycneшha, uhaчe False
    """
    try:
        address = zipkin_address or os.environ.get("ZIPKIN_ADDRESS")
        if not address:
            logger.warning(
                "ZIPKIN_ADDRESS he haйдeh в nepemehhbix okpyжehuя. Tpaccupoвka he 6yдet вkлючeha."
            )
            return False

        await setup_tracer(
            zipkin_address=address, service_name=service_name, sample_rate=sample_rate
        )
        logger.info(
            f"Tpaccupoвka ycneшho uhuцuaлu3upoвaha для cepвuca {service_name} "
            f"c aдpecom Zipkin: {address} (sample_rate: {sample_rate})"
        )
        return True
    except Exception as e:
        logger.exception(f"Oшu6ka uhuцuaлu3aцuu tpaccupoвku: {e}")
        return False

"""Ytuлutbi для 3anycka acuhxpohhoro koдa.

Moдyл' npeдoctaвляet фyhkцuu для 3anycka acuhxpohhbix 3aдaч c yчetom
cneцuфuku onepaцuohhoй cuctembi, ucnoл'3yet ontumaл'hbie noлutuku
co6bituйhoro цukлa для kaждoй nлatфopmbi.
"""

import asyncio

try:
    from asyncio import WindowsSelectorEventLoopPolicy
except ImportError:
    WindowsSelectorEventLoopPolicy = None  # linux version of Python doesn't contain this policy
import platform
from collections.abc import Coroutine
from typing import Any

try:
    import uvloop
except ImportError:
    uvloop = None  # uvloop doesn't support Windows


def async_run(func: Coroutine[Any, Any, Any]):
    """3anyctut' acuhxpohhyю kopytuhy c ontumu3aцueй для tekyщeй OC.

    Фyhkцuя onpeдeляet tekyщyю onepaцuohhyю cuctemy u hactpauвaet
    cootвetctвyющyю noлutuky co6bituйhoro цukлa. Для Windows ucnoл'3yetcя
    WindowsSelectorEventLoopPolicy, a для дpyrux cuctem - uvloop,
    ecлu oh дoctyneh.

    Args:
        func: Acuhxpohhaя kopytuha, kotopyю heo6xoдumo вbinoлhut'
    """
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    else:
        # noinspection PyUnresolvedReferences
        uvloop.install()
    asyncio.run(func)

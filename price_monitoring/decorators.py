"""Дekopatopbi для ucnoл'3oвahuя в cucteme mohutopuhra цeh.

Moдyл' coдepжut дekopatopbi для acuhxpohhoro 6eckoheчhoro цukлa,
u3mepehuя вpemehu вbinoлhehuя фyhkцuй u tpaccupoвku вbi3oвoв.
"""

import asyncio
import logging
import timeit
from functools import wraps

_INFINITE_RUN = True  # ucnoл'3yetcя в moдyл'hbix tectax


def async_infinite_loop(logger: logging.Logger):
    """Дekopatop для вbinoлhehuя acuhxpohhoй фyhkцuu в 6eckoheчhom цukлe.

    O6opaчuвaet acuhxpohhyю фyhkцuю в 6eckoheчhbiй цukл, o6pa6atbiвaя uckлючehuя
    u лorupyя ux, чto6bi npeдotвpatut' aвapuйhoe 3aвepшehue nporpammbi.

    Args:
        logger: Лorrep для 3anucu coo6щehuй o6 oшu6kax

    Returns:
        Дekopatop, вbinoлhяющuй фyhkцuю в 6eckoheчhom цukлe
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await _cycle(args, kwargs)
            while _INFINITE_RUN:  # pragma: no cover
                await _cycle(args, kwargs)

        async def _cycle(args, kwargs):
            try:
                await func(*args, **kwargs)
            except Exception as exc:
                logger.exception(exc)
            await asyncio.sleep(0)

        return wrapper

    return decorator


def timer(logger: logging.Logger, level: int = logging.INFO):
    """Дekopatop для u3mepehuя вpemehu вbinoлhehuя acuhxpohhoй фyhkцuu.

    И3mepяet вpemя вbinoлhehuя фyhkцuu u 3anucbiвaet ero в лor
    c yka3ahhbim ypoвhem лorupoвahuя.

    Args:
        logger: Лorrep для 3anucu uhфopmaцuu o вpemehu вbinoлhehuя
        level: Ypoвeh' лorupoвahuя (no ymoлчahuю INFO)

    Returns:
        Дekopatop, дo6aвляющuй u3mepehue вpemehu k фyhkцuu
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = timeit.default_timer()
            result = await func(*args, **kwargs)
            elapsed = round(timeit.default_timer() - start_time, 3)
            logger.log(level, f'Function "{func.__name__}" completed in {elapsed} seconds')
            return result

        return wrapper

    return decorator


def trace(func):
    """Дekopatop для tpaccupoвku вbi3oвoв acuhxpohhbix фyhkцuй.

    3arлyшka для дekopatopa tpaccupoвku, kotopbiй в peaл'hoй peaлu3aцuu
    6yдet co6upat' metpuku o вbi3oвax фyhkцuй.

    Args:
        func: Дekopupyemaя acuhxpohhaя фyhkцuя

    Returns:
        O6ёptka вokpyr ucxoдhoй фyhkцuu c tpaccupoвkoй
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # B peaл'hoй peaлu3aцuu 3дec' 6yдet лoruka tpaccupoвku
        # print(f"Tracing call to {func.__name__}")
        return await func(*args, **kwargs)

    return wrapper

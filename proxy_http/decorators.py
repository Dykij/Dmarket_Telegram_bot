"""Модуль с декораторами для работы с HTTP-прокси.

Содержит вспомогательные декораторы для управления поведением
HTTP-клиентов при использовании прокси-серверов.
"""

import asyncio
from functools import wraps

import aiohttp


def catch_aiohttp(logger):
    """Декоратор для обработки ошибок при работе с aiohttp.

    Перехватывает различные типы ошибок, которые могут возникнуть
    при работе с HTTP-клиентом через прокси, и логирует их.

    Примечание: Этот декоратор подготовлен для использования
    в будущих версиях системы при расширении функциональности
    работы с прокси-серверами.

    Args:
        logger: Логгер для записи информации об ошибках

    Returns:
        Декорированная функция, которая перехватывает исключения
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (
                aiohttp.ClientHttpProxyError,
                aiohttp.ClientProxyConnectionError,
            ) as exc:
                logger.exception("Failed to connect to proxy", exc_info=exc)
            except (
                asyncio.exceptions.TimeoutError,
                aiohttp.ClientConnectionError,
                aiohttp.ClientPayloadError,
                aiohttp.ClientResponseError,
                ConnectionResetError,
            ) as exc:
                logger.exception("Failed to connect to proxy", exc_info=exc)

        return wrapper

    return decorator

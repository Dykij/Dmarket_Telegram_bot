"""
Декораторы для использования в системе мониторинга цен.

Модуль содержит декораторы для асинхронного бесконечного цикла,
измерения времени выполнения функций и трассировки вызовов.
"""

import asyncio
import logging
import timeit
from functools import wraps

_INFINITE_RUN = True  # используется в модульных тестах


def async_infinite_loop(logger: logging.Logger):
    """
    Декоратор для выполнения асинхронной функции в бесконечном цикле.

    Оборачивает асинхронную функцию в бесконечный цикл, обрабатывая исключения
    и логируя их, чтобы предотвратить аварийное завершение программы.

    Args:
        logger: Логгер для записи сообщений об ошибках

    Returns:
        Декоратор, выполняющий функцию в бесконечном цикле
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
    """
    Декоратор для измерения времени выполнения асинхронной функции.

    Измеряет время выполнения функции и записывает его в лог
    с указанным уровнем логирования.

    Args:
        logger: Логгер для записи информации о времени выполнения
        level: Уровень логирования (по умолчанию INFO)

    Returns:
        Декоратор, добавляющий измерение времени к функции
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = timeit.default_timer()
            result = await func(*args, **kwargs)
            elapsed = round(timeit.default_timer() - start_time, 3)
            logger.log(level, f'Функция "{func.__name__}" выполнилась за {elapsed} секунд.')
            return result

        return wrapper

    return decorator


def trace(func):
    """
    Декоратор для трассировки вызовов асинхронных функций.

    Заглушка для декоратора трассировки, который в реальной реализации
    будет собирать метрики о вызовах функций.

    Args:
        func: Декорируемая асинхронная функция

    Returns:
        Обёртка вокруг исходной функции с трассировкой
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # В реальной реализации здесь будет логика трассировки
        # print(f"Tracing call to {func.__name__}")
        return await func(*args, **kwargs)

    return wrapper

"""
Утилиты для запуска асинхронного кода.

Модуль предоставляет функции для запуска асинхронных задач с учетом
специфики операционной системы, использует оптимальные политики
событийного цикла для каждой платформы.
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
    """
    Запустить асинхронную корутину с оптимизацией для текущей ОС.

    Функция определяет текущую операционную систему и настраивает
    соответствующую политику событийного цикла. Для Windows используется
    WindowsSelectorEventLoopPolicy, а для других систем - uvloop,
    если он доступен.

    Args:
        func: Асинхронная корутина, которую необходимо выполнить
    """
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    else:
        # noinspection PyUnresolvedReferences
        uvloop.install()
    asyncio.run(func)

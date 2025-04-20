"""
Общие функции и утилиты для системы мониторинга цен.

Модуль предоставляет общие функции для создания HTTP-заголовков
и управления сессиями с прокси-серверами.
"""

from collections.abc import Sequence
from time import time

from random_user_agent.params import OperatingSystem, SoftwareName
from random_user_agent.user_agent import UserAgent

from proxy_http.aiohttp_session_factory import AiohttpSessionFactory
from proxy_http.async_proxies_concurrent_limiter import \
    AsyncSessionConcurrentLimiter
from proxy_http.proxy import Proxy

# Ротатор User-Agent для имитации запросов от разных браузеров
user_agent_rotator = UserAgent(
    software_names=[SoftwareName.CHROME.value],
    operating_systems=[OperatingSystem.WINDOWS.value],
    limit=1000,
)


def _create_headers():
    """
    Создать набор HTTP-заголовков для запросов.

    Генерирует заголовки с случайным User-Agent для имитации запросов
    от разных браузеров, чтобы снизить вероятность блокировки.

    Returns:
        dict: Словарь с HTTP-заголовками для запросов.
    """
    return {
        "User-Agent": user_agent_rotator.get_random_user_agent(),
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        # 'X-Requested-With': 'XMLHttpRequest',
        "Connection": "keep-alive",
        # 'Referer': referer,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


def create_limiter(proxies: Sequence[Proxy]):
    """
    Создать ограничитель одновременных подключений через прокси.

    Создает объект для контроля и ограничения количества одновременных
    HTTP-сессий через прокси-серверы, предотвращая их перегрузку.

    Args:
        proxies: Последовательность объектов Proxy для создания сессий.

    Returns:
        AsyncSessionConcurrentLimiter: Объект управления сессиями.
    """
    return AsyncSessionConcurrentLimiter(
        [
            AiohttpSessionFactory.create_session_with_proxy(proxy, headers=_create_headers())
            for proxy in proxies
        ],
        time(),
    )

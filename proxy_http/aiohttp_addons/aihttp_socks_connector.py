"""Модуль для обеспечения поддержки SOCKS-прокси в aiohttp.

Предоставляет расширение для библиотеки aiohttp, позволяющее выполнять
HTTP-запросы через SOCKS-прокси, что обеспечивает дополнительный уровень
анонимности и безопасности при работе с внешними API.

Примечание: Этот модуль подготовлен для использования в будущих версиях
системы при расширении функциональности работы с прокси-серверами.
"""

from aiohttp import TCPConnector
from python_socks import parse_proxy_url
from python_socks.async_.asyncio.v2 import Proxy


class ProxyConnector(TCPConnector):
    """Коннектор для aiohttp с поддержкой различных типов прокси.

    Расширяет стандартный TCPConnector, добавляя возможность
    подключения через прокси-серверы, включая HTTP и SOCKS прокси.

    Attributes:
        proxy_url: URL прокси-сервера в формате 'protocol://user:password@host:port'
    """

    def __init__(self, proxy_url, **kwargs):
        """Инициализирует коннектор с настройками прокси-сервера.

        Args:
            proxy_url: URL прокси-сервера в формате 'protocol://user:password@host:port',
                      где protocol может быть http, socks4, socks5
            **kwargs: Дополнительные аргументы для базового TCPConnector
        """
        super().__init__(**kwargs)
        self._proxy_url = proxy_url

        # Настраиваем параметры прокси
        proxy_type, host, port, username, password = parse_proxy_url(proxy_url)
        self._proxy_params = (proxy_type, host, port, username, password)

    async def _create_proxy_connection(self, req, traces, timeout):
        """Создает соединение через прокси-сервер.

        Args:
            req: Объект запроса
            traces: Трассировки запроса
            timeout: Таймаут соединения

        Returns:
            Установленное соединение через прокси-сервер
        """
        proxy_type, host, port, username, password = self._proxy_params

        # Создаем объект прокси с нужными параметрами
        proxy = Proxy.create(proxy_type, host=host, port=port, username=username, password=password)

        # Получаем целевые хост и порт из запроса
        target_host = req.url.host
        target_port = req.url.port or (443 if req.url.scheme == "https" else 80)

        # Устанавливаем соединение через прокси
        connection = await proxy.connect(target_host, target_port)

        return connection

    async def _create_direct_connection(self, req, traces, timeout):
        """Создает прямое соединение, если прокси не указан.

        Переопределяет стандартный метод создания соединения
        при выполнении HTTP-запросов.
        """
        # Если есть прокси, используем его
        if hasattr(self, "_proxy_params"):
            return await self._create_proxy_connection(req, traces, timeout)

        # Иначе используем стандартный способ создания соединения
        return await super()._create_direct_connection(req, traces, timeout)

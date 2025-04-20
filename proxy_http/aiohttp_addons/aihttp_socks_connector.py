"""
Модуль для обеспечения поддержки SOCKS-прокси в aiohttp.

Предоставляет расширение для библиотеки aiohttp, позволяющее выполнять
HTTP-запросы через SOCKS-прокси, что обеспечивает дополнительный уровень
анонимности и безопасности при работе с внешними API.

Примечание: Этот модуль подготовлен для использования в будущих версиях
системы при расширении функциональности работы с прокси-серверами.
"""

from aiohttp import TCPConnector
from python_socks import ProxyType, parse_proxy_url
from python_socks.async_.asyncio.v2 import Proxy


class ProxyConnector(TCPConnector):
    """
    Коннектор для aiohttp с поддержкой различных типов прокси.

    Расширяет стандартный TCPConnector, добавляя возможность
    маршрутизации запросов через прокси-серверы различных типов,
    включая SOCKS4, SOCKS5 и HTTP.

    Attributes:
        _proxy_type: Тип прокси (SOCKS4, SOCKS5, HTTP)
        _proxy_host: Хост прокси-сервера
        _proxy_port: Порт прокси-сервера
        _proxy_username: Имя пользователя для авторизации на прокси
        _proxy_password: Пароль для авторизации на прокси
        _rdns: Флаг разрешения имен через прокси
    """

    def __init__(
        self,
        proxy_type=ProxyType.SOCKS5,
        host=None,
        port=None,
        username=None,
        password=None,
        rdns=None,
        **kwargs,
    ):
        """
        Инициализирует прокси-коннектор с указанными параметрами.

        Args:
            proxy_type: Тип прокси из enum ProxyType
            host: Хост прокси-сервера
            port: Порт прокси-сервера
            username: Имя пользователя для авторизации на прокси
            password: Пароль для авторизации на прокси
            rdns: Флаг разрешения имен через прокси
            **kwargs: Дополнительные параметры для TCPConnector
        """
        super().__init__(**kwargs)

        self._proxy_type = proxy_type
        self._proxy_host = host
        self._proxy_port = port
        self._proxy_username = username
        self._proxy_password = password
        self._rdns = rdns

    # noinspection PyMethodOverriding
    async def _wrap_create_connection(self, protocol_factory, host, port, *, ssl, **kwargs):
        """
        Создает соединение через прокси-сервер.

        Этот метод переопределяет стандартное поведение TCPConnector,
        перенаправляя соединение через указанный прокси-сервер.

        Примечание: Этот метод необходим для обеспечения поддержки прокси
        в aiohttp и будет вызываться внутренними механизмами библиотеки
        при выполнении HTTP-запросов.

        Args:
            protocol_factory: Фабрика протоколов
            host: Хост целевого сервера
            port: Порт целевого сервера
            ssl: Параметры SSL/TLS
            **kwargs: Дополнительные параметры соединения

        Returns:
            Кортеж (transport, protocol) для установленного соединения
        """
        proxy = Proxy.create(
            proxy_type=self._proxy_type,
            host=self._proxy_host,
            port=self._proxy_port,
            username=self._proxy_username,
            password=self._proxy_password,
            rdns=self._rdns,
            loop=self._loop,
        )

        connect_timeout = None

        timeout = kwargs.get("timeout")
        if timeout is not None:
            connect_timeout = getattr(timeout, "sock_connect", None)

        stream = await proxy.connect(
            dest_host=host, dest_port=port, dest_ssl=ssl, timeout=connect_timeout
        )

        transport = stream.writer.transport
        protocol = protocol_factory()

        transport.set_protocol(protocol)
        protocol.transport = transport

        return transport, protocol

    @classmethod
    def from_url(cls, url, **kwargs):
        """
        Создает прокси-коннектор из URL.

        Args:
            url: URL прокси в формате "протокол://[логин:пароль@]хост:порт"
            **kwargs: Дополнительные параметры для инициализации коннектора

        Returns:
            Настроенный экземпляр ProxyConnector
        """
        proxy_type, host, port, username, password = parse_proxy_url(url)
        return cls(
            proxy_type=proxy_type,
            host=host,
            port=port,
            username=username,
            password=password,
            **kwargs,
        )

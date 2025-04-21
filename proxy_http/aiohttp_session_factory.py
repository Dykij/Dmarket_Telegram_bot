from collections.abc import Mapping
from typing import Optional

from aiohttp import ClientSession

from proxy_http.aiohttp_addons.aihttp_socks_connector import ProxyConnector
from proxy_http.proxy import Proxy


class AiohttpSessionFactory:
    def __init__(self):
        """
        Инициализирует фабрику сессий aiohttp.
        """
        self._sessions = []

    def create_session(self) -> ClientSession:
        """
        Создает новую сессию aiohttp и добавляет ее в список сессий.

        Returns:
            ClientSession: Новая сессия aiohttp
        """
        session = ClientSession()
        self._sessions.append(session)
        return session

    def create_session_with_proxy(
        self, proxy: Proxy, headers: Optional[Mapping[str, str]] = None
    ) -> ClientSession:
        """
        Создает новую сессию aiohttp с прокси и добавляет ее в список сессий.

        Args:
            proxy: Объект прокси
            headers: Заголовки HTTP (опционально)

        Returns:
            ClientSession: Новая сессия aiohttp с прокси
        """
        connector = ProxyConnector.from_url(proxy.serialize(), ssl=False)
        session = ClientSession(connector=connector, headers=headers)
        self._sessions.append(session)
        return session

    async def close_all_sessions(self) -> None:
        """
        Закрывает все созданные сессии aiohttp.
        """
        for session in self._sessions:
            if not session.closed:
                await session.close()
        self._sessions.clear()

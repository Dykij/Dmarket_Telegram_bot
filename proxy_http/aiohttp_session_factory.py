from collections.abc import Mapping
from typing import Optional

from aiohttp import ClientSession

from proxy_http.aiohttp_addons.aihttp_socks_connector import ProxyConnector
from proxy_http.proxy import Proxy


class AiohttpSessionFactory:
    def __init__(self):
        """Initialize the aiohttp session factory."""
        self._sessions = []

    def create_session(self) -> ClientSession:
        """Create a new aiohttp session and add it to the sessions list.

        Returns:
            ClientSession: New aiohttp session
        """
        session = ClientSession()
        self._sessions.append(session)
        return session

    def create_session_with_proxy(
        self, proxy: Proxy, headers: Optional[Mapping[str, str]] = None
    ) -> ClientSession:
        """Create a new aiohttp session with a proxy and add it to the sessions list.

        Args:
            proxy: Proxy object
            headers: HTTP headers (optional)

        Returns:
            ClientSession: New aiohttp session with proxy
        """
        connector = ProxyConnector.from_url(proxy.serialize(), ssl=False)
        session = ClientSession(connector=connector, headers=headers)
        self._sessions.append(session)
        return session

    async def close_all_sessions(self) -> None:
        """Close all created aiohttp sessions."""
        for session in self._sessions:
            if not session.closed:
                await session.close()
        self._sessions.clear()

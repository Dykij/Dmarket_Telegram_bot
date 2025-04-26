"""Module for working with proxy servers.

Provides classes for storing information about proxy servers and
functionality for working with them in HTTP requests.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlsplit

from marshmallow_dataclass import add_schema

from common.core.dataclass_json import JsonMixin

logger = logging.getLogger(__name__)


@add_schema
@dataclass
class Proxy(JsonMixin):
    """Class representing a proxy server.

    Stores information about a proxy server, including host, port,
    authentication credentials, and protocol.

    Attributes:
        host: Proxy server host
        port: Proxy server port
        login: Login for proxy server authentication
        password: Password for proxy server authentication
        protocol: Proxy server protocol (http, socks5, etc.)
        proxy_str: Proxy parameters string for quick initialization
    """

    class Meta:
        """Meta-class for serialization configuration.

        Note: This class is necessary for integration with marshmallow
        and managing the order of fields when serializing a Proxy object.
        In future versions, it may be used to extend
        serialization functionality.

        Attributes:
            ordered: Flag indicating the need to preserve
                    the order of fields during serialization
        """

        ordered = True

    host: Optional[str] = None
    port: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    protocol: Optional[str] = None
    proxy_str: Optional[str] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        """Initialize proxy from string if provided."""
        if self.proxy_str:
            self.deserialize(self.proxy_str)

    def get_identifier(self) -> str:
        """Return a unique proxy identifier.

        Note: This method is used to identify proxy servers
        in the caching system and limiting simultaneous connections.
        In future versions, it may be extended to support more complex
        identification schemes.

        Returns:
            String uniquely identifying the proxy server
        """
        return f"{self.host}:{self.port}"

    def _build_proxy_url(self):
        """Create URL for connecting to the proxy."""
        url = ""
        if self.login and self.password:
            url += f"{self.login}:{self.password}@"
        url += f"{self.host}:{self.port}"
        return url

    def deserialize(self, s: str) -> bool:
        """Initialize object from a proxy URL string.

        Args:
            s: Proxy URL in format "[protocol://][login:password@]host:port"

        Returns:
            True on success, False on parsing error
        """
        try:
            if "//" not in s:
                s = "//" + s
            result = urlsplit(s)
            self.protocol = result.scheme
            if self.protocol == "https":
                self.protocol = "http"
            self.host = result.hostname
            self.port = str(result.port)
            self.login = result.username
            self.password = result.password
            return True
        except Exception as e:
            # Handle any error when parsing proxy
            logger.warning(f"Failed to parse proxy URL: {e}")
            self.protocol = None
            self.host = None
            self.port = None
            self.login = None
            self.password = None
            return False

    def serialize(self):
        """Convert object to proxy URL string.

        Returns:
            Proxy URL in format "protocol://[login:password@]host:port"
        """
        return f"{self.protocol}://{self._build_proxy_url()}"

    def __eq__(self, other):
        """Compare two proxy objects.

        Args:
            other: Another object to compare

        Returns:
            True if objects represent the same proxy server
        """
        if not isinstance(other, Proxy):
            return False
        return (
            self.host == other.host
            and self.port == other.port
            and self.login == other.login
            and self.password == other.password
        )

    def __repr__(self):
        """Represent object as a string for debugging.

        Returns:
            String with proxy host and port
        """
        return f"{self.host}:{self.port}"

    def __str__(self):
        """Convert object to string.

        Returns:
            Proxy URL in format "protocol://[login:password@]host:port"
        """
        return f"{self.protocol}://{self._build_proxy_url()}"

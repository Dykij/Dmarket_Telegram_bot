"""
Модуль для работы с прокси-серверами.

Предоставляет классы для хранения информации о прокси-серверах и
функциональность для работы с ними в HTTP-запросах.
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
    """
    Класс, представляющий прокси-сервер.

    Хранит информацию о прокси-сервере, включая хост, порт,
    учетные данные для авторизации и протокол.

    Attributes:
        host: Хост прокси-сервера
        port: Порт прокси-сервера
        login: Логин для авторизации на прокси-сервере
        password: Пароль для авторизации на прокси-сервере
        protocol: Протокол прокси-сервера (http, socks5 и т.д.)
        proxy_str: Строка с параметрами прокси для быстрой инициализации
    """

    class Meta:
        """
        Мета-класс для настройки сериализации.

        Примечание: Этот класс необходим для интеграции с marshmallow
        и управления порядком полей при сериализации объекта Proxy.
        В будущих версиях может использоваться для расширения
        функциональности сериализации.

        Attributes:
            ordered: Флаг, указывающий на необходимость сохранения
                    порядка полей при сериализации
        """

        ordered = True

    host: Optional[str] = None
    port: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    protocol: Optional[str] = None
    proxy_str: Optional[str] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        """Инициализирует прокси из строки, если она предоставлена."""
        if self.proxy_str:
            self.deserialize(self.proxy_str)

    def get_identifier(self) -> str:
        """
        Возвращает уникальный идентификатор прокси.

        Примечание: Этот метод используется для идентификации прокси-серверов
        в системе кэширования и ограничения одновременных подключений.
        В будущих версиях может быть расширен для поддержки более сложных
        схем идентификации.

        Returns:
            Строка, уникально идентифицирующая прокси-сервер
        """
        return f"{self.host}:{self.port}"

    def _build_proxy_url(self):
        """Создает URL для подключения к прокси."""
        url = ""
        if self.login and self.password:
            url += f"{self.login}:{self.password}@"
        url += f"{self.host}:{self.port}"
        return url

    def deserialize(self, s: str) -> bool:
        """
        Инициализирует объект из строки с URL прокси.

        Args:
            s: URL прокси в формате "[протокол://][логин:пароль@]хост:порт"

        Returns:
            True в случае успеха, False при ошибке парсинга
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
            # Обрабатываем любую ошибку при парсинге прокси
            logger.warning(f"Failed to parse proxy URL: {e}")
            self.protocol = None
            self.host = None
            self.port = None
            self.login = None
            self.password = None
            return False

    def serialize(self):
        """
        Преобразует объект в строку URL прокси.

        Returns:
            URL прокси в формате "протокол://[логин:пароль@]хост:порт"
        """
        return f"{self.protocol}://{self._build_proxy_url()}"

    def __eq__(self, other):
        """
        Сравнивает два объекта прокси.

        Args:
            other: Другой объект для сравнения

        Returns:
            True, если объекты представляют один и тот же прокси-сервер
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
        """
        Представляет объект в виде строки для отладки.

        Returns:
            Строка с хостом и портом прокси
        """
        return f"{self.host}:{self.port}"

    def __str__(self):
        """
        Преобразует объект в строку.

        Returns:
            URL прокси в формате "протокол://[логин:пароль@]хост:порт"
        """
        return f"{self.protocol}://{self._build_proxy_url()}"

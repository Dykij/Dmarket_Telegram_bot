from typing import Optional

from aio_pika import Channel, connect_robust


class RabbitMQClient:
    def __init__(
        self,
        host: str,
        port: int,
        login: str,
        password: str,
        connection_name: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.connection_name = connection_name
        self.connection = None

    async def connect(self):
        self.connection = await connect_robust(
            host=self.host,
            port=self.port,
            login=self.login,
            password=self.password,
        )
        return self

    async def create_channel(self) -> Channel:
        return await self.connection.channel()

from typing import Optional

import aioredis
from aioredis import Redis


class RedisConnector:
    def __init__(self, host: str, port: int, db: int, password: Optional[str] = None):
        """
        Инициализирует Redis-коннектор.

        Args:
            host: Хост Redis-сервера
            port: Порт Redis-сервера
            db: Номер базы данных
            password: Пароль для подключения к Redis (опционально)
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.client: Optional[Redis] = None

    async def get_client(self) -> Redis:
        """
        Возвращает клиент Redis, создавая его при необходимости.

        Returns:
            Клиент Redis для взаимодействия c базой данных
        """
        if self.client is None:
            self.client = await aioredis.create_redis_pool(
                f"redis://{self.host}:{self.port}", db=self.db, password=self.password
            )
        return self.client

    async def close(self) -> None:
        """
        Закрывает соединение c Redis.
        """
        if self.client:
            self.client.close()
            await self.client.wait_closed()
            self.client = None

    @staticmethod
    def create(host: str, port: str, db: str, password: Optional[str] = None) -> Redis:
        """
        Создает синхронный клиент Redis.

        Args:
            host: Хост Redis-сервера
            port: Порт Redis-сервера, в виде строки
            db: Номер базы данных, в виде строки
            password: Пароль для подключения к Redis (опционально)

        Returns:
            Клиент Redis
        """
        if password is None:
            return Redis(host=host, port=int(port), db=int(db))
        else:
            return Redis(host=host, port=int(port), db=int(db), password=password)

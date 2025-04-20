from abc import ABC, abstractmethod


class AbstractWhitelist(ABC):
    @abstractmethod
    async def add_member(self, chat_id: int) -> None:
        """
        Добавляет ID чата пользователя в белый список.

        Args:
            chat_id: ID чата пользователя Telegram
        """
        ...

    @abstractmethod
    async def remove_member(self, chat_id: int) -> None:
        """
        Удаляет ID чата пользователя из белого списка.

        Args:
            chat_id: ID чата пользователя Telegram
        """
        ...

    @abstractmethod
    async def get_members(self) -> list[int]:
        """
        Возвращает список ID чатов пользователей из белого списка.

        Returns:
            Список ID чатов пользователей Telegram
        """
        ...

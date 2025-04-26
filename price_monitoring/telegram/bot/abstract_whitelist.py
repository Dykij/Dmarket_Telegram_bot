from abc import ABC, abstractmethod


class AbstractWhitelist(ABC):
    @abstractmethod
    async def add_member(self, chat_id: int) -> None:
        """Дo6aвляet ID чata noл'3oвateля в 6eлbiй cnucok.

        Args:
            chat_id: ID чata noл'3oвateля Telegram
        """
        ...

    @abstractmethod
    async def remove_member(self, chat_id: int) -> None:
        """Yдaляet ID чata noл'3oвateля u3 6eлoro cnucka.

        Args:
            chat_id: ID чata noл'3oвateля Telegram
        """
        ...

    @abstractmethod
    async def get_members(self) -> list[int]:
        """Bo3вpaщaet cnucok ID чatoв noл'3oвateлeй u3 6eлoro cnucka.

        Returns:
            Cnucok ID чatoв noл'3oвateлeй Telegram
        """
        ...

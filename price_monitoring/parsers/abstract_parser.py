"""Abstract base class for parsers."""

from abc import ABC, abstractmethod


class AbstractParser(ABC):
    """Abstract base class defining the interface for parsers."""

    @abstractmethod
    async def run(self):
        """Run the parser logic."""

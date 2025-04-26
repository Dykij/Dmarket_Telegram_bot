"""Module for managing limitation of simultaneous connections to proxies.

Provides mechanisms for limiting the number of simultaneous
HTTP requests through proxy servers, which helps avoid blocks
and improves system stability.
"""

import asyncio
from asyncio import Lock
from time import time

from aiohttp import ClientSession


class NoAvailableSessionError(Exception):
    """Exception raised when no available sessions exist."""


class AsyncSessionConcurrentLimiter:
    """Limiter for the number of simultaneous HTTP sessions.

    Manages access to a set of sessions, preventing their overload
    and ensuring even distribution of requests.

    Note: This class is prepared for use in future versions
    of the system when expanding functionality for working with proxy servers.

    Attributes:
        _sessions: Dictionary of sessions and times when they will be available
        _lock: Lock for synchronizing access to sessions
    """

    def __init__(self, sessions: list[ClientSession], timestamp: float):
        """Initialize the limiter with specified sessions.

        Args:
            sessions: List of sessions to manage
            timestamp: Initial availability time for all sessions
        """
        self._sessions = dict.fromkeys(sessions, timestamp)
        self._lock = Lock()

    async def get_available(self, postpone_duration: float) -> ClientSession:
        """Get an available session and postpone its use.

        Blocks the caller until an available session appears.
        After obtaining a session, it will be unavailable
        for other requests for the specified time.

        Note: This method is used for fair distribution
        of load between proxy servers and preventing their blocking.

        Args:
            postpone_duration: Session blocking time in seconds

        Returns:
            Available ClientSession

        Raises:
            NoAvailableSessionError: If no available sessions
        """
        while True:
            try:
                async with self._lock:
                    return self._get_available_no_wait(time(), postpone_duration)
            except NoAvailableSessionError:
                await asyncio.sleep(0.1)

    def _get_available_no_wait(self, timestamp: float, postpone_duration: float) -> ClientSession:
        """Get an available session without waiting.

        Args:
            timestamp: Current time
            postpone_duration: Duration in seconds for which
                               the session will be unavailable

        Returns:
            Available ClientSession

        Raises:
            NoAvailableSessionError: If no available sessions
        """
        for session in self._sessions:
            if timestamp > self._sessions[session]:
                self._postpone(session, timestamp + postpone_duration)
                return session
        raise NoAvailableSessionError

    def _postpone(self, session: ClientSession, timestamp: float):
        """Postpone the use of a session until the specified time.

        Args:
            session: Session to postpone
            timestamp: Time until which the session will be unavailable

        Raises:
            NoAvailableSessionError: If session not found
        """
        try:
            self._sessions[session] = timestamp
        except KeyError:
            raise NoAvailableSessionError

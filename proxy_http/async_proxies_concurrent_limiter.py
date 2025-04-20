"""
Модуль для управления ограничением одновременных подключений к прокси.

Предоставляет механизмы для ограничения количества одновременных
HTTP-запросов через прокси-серверы, что позволяет избежать блокировок
и повысить стабильность работы системы.
"""

import asyncio
from asyncio import Lock
from time import time
from typing import List

from aiohttp import ClientSession


class NoAvailableSessionError(Exception):
    """Исключение, возникающее при отсутствии доступных сессий."""



class AsyncSessionConcurrentLimiter:
    """
    Ограничитель количества одновременных HTTP-сессий.

    Управляет доступом к набору сессий, предотвращая их перегрузку
    и обеспечивая равномерное распределение запросов.

    Примечание: Этот класс подготовлен для использования в будущих версиях
    системы при расширении функциональности работы с прокси-серверами.

    Attributes:
        _sessions: Словарь сессий и времени, когда они будут доступны
        _lock: Блокировка для синхронизации доступа к сессиям
    """

    def __init__(self, sessions: List[ClientSession], timestamp: float):
        """
        Инициализирует ограничитель с указанными сессиями.

        Args:
            sessions: Список сессий для управления
            timestamp: Начальное время доступности всех сессий
        """
        self._sessions = dict.fromkeys(sessions, timestamp)
        self._lock = Lock()

    async def get_available(self, postpone_duration: float) -> ClientSession:
        """
        Получает доступную сессию и откладывает ее использование.

        Блокирует вызывающую сторону до тех пор, пока не появится
        доступная сессия. После получения сессии, она будет недоступна
        для других запросов в течение указанного времени.

        Примечание: Этот метод используется для справедливого распределения
        нагрузки между прокси-серверами и предотвращения их блокировки.

        Args:
            postpone_duration: Время блокировки сессии в секундах

        Returns:
            Доступная сессия ClientSession

        Raises:
            NoAvailableSessionError: Если нет доступных сессий
        """
        while True:
            try:
                async with self._lock:
                    return self._get_available_no_wait(time(), postpone_duration)
            except NoAvailableSessionError:
                await asyncio.sleep(0.1)

    def _get_available_no_wait(self, timestamp: float, postpone_duration: float) -> ClientSession:
        """
        Получает доступную сессию без ожидания.

        Args:
            timestamp: Текущее время
            postpone_duration: Длительность в секундах, на которую
                               сессия будет недоступна

        Returns:
            Доступная сессия ClientSession

        Raises:
            NoAvailableSessionError: Если нет доступных сессий
        """
        for session in self._sessions:
            if timestamp > self._sessions[session]:
                self._postpone(session, timestamp + postpone_duration)
                return session
        raise NoAvailableSessionError

    def _postpone(self, session: ClientSession, timestamp: float):
        """
        Откладывает использование сессии до указанного времени.

        Args:
            session: Сессия для откладывания
            timestamp: Время, до которого сессия будет недоступна

        Raises:
            NoAvailableSessionError: Если сессия не найдена
        """
        try:
            self._sessions[session] = timestamp
        except KeyError:
            raise NoAvailableSessionError

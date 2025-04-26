import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

# Тип для функций, которые можно декорировать
F = TypeVar("F", bound=Callable[..., Any])


class RateLimiter:
    """Расширенный класс для ограничения частоты запросов к API.

    Позволяет устанавливать ограничения по количеству запросов в заданное время,
    автоматически добавляет задержки между запросами и поддерживает адаптивные
    стратегии отсрочки при ошибках превышения лимитов.

    Attributes:
        calls_limit: Максимальное число вызовов
        period: Период в секундах, за который разрешено calls_limit вызовов
        min_interval: Минимальный интервал между вызовами в секундах
        max_backoff: Максимальное время отсрочки в секундах при ошибках превышения лимитов
        jitter: Добавлять случайное отклонение к времени отсрочки для предотвращения "thundering herd"
    """

    def __init__(
        self,
        calls_limit: int = 100,
        period: float = 60.0,
        min_interval: float = 0.1,
        max_backoff: float = 60.0,
        jitter: bool = True,
    ):
        """Инициализирует лимиты для ограничения запросов.

        Args:
            calls_limit: Максимальное число вызовов в период
            period: Период в секундах
            min_interval: Минимальный интервал между вызовами в секундах
            max_backoff: Максимальное время отсрочки в секундах при ошибках превышения лимитов
            jitter: Добавлять случайное отклонение к времени отсрочки
        """
        self.calls_limit = calls_limit
        self.period = period
        self.min_interval = min_interval
        self.max_backoff = max_backoff
        self.jitter = jitter
        self.call_times: list[float] = []
        self.last_call_time: float = 0.0
        self.consecutive_failures: int = 0

    async def wait_if_needed(self) -> None:
        """Блокирует выполнение, если достигнуты лимиты запросов.

        Метод отслеживает историю вызовов и добавляет задержку, если:
        1. Не прошло min_interval с момента последнего вызова
        2. Достигнут лимит calls_limit в течение периода period
        3. Были последовательные ошибки превышения лимитов (через handle_rate_limit_error)
        """
        current_time = time.time()

        # Если были последовательные ошибки, применяем экспоненциальную отсрочку
        if self.consecutive_failures > 0:
            backoff_time = self._calculate_backoff_time()
            logger.warning(
                f"Applying exponential backoff after {self.consecutive_failures} consecutive failures. "
                f"Waiting for {backoff_time:.2f}s."
            )
            await asyncio.sleep(backoff_time)
            current_time = time.time()

        # Проверяем минимальный интервал между запросами
        if current_time - self.last_call_time < self.min_interval:
            wait_time = self.min_interval - (current_time - self.last_call_time)
            logger.debug(f"Rate limiting: waiting for {wait_time:.2f}s (min interval)")
            await asyncio.sleep(wait_time)
            current_time = time.time()

        # Очищаем устаревшие записи о вызовах
        self.call_times = [t for t in self.call_times if current_time - t <= self.period]

        # Проверяем количество вызовов в период
        if len(self.call_times) >= self.calls_limit:
            # Нужно дождаться, пока самый старый вызов выйдет за пределы периода
            oldest_call = self.call_times[0]
            wait_time = oldest_call + self.period - current_time

            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached: {self.calls_limit} calls in {self.period}s. "
                    f"Waiting for {wait_time:.2f}s."
                )
                await asyncio.sleep(wait_time)
                # Обновляем время и очищаем устаревшие записи
                current_time = time.time()
                self.call_times = [t for t in self.call_times if current_time - t <= self.period]

    def register_call(self) -> None:
        """Регистрирует новый вызов API и обновляет внутреннее состояние."""
        current_time = time.time()
        self.call_times.append(current_time)
        self.last_call_time = current_time

    def handle_rate_limit_error(self) -> None:
        """Обрабатывает ошибку превышения лимита скорости и увеличивает счетчик ошибок."""
        self.consecutive_failures += 1
        logger.warning(
            f"Rate limit error detected (consecutive failures: {self.consecutive_failures})"
        )

    def handle_success(self) -> None:
        """Сбрасывает счетчик последовательных ошибок при успешном запросе."""
        self.consecutive_failures = 0

    def _calculate_backoff_time(self) -> float:
        """Вычисляет время экспоненциальной отсрочки.

        Returns:
            float: Время отсрочки в секундах
        """
        # Экспоненциальная отсрочка с базой 2
        base_backoff = min(self.max_backoff, 2 ** (self.consecutive_failures - 1))

        # Добавляем случайный разброс, если включен jitter
        if self.jitter:
            jitter_factor = random.uniform(0.5, 1.5)
            backoff = base_backoff * jitter_factor
        else:
            backoff = base_backoff

        # Ограничиваем максимальным значением
        return min(self.max_backoff, backoff)


def rate_limit(
    calls_limit: int = 100,
    period: float = 60.0,
    min_interval: float = 0.1,
    max_backoff: float = 60.0,
    jitter: bool = True,
) -> Callable[[F], F]:
    """Декоратор для ограничения частоты вызовов асинхронных функций.

    Args:
        calls_limit: Максимальное число вызовов в период
        period: Период в секундах
        min_interval: Минимальный интервал между вызовами в секундах
        max_backoff: Максимальное время отсрочки в секундах при ошибках превышения лимитов
        jitter: Добавлять случайное отклонение к времени отсрочки

    Returns:
        Декоратор для функции
    """
    limiter = RateLimiter(
        calls_limit=calls_limit,
        period=period,
        min_interval=min_interval,
        max_backoff=max_backoff,
        jitter=jitter,
    )

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Ждем, если достигнуты лимиты
            await limiter.wait_if_needed()

            try:
                # Регистрируем вызов
                limiter.register_call()

                # Вызываем оригинальную функцию
                result = await func(*args, **kwargs)

                # Отмечаем успешное выполнение
                limiter.handle_success()

                return result
            except Exception as e:
                # Если это ошибка превышения лимита, обрабатываем ее
                if _is_rate_limit_error(e):
                    limiter.handle_rate_limit_error()
                # В любом случае пробрасываем исключение дальше
                raise

        return wrapper  # type: ignore

    return decorator


def _is_rate_limit_error(exc: Exception) -> bool:
    """Проверяет, является ли исключение ошибкой превышения лимита.

    Args:
        exc: Объект исключения для проверки

    Returns:
        bool: True, если это ошибка превышения лимита
    """
    # TODO: Проверить, если это API возвращает специфические коды ошибок или сообщения
    # для случаев превышения лимита запросов
    error_str = str(exc).lower()
    rate_limit_keywords = [
        "rate limit",
        "ratelimit",
        "too many requests",
        "429",
        "throttle",
        "quota exceeded",
    ]
    return any(keyword in error_str for keyword in rate_limit_keywords)

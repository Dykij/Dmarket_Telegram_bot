import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

# Тип для функций, которые можно декорировать
F = TypeVar('F', bound=Callable[..., Any])

class RateLimiter:
    """
    Расширенный класс для ограничения частоты запросов к API.

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
        jitter: bool = True
    ):
        """
        Инициализирует лимиты для ограничения запросов.

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
        self.call_times: List[float] = []
        self.last_call_time: float = 0.0
        self.consecutive_failures: int = 0

    async def wait_if_needed(self) -> None:
        """
        Блокирует выполнение, если достигнуты лимиты запросов.

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

        # Записываем текущий вызов
        self.call_times.append(current_time)
        self.last_call_time = current_time

    def _calculate_backoff_time(self) -> float:
        """
        Рассчитывает время экспоненциальной отсрочки на основе количества последовательных ошибок.

        Использует формулу: min(max_backoff, 2^(consecutive_failures - 1) * min_interval)
        Если включен jitter, добавляет случайное отклонение до 25% от рассчитанного времени.

        Returns:
            Время отсрочки в секундах
        """
        # Базовое время отсрочки с экспоненциальным ростом
        backoff = min(
            self.max_backoff,
            (2 ** (self.consecutive_failures - 1)) * self.min_interval
        )

        # Добавляем случайное отклонение (jitter) для предотвращения "thundering herd"
        if self.jitter:
            jitter_factor = 1.0 + random.uniform(-0.25, 0.25)
            backoff *= jitter_factor

        return backoff

    async def handle_rate_limit_error(self, status_code: Optional[int] = None, retry_after: Optional[Union[int, float]] = None) -> None:
        """
        Обрабатывает ошибку превышения лимита запросов от API.

        Увеличивает счетчик последовательных ошибок и добавляет задержку на основе
        информации от API (если предоставлена) или рассчитывает экспоненциальную отсрочку.

        Args:
            status_code: HTTP-код ответа (обычно 429 для ошибок превышения лимита)
            retry_after: Рекомендуемое API время ожидания в секундах (если предоставлено)
        """
        self.consecutive_failures += 1

        # Если API предоставило время для повторной попытки, используем его
        if retry_after is not None:
            wait_time = float(retry_after)
            logger.warning(
                f"Rate limit exceeded (status: {status_code}). "
                f"API requested wait time: {wait_time:.2f}s."
            )
            await asyncio.sleep(wait_time)
        else:
            # Иначе рассчитываем время отсрочки на основе количества ошибок
            backoff_time = self._calculate_backoff_time()
            logger.warning(
                f"Rate limit exceeded (status: {status_code}). "
                f"Using exponential backoff: {backoff_time:.2f}s."
            )
            await asyncio.sleep(backoff_time)

    def mark_success(self) -> None:
        """
        Отмечает успешный запрос, сбрасывая счетчик последовательных ошибок.

        Вызывайте этот метод после успешного выполнения запроса к API,
        чтобы сбросить стратегию экспоненциальной отсрочки.
        """
        if self.consecutive_failures > 0:
            logger.debug(f"Resetting consecutive failures counter from {self.consecutive_failures} to 0")
            self.consecutive_failures = 0


# Кэш для хранения экземпляров RateLimiter для разных endpoint'ов
_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(
    endpoint: str,
    calls_limit: int = 100, 
    period: float = 60.0, 
    min_interval: float = 0.1,
    max_backoff: float = 60.0,
    jitter: bool = True
) -> RateLimiter:
    """
    Возвращает или создает RateLimiter для заданного endpoint'а.

    Args:
        endpoint: Имя endpoint'а или API для идентификации лимитера
        calls_limit: Максимальное число вызовов в период
        period: Период в секундах
        min_interval: Минимальный интервал между вызовами в секундах
        max_backoff: Максимальное время отсрочки в секундах при ошибках превышения лимитов
        jitter: Добавлять случайное отклонение к времени отсрочки

    Returns:
        Экземпляр RateLimiter для заданного endpoint'а
    """
    if endpoint not in _limiters:
        _limiters[endpoint] = RateLimiter(calls_limit, period, min_interval, max_backoff, jitter)
    return _limiters[endpoint]


def rate_limited(
    endpoint: str, 
    calls_limit: Optional[int] = None, 
    period: Optional[float] = None, 
    min_interval: Optional[float] = None,
    max_backoff: Optional[float] = None,
    jitter: Optional[bool] = None
) -> Callable[[F], F]:
    """
    Декоратор для ограничения частоты вызовов асинхронных функций.

    Args:
        endpoint: Имя endpoint'а или API для идентификации лимитера
        calls_limit: Максимальное число вызовов в период (если None, используется значение по умолчанию)
        period: Период в секундах (если None, используется значение по умолчанию)
        min_interval: Минимальный интервал между вызовами в секундах (если None, используется значение по умолчанию)
        max_backoff: Максимальное время отсрочки в секундах (если None, используется значение по умолчанию)
        jitter: Добавлять случайное отклонение к времени отсрочки (если None, используется значение по умолчанию)

    Returns:
        Декорированная функция с ограниченной частотой вызовов
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Получаем или создаем лимитер с заданными параметрами
            limiter_args = {}
            if calls_limit is not None:
                limiter_args['calls_limit'] = calls_limit
            if period is not None:
                limiter_args['period'] = period
            if min_interval is not None:
                limiter_args['min_interval'] = min_interval
            if max_backoff is not None:
                limiter_args['max_backoff'] = max_backoff
            if jitter is not None:
                limiter_args['jitter'] = jitter

            limiter = get_rate_limiter(endpoint, **limiter_args)

            # Ждем, если нужно
            await limiter.wait_if_needed()

            try:
                # Вызываем оригинальную функцию
                result = await func(*args, **kwargs)
                # Отмечаем успешное выполнение
                limiter.mark_success()
                return result
            except Exception as e:
                # Проверяем, является ли исключение ошибкой превышения лимита
                # Это упрощенная проверка, в реальном коде нужно проверять конкретные типы исключений
                if hasattr(e, 'status') and getattr(e, 'status', 0) == 429:
                    retry_after = getattr(e, 'retry_after', None)
                    await limiter.handle_rate_limit_error(status_code=429, retry_after=retry_after)
                # Повторно вызываем исключение для обработки на более высоком уровне
                raise

        return wrapper  # type: ignore

    return decorator


# Примеры использования:

# Базовое использование с декоратором:
# @rate_limited("dmarket_api", calls_limit=100, period=60, min_interval=0.5)
# async def fetch_dmarket_data(some_params):
#     # код запроса к API
#     pass

# Использование с обработкой ошибок превышения лимита:
# async def fetch_with_rate_limit_handling(url, params):
#     limiter = get_rate_limiter("dmarket_api", calls_limit=100, period=60)
#     
#     while True:
#         try:
#             await limiter.wait_if_needed()
#             response = await make_request(url, params)
#             limiter.mark_success()
#             return response
#         except RateLimitExceeded as e:
#             await limiter.handle_rate_limit_error(status_code=e.status, retry_after=e.retry_after)
#         except Exception as e:
#             # Обработка других ошибок
#             raise

# Специфические лимиты для DMarket API:
# Публичные эндпоинты: 100 запросов в минуту
DMARKET_PUBLIC_RATE_LIMITER = get_rate_limiter(
    "dmarket_public_api", 
    calls_limit=100, 
    period=60.0, 
    min_interval=0.1,
    max_backoff=120.0
)

# Приватные эндпоинты: 60 запросов в минуту
DMARKET_PRIVATE_RATE_LIMITER = get_rate_limiter(
    "dmarket_private_api", 
    calls_limit=60, 
    period=60.0, 
    min_interval=0.2,
    max_backoff=120.0
)

# Эндпоинты для торговли: 30 запросов в минуту
DMARKET_TRADING_RATE_LIMITER = get_rate_limiter(
    "dmarket_trading_api", 
    calls_limit=30, 
    period=60.0, 
    min_interval=0.5,
    max_backoff=300.0
)

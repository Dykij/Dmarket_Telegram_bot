import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

# Тип для функций, которые можно декорировать
F = TypeVar('F', bound=Callable[..., Any])

class RateLimiter:
    """
    Простой класс для ограничения частоты запросов к API.
    
    Позволяет устанавливать ограничения по количеству запросов в заданное время
    и автоматически добавляет задержки между запросами.
    
    Attributes:
        calls_limit: Максимальное число вызовов
        period: Период в секундах, за который разрешено calls_limit вызовов
        min_interval: Минимальный интервал между вызовами в секундах
    """
    
    def __init__(
        self, 
        calls_limit: int = 100, 
        period: float = 60.0, 
        min_interval: float = 0.1
    ):
        """
        Инициализирует лимиты для ограничения запросов.
        
        Args:
            calls_limit: Максимальное число вызовов в период
            period: Период в секундах
            min_interval: Минимальный интервал между вызовами в секундах
        """
        self.calls_limit = calls_limit
        self.period = period
        self.min_interval = min_interval
        self.call_times: List[float] = []
        self.last_call_time: float = 0.0
    
    async def wait_if_needed(self) -> None:
        """
        Блокирует выполнение, если достигнуты лимиты запросов.
        
        Метод отслеживает историю вызовов и добавляет задержку, если:
        1. Не прошло min_interval с момента последнего вызова
        2. Достигнут лимит calls_limit в течение периода period
        """
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


# Кэш для хранения экземпляров RateLimiter для разных endpoint'ов
_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(
    endpoint: str,
    calls_limit: int = 100, 
    period: float = 60.0, 
    min_interval: float = 0.1
) -> RateLimiter:
    """
    Возвращает или создает RateLimiter для заданного endpoint'а.
    
    Args:
        endpoint: Имя endpoint'а или API для идентификации лимитера
        calls_limit: Максимальное число вызовов в период
        period: Период в секундах
        min_interval: Минимальный интервал между вызовами в секундах
    
    Returns:
        Экземпляр RateLimiter для заданного endpoint'а
    """
    if endpoint not in _limiters:
        _limiters[endpoint] = RateLimiter(calls_limit, period, min_interval)
    return _limiters[endpoint]


def rate_limited(
    endpoint: str, 
    calls_limit: Optional[int] = None, 
    period: Optional[float] = None, 
    min_interval: Optional[float] = None
) -> Callable[[F], F]:
    """
    Декоратор для ограничения частоты вызовов асинхронных функций.
    
    Args:
        endpoint: Имя endpoint'а или API для идентификации лимитера
        calls_limit: Максимальное число вызовов в период (если None, используется значение по умолчанию)
        period: Период в секундах (если None, используется значение по умолчанию)
        min_interval: Минимальный интервал между вызовами в секундах (если None, используется значение по умолчанию)
    
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
            
            limiter = get_rate_limiter(endpoint, **limiter_args)
            
            # Ждем, если нужно
            await limiter.wait_if_needed()
            
            # Вызываем оригинальную функцию
            return await func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator


# Пример использования:
# @rate_limited("dmarket_api", calls_limit=100, period=60, min_interval=0.5)
# async def fetch_dmarket_data(some_params):
#     # код запроса к API
#     pass 
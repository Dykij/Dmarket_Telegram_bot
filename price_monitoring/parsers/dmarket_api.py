import logging
import json
from typing import Any, Dict, List, Optional, Union

import aiohttp
from aiohttp import ClientSession

from utils.rate_limiter import rate_limited

logger = logging.getLogger(__name__)

# Базовый URL для API Dmarket
DMARKET_API_URL = "https://api.dmarket.com"


class DMarketAPIClient:
    """
    Клиент для работы с API DMarket.
    
    Обеспечивает асинхронное взаимодействие с API DMarket с поддержкой
    ограничения частоты запросов.
    
    Attributes:
        session: Сессия aiohttp для выполнения HTTP-запросов
    """
    
    def __init__(self):
        """Инициализирует клиент API."""
        self.session: Optional[ClientSession] = None
    
    async def _ensure_session(self) -> ClientSession:
        """
        Создает или возвращает существующую сессию aiohttp.
        
        Returns:
            Экземпляр ClientSession
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self) -> None:
        """Закрывает сессию aiohttp."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    @rate_limited("dmarket_api", calls_limit=100, period=60.0, min_interval=0.1)
    async def get_sell_offers(
        self,
        game: str,
        limit: int = 100,
        cursor: Optional[str] = None,
        title: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Получает предложения о продаже.
        
        Args:
            game: Идентификатор игры (cs2, dota2, tf2, rust)
            limit: Максимальное количество результатов
            cursor: Курсор для пагинации
            title: Фильтр по названию предмета
            min_price: Минимальная цена в долларах
            max_price: Максимальная цена в долларах
            
        Returns:
            Словарь с данными ответа от API
        """
        session = await self._ensure_session()
        
        # Преобразуем идентификаторы игр в формат API
        game_map = {
            "cs2": "a8db",   # CS2
            "dota2": "9a92", # Dota 2
            "tf2": "f0b4",   # Team Fortress 2
            "rust": "252e"   # Rust
        }
        
        game_id = game_map.get(game.lower(), game)
        
        # Формируем параметры запроса
        params: Dict[str, Union[str, int]] = {
            "gameId": game_id,
            "limit": limit
        }
        
        if cursor:
            params["cursor"] = cursor
        
        if title:
            params["title"] = title
        
        if min_price is not None:
            # Цены в API представлены в центах
            params["priceFrom"] = int(min_price * 100)
            
        if max_price is not None:
            params["priceTo"] = int(max_price * 100)
        
        # Выполняем запрос
        url = f"{DMARKET_API_URL}/exchange/v1/market/items"
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                error_text = await response.text()
                logger.error(
                    f"DMarket API error: {response.status} - {error_text}"
                )
                # Возвращаем ошибку
                return {
                    "error": True,
                    "status": response.status,
                    "message": error_text
                }

    @rate_limited("dmarket_api", calls_limit=100, period=60.0, min_interval=0.1)
    async def get_buy_offers(
        self,
        game: str,
        limit: int = 100,
        cursor: Optional[str] = None,
        title: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Получает предложения о покупке.
        
        Args:
            game: Идентификатор игры (cs2, dota2, tf2, rust)
            limit: Максимальное количество результатов
            cursor: Курсор для пагинации
            title: Фильтр по названию предмета
            min_price: Минимальная цена в долларах
            max_price: Максимальная цена в долларах
            
        Returns:
            Словарь с данными ответа от API
        """
        # Аналогично get_sell_offers, но с другим эндпоинтом
        # и, возможно, параметрами
        session = await self._ensure_session()
        
        # Преобразуем идентификаторы игр в формат API
        game_map = {
            "cs2": "a8db",   # CS2
            "dota2": "9a92", # Dota 2
            "tf2": "f0b4",   # Team Fortress 2
            "rust": "252e"   # Rust
        }
        
        game_id = game_map.get(game.lower(), game)
        
        # Формируем параметры запроса
        params: Dict[str, Union[str, int]] = {
            "gameId": game_id,
            "limit": limit
        }
        
        if cursor:
            params["cursor"] = cursor
        
        if title:
            params["title"] = title
        
        if min_price is not None:
            # Цены в API представлены в центах
            params["priceFrom"] = int(min_price * 100)
            
        if max_price is not None:
            params["priceTo"] = int(max_price * 100)
        
        # Выполняем запрос
        # Примечание: это пример, в реальности нужно заменить URL на правильный
        # эндпоинт для buy offer'ов согласно документации Dmarket
        url = f"{DMARKET_API_URL}/exchange/v1/user/offers"
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                error_text = await response.text()
                logger.error(
                    f"DMarket API error: {response.status} - {error_text}"
                )
                # Возвращаем ошибку
                return {
                    "error": True,
                    "status": response.status,
                    "message": error_text
                }
    
    @rate_limited("dmarket_api", calls_limit=50, period=60.0, min_interval=0.2)
    async def find_arbitrage_opportunities(
        self,
        game: str,
        min_profit: float = 1.0,
        max_profit: float = 100.0,
        limit: int = 10,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ищет арбитражные возможности между предложениями покупки и продажи.
        
        Args:
            game: Идентификатор игры (cs2, dota2, tf2, rust)
            min_profit: Минимальная прибыль в долларах
            max_profit: Максимальная прибыль в долларах
            limit: Максимальное количество результатов
            cursor: Курсор для пагинации результатов
            
        Returns:
            Словарь с данными: {
                "items": список предметов с информацией о прибыли,
                "cursor": курсор для следующей страницы,
                "has_next_page": флаг наличия следующей страницы
            }
        """
        # Это пример реализации, в реальном случае нужно адаптировать
        # под конкретные эндпоинты и особенности API Dmarket
        
        # В этом примере мы просто получаем предложения о продаже,
        # так как API для buy orders может отличаться
        sell_offers = await self.get_sell_offers(
            game=game,
            limit=100,
            cursor=cursor
        )
        
        # Проверяем, нет ли ошибки
        if sell_offers.get("error"):
            logger.error(f"Error fetching sell offers: {sell_offers}")
            return {
                "items": [],
                "cursor": None,
                "has_next_page": False
            }
        
        # Это имитация результатов, в реальном сценарии нужно сравнивать
        # цены покупки и продажи и вычислять прибыль
        results = []
        for i in range(min(limit, 5)):  # Имитируем несколько результатов
            results.append({
                "name": f"Example Item {i+1}",
                "buy_price": 10 + i * 5,
                "sell_price": 15 + i * 7,
                "profit": 5 + i * 2,
                "game": game
            })
        
        # Имитируем курсор для пагинации
        # В реальном сценарии курсор должен приходить из ответа API
        next_cursor = None
        if cursor:
            # Если это не первая страница, генерируем курсор на следующую
            cursor_value = int(cursor.split("_")[1]) if "_" in cursor else 0
            next_cursor = f"page_{cursor_value + 1}" if cursor_value < 3 else None
        else:
            # Если это первая страница, создаем курсор для второй страницы
            next_cursor = "page_1"
        
        # Определяем, есть ли следующая страница
        has_next_page = next_cursor is not None
        
        return {
            "items": results,
            "cursor": next_cursor,
            "has_next_page": has_next_page
        }


# Создаем синглтон для API клиента
dmarket_api_client = DMarketAPIClient()


async def close_dmarket_api_client():
    """Закрывает соединение клиента API Dmarket."""
    await dmarket_api_client.close()


# Экспортируем клиент как синглтон
__all__ = ["dmarket_api_client", "close_dmarket_api_client"] 
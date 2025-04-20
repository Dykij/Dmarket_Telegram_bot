from .dmarket_items_queue import DmarketItemReader, DmarketItemWriter
from .dmarket_result_queue import DmarketOrderReader, DmarketOrderWriter
from .dmarket_sell_history_queue import (DmarketSellHistoryReader,
                                         DmarketSellHistoryWriter)
from .market_name_queue import MarketNameReader, MarketNameWriter

# Алиасы для обратной совместимости
CsmoneyReader = DmarketItemReader
CsmoneyWriter = DmarketItemWriter
SteamOrderReader = DmarketOrderReader
SteamOrderWriter = DmarketOrderWriter
SteamSellHistoryReader = DmarketSellHistoryReader
SteamSellHistoryWriter = DmarketSellHistoryWriter

__all__ = [
    "DmarketItemReader",
    "DmarketItemWriter",
    "MarketNameReader",
    "MarketNameWriter",
    "DmarketOrderReader",
    "DmarketOrderWriter",
    "DmarketSellHistoryReader",
    "DmarketSellHistoryWriter",
    # Алиасы для обратной совместимости
    "CsmoneyReader",
    "CsmoneyWriter",
    "SteamOrderReader",
    "SteamOrderWriter",
    "SteamSellHistoryReader",
    "SteamSellHistoryWriter",
]

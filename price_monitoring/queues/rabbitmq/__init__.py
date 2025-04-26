from .dmarket_items_queue import DmarketItemReader, DmarketItemWriter
from .dmarket_result_queue import DmarketOrderReader, DmarketOrderWriter
from .dmarket_sell_history_queue import DmarketSellHistoryReader, DmarketSellHistoryWriter
from .market_name_queue import MarketNameReader, MarketNameWriter

# Aлuacbi для o6pathoй coвmectumoctu
CsmoneyReader = DmarketItemReader
CsmoneyWriter = DmarketItemWriter
SteamOrderReader = DmarketOrderReader
SteamOrderWriter = DmarketOrderWriter
SteamSellHistoryReader = DmarketSellHistoryReader
SteamSellHistoryWriter = DmarketSellHistoryWriter

__all__ = [
    # Aлuacbi для o6pathoй coвmectumoctu
    "CsmoneyReader",
    "CsmoneyWriter",
    "DmarketItemReader",
    "DmarketItemWriter",
    "DmarketOrderReader",
    "DmarketOrderWriter",
    "DmarketSellHistoryReader",
    "DmarketSellHistoryWriter",
    "MarketNameReader",
    "MarketNameWriter",
    "SteamOrderReader",
    "SteamOrderWriter",
    "SteamSellHistoryReader",
    "SteamSellHistoryWriter",
]

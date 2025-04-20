import logging
from typing import List

from price_monitoring.models.dmarket import MarketNamePack
from price_monitoring.storage.abstract_market_name_writer import AbstractMarketNameWriter

logger = logging.getLogger(__name__)


class MarketNameExtractor:
    def __init__(self, market_name_writer: AbstractMarketNameWriter):
        self.market_name_writer = market_name_writer

    def extract(self, html_content: str) -> List[MarketNamePack]:
        # Здесь будет логика парсинга HTML и извлечения данных о рынках
        pass
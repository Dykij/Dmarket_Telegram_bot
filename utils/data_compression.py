"""Модуль сжатия данных для Dmarket Telegram Bot.

Реализует класс DataCompressor для сжатия и распаковки данных (строк и JSON-объектов)
с поддержкой обработки ошибок и логирования.
"""

import json
import logging
import zlib
from typing import Any

logger = logging.getLogger(__name__)


class DataCompressor:
    """Класс для сжатия и распаковки данных (строк и JSON-объектов)."""

    @staticmethod
    def compress_string(data: str) -> bytes:
        """Сжимает строку в байты с помощью zlib."""
        try:
            return zlib.compress(data.encode("utf-8"))
        except Exception as e:
            logger.error(f"Ошибка при сжатии строки: {e}")
            raise

    @staticmethod
    def decompress_string(data: bytes) -> str:
        """Распаковывает байты в строку с помощью zlib."""
        try:
            return zlib.decompress(data).decode("utf-8")
        except Exception as e:
            logger.error(f"Ошибка при распаковке строки: {e}")
            raise

    @staticmethod
    def compress_json(obj: Any) -> bytes:
        """Сериализует объект в JSON и сжимает его."""
        try:
            json_str = json.dumps(obj, ensure_ascii=False)
            return DataCompressor.compress_string(json_str)
        except Exception as e:
            logger.error(f"Ошибка при сжатии JSON: {e}")
            raise

    @staticmethod
    def decompress_json(data: bytes) -> Any:
        """Распаковывает байты и десериализует JSON-объект."""
        try:
            json_str = DataCompressor.decompress_string(data)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Ошибка при распаковке JSON: {e}")
            raise

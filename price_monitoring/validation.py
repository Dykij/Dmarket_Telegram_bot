"""
Модуль содержит классы для валидации данных в системе мониторинга цен.

Валидаторы проверяют корректность входных данных, предотвращают ошибки
и обеспечивают консистентность данных в системе.
"""

import logging
import re
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DmarketDataValidator:
    """Валидатор для данных, получаемых от DMarket API."""

    @staticmethod
    def validate_item(item: dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Проверяет корректность данных предмета.

        Args:
            item: Словарь с данными предмета

        Returns:
            Кортеж (успех_валидации, сообщение_об_ошибке)
        """
        # Проверка наличия обязательных полей
        required_fields = ["title", "game_id", "price"]
        for field in required_fields:
            if field not in item:
                return False, f"Отсутствует обязательное поле: {field}"

        # Проверка типов данных
        if not isinstance(item["title"], str):
            return False, "Поле 'title' должно быть строкой"

        if not isinstance(item["game_id"], str):
            return False, "Поле 'game_id' должно быть строкой"

        # Проверка корректности цены
        try:
            price = float(item["price"])
            if price < 0:
                return False, "Цена не может быть отрицательной"
        except (ValueError, TypeError):
            return False, "Некорректный формат цены"

        # Проверка валюты (если она указана)
        if "currency" in item and not isinstance(item["currency"], str):
            return False, "Поле 'currency' должно быть строкой"

        return True, None

    @staticmethod
    def validate_items_payload(
        payload: dict[str, Any],
    ) -> Tuple[bool, Optional[str], List[dict[str, Any]]]:
        """
        Проверяет корректность пакета данных с предметами.

        Примечание: Этот метод подготовлен для использования в будущих версиях
        системы мониторинга цен при расширении функциональности.

        Args:
            payload: Пакет данных с предметами

        Returns:
            Кортеж (успех_валидации, сообщение_об_ошибке,
            отфильтрованные_предметы)
        """
        if not isinstance(payload, dict):
            return False, "Payload должен быть словарем", []

        if "items" not in payload:
            return False, "Отсутствует обязательное поле 'items'", []

        if not isinstance(payload["items"], list):
            return False, "Поле 'items' должно быть списком", []

        valid_items = []
        for index, item in enumerate(payload["items"]):
            is_valid, error_message = DmarketDataValidator.validate_item(item)
            if is_valid:
                valid_items.append(item)
            else:
                logger.warning(f"Пропуск некорректного предмета (индекс {index}): {error_message}")

        if not valid_items and payload["items"]:
            return False, "Ни один из предметов не прошел валидацию", []

        return True, None, valid_items


class SecurityUtils:
    """
    Утилиты для обеспечения безопасности данных.

    Класс предоставляет методы для очистки входных данных от потенциально
    опасных символов и маскирования конфиденциальной информации в логах.

    Примечание: Этот класс подготовлен для использования в будущих версиях
    системы мониторинга цен при расширении функциональности для обеспечения
    дополнительной безопасности.
    """

    @staticmethod
    def sanitize_string(input_str: str) -> str:
        """
        Очищает строку от потенциально опасных символов.

        Метод удаляет управляющие и специальные символы, оставляя только
        безопасные символы для отображения и обработки.

        Args:
            input_str: Входная строка для очистки

        Returns:
            Очищенная строка, содержащая только безопасные символы
        """
        if not input_str:
            return ""

        # Удаляем управляющие и потенциально опасные символы
        sanitized = re.sub(r"[^\w\s\-.,;:!?()\[\]{}\'\"]+", "", input_str)
        return sanitized

    @staticmethod
    def mask_sensitive_data(data: str) -> str:
        """
        Маскирует чувствительные данные (API-ключи, токены) для журналов.

        Метод обнаруживает и скрывает конфиденциальную информацию в текстовых
        данных, защищая их от случайного раскрытия в логах.

        Args:
            data: Строка, которая может содержать чувствительную информацию

        Returns:
            Строка с замаскированными чувствительными данными
        """
        if not data:
            return ""

        # Маскировка API-ключей и токенов
        masked = re.sub(
            r'(api[_-]?key|token|secret)["\']?\s*[=:]\s*["\']?([^"\']+)["\']?',
            r"\1=***MASKED***",
            data,
            flags=re.IGNORECASE,
        )

        return masked

"""Module contains classes for data validation in the price monitoring system.

Validators check the correctness of input data, prevent errors,
and ensure data consistency in the system.
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DmarketDataValidator:
    """Validator for data received from the DMarket API."""

    @staticmethod
    def validate_item(item: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Check the correctness of item data.

        Args:
            item: Dictionary with item data

        Returns:
            Tuple (validation_success, error_message)
        """
        # Check for required fields
        required_fields = ["title", "game_id", "price"]
        for field in required_fields:
            if field not in item:
                return False, f"Missing required field: {field}"

        # Check data types
        if not isinstance(item["title"], str):
            return False, "Field 'title' must be a string"

        if not isinstance(item["game_id"], str):
            return False, "Field 'game_id' must be a string"

        # Check price correctness
        try:
            price = float(item["price"])
            if price < 0:
                return False, "Price cannot be negative"
        except (ValueError, TypeError):
            return False, "Invalid price format"

        # Check currency (if specified)
        if "currency" in item and not isinstance(item["currency"], str):
            return False, "Field 'currency' must be a string"

        return True, None

    @staticmethod
    def validate_items_payload(
        payload: dict[str, Any],
    ) -> tuple[bool, Optional[str], list[dict[str, Any]]]:
        """Check the correctness of the items data package.

        Note: This method is prepared for use in future versions
        of the price monitoring system when expanding functionality.

        Args:
            payload: Data package with items

        Returns:
            Tuple (validation_success, error_message,
            filtered_items)
        """
        if not isinstance(payload, dict):
            return False, "Payload must be a dictionary", []

        if "items" not in payload:
            return False, "Missing required field 'items'", []

        if not isinstance(payload["items"], list):
            return False, "Field 'items' must be a list", []

        valid_items = []
        for index, item in enumerate(payload["items"]):
            is_valid, error_message = DmarketDataValidator.validate_item(item)
            if is_valid:
                valid_items.append(item)
            else:
                logger.warning(f"Skipping invalid item (index {index}): {error_message}")

        if not valid_items and payload["items"]:
            return False, "None of the items passed validation", []

        return True, None, valid_items


class SecurityUtils:
    """Utilities for ensuring data security.

    The class provides methods for cleaning input data from potentially
    dangerous characters and masking confidential information in logs.

    Note: This class is prepared for use in future versions
    of the price monitoring system when expanding functionality to provide
    additional security.
    """

    @staticmethod
    def sanitize_string(input_str: str) -> str:
        """Clean a string from potentially dangerous characters.

        The method removes control and special characters, leaving only
        safe characters for display and processing.

        Args:
            input_str: Input string to clean

        Returns:
            Cleaned string containing only safe characters
        """
        if not input_str:
            return ""

        # Remove control and potentially dangerous characters
        sanitized = re.sub(r"[^\w\s\-.,;:!?()\[\]{}\'\"]+", "", input_str)
        return sanitized

    @staticmethod
    def mask_sensitive_data(data: str) -> str:
        """Mask sensitive data (API keys, tokens) for logs.

        The method detects and hides confidential information in text
        data, protecting it from accidental disclosure in logs.

        Args:
            data: String that may contain sensitive information

        Returns:
            String with masked sensitive data
        """
        if not data:
            return ""

        # Masking API keys and tokens
        masked = re.sub(
            r'(api[_-]?key|token|secret)["\']?\s*[=:]\s*["\']?([^"\']+)["\']?',
            r"\1=***MASKED***",
            data,
            flags=re.IGNORECASE,
        )

        return masked

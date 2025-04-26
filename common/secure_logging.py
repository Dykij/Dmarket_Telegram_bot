"""Secure Logging Module.

This module provides utilities for secure logging with sensitive data masking.
"""

import json
import logging
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set

# Define sensitive field names that should be masked in logs
DEFAULT_SENSITIVE_FIELDS = {
    # Auth/Security related
    "api_key",
    "apikey",
    "api_secret",
    "apisecret",
    "secret_key",
    "secretkey",
    "access_key",
    "accesskey",
    "access_token",
    "accesstoken",
    "refresh_token",
    "api_token",
    "apitoken",
    "auth_token",
    "authtoken",
    "token",
    "password",
    "pass",
    "pwd",
    "secret",
    "signature",
    "private_key",
    "privatekey",
    # Personal/Financial data
    "credit_card",
    "creditcard",
    "card_number",
    "cardnumber",
    "cvv",
    "cvc",
    "ssn",
    "social_security",
    "passport",
    "account_number",
    "accountnumber",
    # DMarket specific
    "dmarket_token",
    "dmarket_secret",
    "dmarket_api_key",
    "dmarket_api_secret",
    # Telegram specific
    "telegram_token",
    "telegram_api_token",
    "bot_token",
    "bot_api_token",
}

# Regex patterns for sensitive data
DEFAULT_SENSITIVE_PATTERNS = [
    # Credit Card Numbers
    r"\b(?:\d[ -]*?){13,16}\b",
    # API Keys/Tokens (common formats)
    r"([a-zA-Z0-9_-]{30,})",
    # Telegram Bot Tokens
    r"\b\d{8,10}:[a-zA-Z0-9_-]{35}\b",
]


class SensitiveDataFilter(logging.Filter):
    """A logging filter that masks sensitive data in log records.

    This filter will look for sensitive fields and patterns in log messages
    and mask them with asterisks to prevent leaking secrets.
    """

    def __init__(
        self,
        sensitive_fields: Optional[Set[str]] = None,
        sensitive_patterns: Optional[List[str]] = None,
        mask_char: str = "*",
        mask_length: int = 8,
    ):
        """Initialize the sensitive data filter.

        Args:
            sensitive_fields: Set of field names to mask (default: DEFAULT_SENSITIVE_FIELDS)
            sensitive_patterns: List of regex patterns to match and mask (default: DEFAULT_SENSITIVE_PATTERNS)
            mask_char: Character to use for masking (default: "*")
            mask_length: Length of the mask (default: 8)
        """
        super().__init__()
        self.sensitive_fields = sensitive_fields or DEFAULT_SENSITIVE_FIELDS
        self.sensitive_patterns = sensitive_patterns or DEFAULT_SENSITIVE_PATTERNS
        self.mask_char = mask_char
        self.mask_length = mask_length

        # Compile regex patterns
        self.compiled_patterns = [re.compile(pattern) for pattern in self.sensitive_patterns]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records by masking sensitive data.

        This method modifies the log record in place to mask sensitive data
        before allowing it to be processed by handlers.

        Args:
            record: The log record to filter

        Returns:
            True to allow the record to be processed, False to reject it
        """
        # Always allow the record, but modify it first
        if hasattr(record, "msg") and record.msg:
            if isinstance(record.msg, dict):
                # For structured logging with dictionaries
                record.msg = self._mask_dict(record.msg)
            elif isinstance(record.msg, str):
                # For string messages
                record.msg = self._mask_string(record.msg)

        # Check args as well, as they might contain sensitive data
        if hasattr(record, "args") and record.args:
            if isinstance(record.args, dict):
                record.args = self._mask_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                # Convert to a list to allow modification
                args_list = list(record.args)
                for i, arg in enumerate(args_list):
                    if isinstance(arg, dict):
                        args_list[i] = self._mask_dict(arg)
                    elif isinstance(arg, str):
                        args_list[i] = self._mask_string(arg)
                record.args = tuple(args_list)

        return True

    def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask sensitive data in a dictionary.

        Args:
            data: Dictionary to mask

        Returns:
            Masked dictionary
        """
        if not isinstance(data, dict):
            return data

        # Create a deep copy to avoid modifying the original
        masked = deepcopy(data)

        for key, value in masked.items():
            # Check if key is in sensitive fields (case-insensitive)
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                if isinstance(value, str) and value:
                    masked[key] = self._get_mask(value)

            # Recursively mask nested dictionaries
            elif isinstance(value, dict):
                masked[key] = self._mask_dict(value)

            # Mask sensitive strings
            elif isinstance(value, str):
                masked[key] = self._mask_string(value)

            # Handle lists/tuples
            elif isinstance(value, (list, tuple)):
                masked[key] = [
                    (
                        self._mask_dict(item)
                        if isinstance(item, dict)
                        else self._mask_string(item) if isinstance(item, str) else item
                    )
                    for item in value
                ]

        return masked

    def _mask_string(self, text: str) -> str:
        """Mask sensitive data in a string using regex patterns.

        Args:
            text: String to mask

        Returns:
            Masked string
        """
        if not isinstance(text, str):
            return text

        masked = text

        # Apply regex patterns to find and mask sensitive data
        for pattern in self.compiled_patterns:
            masked = pattern.sub(lambda m: self._get_mask(m.group(0)), masked)

        return masked

    def _get_mask(self, value: str) -> str:
        """Generate a mask for a sensitive value.

        For short values, mask completely. For longer values, show first 2 and last 2 characters.

        Args:
            value: Value to mask

        Returns:
            Masked value
        """
        if len(value) <= 6:
            # Completely mask short values
            return self.mask_char * self.mask_length
        else:
            # Show first 2 and last 2 characters for longer values
            return value[:2] + self.mask_char * self.mask_length + value[-2:]


class SecureJsonFormatter(logging.Formatter):
    """A formatter that produces JSON-formatted logs with sensitive data masking."""

    def __init__(
        self,
        sensitive_fields: Optional[Set[str]] = None,
        sensitive_patterns: Optional[List[str]] = None,
        **kwargs,
    ):
        """Initialize the secure JSON formatter.

        Args:
            sensitive_fields: Set of field names to mask
            sensitive_patterns: List of regex patterns to match and mask
            **kwargs: Additional arguments to pass to logging.Formatter
        """
        super().__init__(**kwargs)
        self.sensitive_data_filter = SensitiveDataFilter(
            sensitive_fields=sensitive_fields, sensitive_patterns=sensitive_patterns
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON with sensitive data masked.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log message
        """
        # Apply sensitive data filter to record
        self.sensitive_data_filter.filter(record)

        # Extract standard record attributes
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "id",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }:
                log_data[key] = value

        return json.dumps(log_data)


def setup_secure_logging(
    level: int = logging.INFO,
    json_format: bool = True,
    sensitive_fields: Optional[Set[str]] = None,
    sensitive_patterns: Optional[List[str]] = None,
    log_file: Optional[str] = None,
) -> None:
    """Set up secure logging with sensitive data masking.

    Args:
        level: Logging level (default: INFO)
        json_format: Whether to use JSON formatting (default: True)
        sensitive_fields: Set of field names to mask (default: DEFAULT_SENSITIVE_FIELDS)
        sensitive_patterns: List of regex patterns to match and mask (default: DEFAULT_SENSITIVE_PATTERNS)
        log_file: Path to log file (default: None, logs to stderr only)
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter(
        sensitive_fields=sensitive_fields, sensitive_patterns=sensitive_patterns
    )

    # Create handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            handlers.append(file_handler)
        except (OSError, PermissionError) as e:
            logging.warning(f"Could not create log file: {e!s}")

    # Configure formatter and add handlers
    for handler in handlers:
        if json_format:
            formatter = SecureJsonFormatter(
                sensitive_fields=sensitive_fields, sensitive_patterns=sensitive_patterns
            )
        else:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            # Add filter to non-JSON formatter
            handler.addFilter(sensitive_filter)

        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


def get_secure_logger(
    name: str,
    level: Optional[int] = None,
    sensitive_fields: Optional[Set[str]] = None,
    sensitive_patterns: Optional[List[str]] = None,
) -> logging.Logger:
    """Get a logger with sensitive data masking.

    Args:
        name: Logger name
        level: Logging level (default: None, inherits from parent)
        sensitive_fields: Set of field names to mask (default: DEFAULT_SENSITIVE_FIELDS)
        sensitive_patterns: List of regex patterns to match and mask (default: DEFAULT_SENSITIVE_PATTERNS)

    Returns:
        Logger with sensitive data masking
    """
    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)

    # Add sensitive data filter if not already present
    has_sensitive_filter = any(isinstance(f, SensitiveDataFilter) for f in logger.filters)

    if not has_sensitive_filter:
        logger.addFilter(
            SensitiveDataFilter(
                sensitive_fields=sensitive_fields, sensitive_patterns=sensitive_patterns
            )
        )

    return logger

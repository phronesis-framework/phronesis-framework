"""Stdlib-based logging: formatters, context adapter, idempotent setup."""

from __future__ import annotations

from .adapter import ContextLoggerAdapter
from .config import configure_logging
from .constants import DEFAULT_LEVEL, PHRONESIS_LOGGER_PREFIX
from .factory import get_logger, get_logger_with_context
from .formatters import HumanReadableFormatter, StructuredFormatter

__all__ = [
    "DEFAULT_LEVEL",
    "PHRONESIS_LOGGER_PREFIX",
    "ContextLoggerAdapter",
    "HumanReadableFormatter",
    "StructuredFormatter",
    "configure_logging",
    "get_logger",
    "get_logger_with_context",
]

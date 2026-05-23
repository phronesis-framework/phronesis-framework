"""Logger factory helpers."""

from __future__ import annotations

import logging
from typing import Any

from .adapter import ContextLoggerAdapter


def get_logger(name: str) -> logging.Logger:
    """Return the logger registered under ``name``."""
    return logging.getLogger(name)


def get_logger_with_context(name: str, **context: Any) -> ContextLoggerAdapter:
    """Return a logger that injects ``context`` into every record."""
    return ContextLoggerAdapter(logging.getLogger(name), dict(context))

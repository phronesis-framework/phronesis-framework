"""Phronesis: opinionated framework for building AI agents."""

from __future__ import annotations

import logging as _logging

from ._internal.logging import (
    configure_logging,
    get_logger,
    get_logger_with_context,
)
from ._internal.logging.constants import PHRONESIS_LOGGER_PREFIX as _ROOT

__version__ = "0.1.0"

# Defensive: prevent stdlib "no handlers" warnings when the consumer has not
# configured logging. Users opt in by calling `configure_logging()` or by
# attaching their own handler to the `phronesis` logger.
_logging.getLogger(_ROOT).addHandler(_logging.NullHandler())

__all__ = [
    "__version__",
    "configure_logging",
    "get_logger",
    "get_logger_with_context",
]

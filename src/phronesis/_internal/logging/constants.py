"""Logging package constants."""

from __future__ import annotations

import logging
from typing import Final

DEFAULT_LEVEL: Final[int] = logging.WARNING
"""Default level for the framework root logger."""

PHRONESIS_LOGGER_PREFIX: Final[str] = "phronesis"
"""Root namespace for all framework loggers."""

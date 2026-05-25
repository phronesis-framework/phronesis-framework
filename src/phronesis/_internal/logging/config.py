"""Idempotent setup for the framework root logger."""

from __future__ import annotations

import logging
import sys
from typing import Final, TextIO

from .constants import DEFAULT_LEVEL, PHRONESIS_LOGGER_PREFIX
from .formatters import HumanReadableFormatter, StructuredFormatter

_HANDLER_MARKER: Final[str] = "_phronesis_managed"


def configure_logging(
    *,
    level: int = DEFAULT_LEVEL,
    structured: bool = True,
    stream: TextIO | None = None,
) -> None:
    """Install a single managed handler on the ``phronesis`` root logger.

    Idempotent: previously installed managed handlers are replaced, so
    repeated calls do not accumulate output. Uses :class:`StructuredFormatter`
    (JSON) by default; pass ``structured=False`` for the human-readable
    formatter. ``stream`` defaults to :data:`sys.stderr`.
    """
    root = logging.getLogger(PHRONESIS_LOGGER_PREFIX)
    root.setLevel(level)

    managed = [handler for handler in root.handlers if getattr(handler, _HANDLER_MARKER, False)]

    for handler in managed:
        root.removeHandler(handler)

    formatter: logging.Formatter = StructuredFormatter() if structured else HumanReadableFormatter()

    handler = logging.StreamHandler(stream or sys.stderr)
    setattr(handler, _HANDLER_MARKER, True)
    handler.setFormatter(formatter)

    root.addHandler(handler)

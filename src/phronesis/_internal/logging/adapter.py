"""Logger adapter that injects a fixed context into every record."""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any


class ContextLoggerAdapter(logging.LoggerAdapter):  # type: ignore[type-arg]
    """Logger adapter that merges a fixed context into every record.

    Call-site ``extra={}`` wins over adapter context on key conflict.
    """

    def __init__(self, logger: logging.Logger, context: dict[str, Any]) -> None:
        super().__init__(logger, context)

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        merged: dict[str, Any] = dict(self.extra or {})
        call_site_extra = kwargs.get("extra")

        if call_site_extra:
            merged.update(call_site_extra)

        kwargs["extra"] = merged

        return msg, kwargs

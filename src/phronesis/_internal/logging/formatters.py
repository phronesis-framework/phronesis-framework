"""JSON and human-readable log record formatters."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Final

_STANDARD_LOGRECORD_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


def _utc_timestamp(record: logging.LogRecord) -> str:
    """Return ``record.created`` as ISO 8601 UTC with milliseconds."""
    dt = datetime.fromtimestamp(record.created, tz=UTC)

    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.{dt.microsecond // 1000:03d}Z"


def _extract_extras(record: logging.LogRecord) -> dict[str, Any]:
    """Return user-injected extras attached to ``record``."""
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _STANDARD_LOGRECORD_ATTRS and not key.startswith("_")
    }


class StructuredFormatter(logging.Formatter):
    """One JSON object per record (``timestamp``, ``level``, ``logger``, ``message`` + extras)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _utc_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        payload.update(_extract_extras(record))

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


class HumanReadableFormatter(logging.Formatter):
    """One line per record: ``<timestamp> <level> <logger>  <message>  [k=v ...]``."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = _utc_timestamp(record)
        extras = _extract_extras(record)
        extras_str = " ".join(f"{key}={value}" for key, value in extras.items())
        suffix = f"  [{extras_str}]" if extras_str else ""

        line = f"{timestamp} {record.levelname:<8} {record.name}  {record.getMessage()}{suffix}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        if record.stack_info:
            line += "\n" + self.formatStack(record.stack_info)

        return line
